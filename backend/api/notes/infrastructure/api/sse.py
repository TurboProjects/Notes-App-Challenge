"""SSE endpoint: GET /api/v1/questions/{id}/stream?ticket=...

Plain async Django view (not DRF): authenticated by the signed stream ticket,
served under ASGI/uvicorn as a text/event-stream.

Flow per connection: validate ticket -> punctual snapshot query (pool,
open/close) -> if terminal, emit and close -> else subscribe to the
per-process broadcaster and wait. Queue timeouts trigger a re-snapshot, so a
dead broadcaster degrades to slow polling instead of hanging the client.
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import StreamingHttpResponse

from api.notes.domain.entities import Question
from api.notes.domain.enums import QuestionStatus
from api.notes.domain.exceptions import QuestionNotFoundError
from api.notes.infrastructure.api.serializers import QuestionSerializer
from api.notes.infrastructure.container import build_question_repository
from api.notes.infrastructure.messaging.broadcaster import broadcaster

logger = logging.getLogger(__name__)

QUEUE_WAIT_SECONDS = 15.0
MAX_STREAM_SECONDS = 300.0


def _sse_event(event: str, data: dict, event_id: int | None = None) -> str:
    lines = [f"event: {event}"]
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"data: {json.dumps(data)}")
    return "\n".join(lines) + "\n\n"


def _snapshot(question_id: int, user_id: int) -> Question:
    return build_question_repository().get_for_user(
        question_id=question_id,
        user_id=user_id,
    )


async def _stream(question_id: int, user_id: int) -> AsyncIterator[str]:
    question = await sync_to_async(_snapshot)(question_id, user_id)
    if question.status != QuestionStatus.PENDING:
        yield _sse_event("status", QuestionSerializer(question).data)
        return

    yield _sse_event("status", QuestionSerializer(question).data)

    queue = await broadcaster.subscribe(question_id)
    try:
        deadline = asyncio.get_event_loop().time() + MAX_STREAM_SECONDS
        while asyncio.get_event_loop().time() < deadline:
            payload: dict | None = None
            # Timeout -> fallback re-snapshot below (broadcaster belt-and-braces).
            with contextlib.suppress(TimeoutError):
                payload = await asyncio.wait_for(
                    queue.get(),
                    timeout=QUEUE_WAIT_SECONDS,
                )

            if payload is not None and payload.get("kind") == "delta":
                # Ephemeral answer-text delta: forwarded as-is, no DB hit; the
                # durable answer still arrives via `status` below.
                yield _sse_event(
                    "delta",
                    {"seq": payload.get("seq"), "text": payload.get("text", "")},
                    event_id=payload.get("seq"),
                )
                continue

            # `status` notification, unknown/missing kind, or timeout: the
            # snapshot query is the source of truth either way.
            question = await sync_to_async(_snapshot)(question_id, user_id)
            if question.status != QuestionStatus.PENDING:
                yield _sse_event("status", QuestionSerializer(question).data)
                return
            # Keep-alive comment so proxies don't kill the idle stream.
            yield ": keep-alive\n\n"
    finally:
        await broadcaster.unsubscribe(question_id, queue)


@transaction.non_atomic_requests
async def question_stream(request: HttpRequest, question_id: int) -> HttpResponse:
    """ATOMIC_REQUESTS must not wrap async views, and a long-lived stream
    must never hold a transaction open anyway; its reads are punctual
    snapshot queries through sync_to_async."""
    ticket = request.GET.get("ticket", "")
    try:
        claims = signing.loads(
            ticket,
            salt=settings.STREAM_TICKET_SALT,
            max_age=settings.STREAM_TICKET_MAX_AGE,
        )
    except signing.BadSignature:
        return HttpResponse(status=401)

    if claims.get("q") != question_id:
        return HttpResponse(status=401)

    try:
        # Existence/ownership check before holding a stream open.
        await sync_to_async(_snapshot)(question_id, claims["u"])
    except QuestionNotFoundError:
        return HttpResponse(status=404)

    response = StreamingHttpResponse(
        _stream(question_id, claims["u"]),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response

"""Per-process SSE broadcaster (design D2).

ONE dedicated LISTEN connection per API process; an asyncio task fans
notifications out to in-process queues, one per live SSE response. 50
concurrent SSE clients cost 50 cheap ASGI responses + ONE Postgres
connection — never one LISTEN per client.

NOT the outbox relay: the relay moves durable work Postgres -> RabbitMQ from
its own process; this moves ephemeral UX notifications Postgres -> HTTP
sockets and must live inside uvicorn, where the responses are. They share
the PgListener primitive only.
"""

import asyncio
import contextlib
import json
import logging

from django.conf import settings

from api.notes.infrastructure.messaging.listener import PgListener

logger = logging.getLogger(__name__)


class QuestionEventsBroadcaster:
    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[dict]]] = {}
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def subscribe(self, question_id: int) -> asyncio.Queue:
        """Register a queue for a question's events; starts (or restarts) the
        shared listener task lazily."""
        queue: asyncio.Queue[dict] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(question_id, set()).add(queue)
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
        return queue

    async def unsubscribe(self, question_id: int, queue: asyncio.Queue) -> None:
        async with self._lock:
            queues = self._subscribers.get(question_id)
            if queues is not None:
                queues.discard(queue)
                if not queues:
                    del self._subscribers[question_id]

    async def _run(self) -> None:
        """The single shared listener loop. If it dies it restarts on the next
        subscribe; SSE generators also re-snapshot on queue timeouts, so a
        dead broadcaster degrades to polling instead of hanging clients."""
        try:
            async with PgListener(settings.QUESTION_EVENTS_CHANNEL) as listener:
                while True:
                    payloads = await listener.wait(wait_seconds=30.0)
                    for raw in payloads:
                        self._dispatch(raw)
        except Exception:
            logger.exception("question-events broadcaster died; will restart lazily")

    def _dispatch(self, raw: str) -> None:
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            payload = json.loads(raw)
            question_id = payload.get("question_id")
            for queue in self._subscribers.get(question_id, set()).copy():
                queue.put_nowait(payload)


broadcaster = QuestionEventsBroadcaster()
"""Module-level singleton: one broadcaster per process by construction."""

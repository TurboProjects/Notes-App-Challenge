"""aio-pika consumer runtime (design D1 / ADR-0001).

Per message:
  1. parse the thin envelope          -> malformed = poison -> DLQ, no retries
  2. claim InboxEvent (unique insert) -> duplicate delivery = ack & skip
  3. run the handler (use case)       -> ack on success
  4. on failure: requeue until x-delivery-limit is reached, then mark the
     inbox record FAILED (the API derives status FAILED from it) and
     dead-letter the message to the DLQ.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

import aio_pika
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from api.notes.infrastructure.messaging.envelopes import MalformedPayloadError
from api.notes.infrastructure.messaging.topology import QueueSpec
from api.notes.infrastructure.messaging.topology import declare_topology
from api.notes.models import InboxEvent

logger = logging.getLogger(__name__)

PREFETCH = 8

Handler = Callable[[dict[str, Any], str], Awaitable[None]]
"""(payload, event_id) -> None. Raises to trigger retry/DLQ."""


def _claim(event_id: str, consumer: str, correlation_id: str) -> InboxEvent | None:
    """Insert the inbox row; None means it already exists (duplicate or retry)."""
    obj, created = InboxEvent.objects.get_or_create(
        event_id=event_id,
        consumer=consumer,
        defaults={"correlation_id": correlation_id},
    )
    return obj if created else (None if obj.processing_status else obj)


def _mark_failed(event_id: str, consumer: str, error_code: str) -> None:
    InboxEvent.objects.filter(event_id=event_id, consumer=consumer).update(
        processing_status=InboxEvent.FAILED,
        error_code=error_code[:100],
        processed_at=timezone.now(),
    )


class ConsumerRuntime:
    """One long-running consumer process bound to one queue."""

    def __init__(self, *, queue: QueueSpec, consumer_name: str, handler: Handler):
        self._queue_spec = queue
        self._consumer_name = consumer_name
        self._handler = handler

    async def run(self) -> None:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=PREFETCH)
            await declare_topology(channel)
            queue = await channel.get_queue(self._queue_spec.name)
            logger.info(
                "%s consuming %s (prefetch=%d)",
                self._consumer_name,
                self._queue_spec.name,
                PREFETCH,
            )
            await queue.consume(self._on_message)
            await asyncio.Future()  # run forever (robust connection reconnects)

    async def _on_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        event_id = message.message_id or ""
        correlation_id = message.correlation_id or ""

        if not event_id:
            # Poison: park in the DLQ immediately; never retried, and the
            # redrive command skips messages without a valid envelope.
            logger.error("poison message (no message_id) on %s", self._queue_spec.name)
            await message.reject(requeue=False)
            return
        try:
            payload = json.loads(message.body)
        except json.JSONDecodeError:
            logger.exception("poison message (bad JSON) on %s", self._queue_spec.name)
            await message.reject(requeue=False)
            return

        claimed = await sync_to_async(_claim)(
            event_id,
            self._consumer_name,
            correlation_id,
        )
        if claimed is None:
            logger.info("duplicate delivery %s; ack & skip", event_id)
            await message.ack()
            return

        try:
            await self._handler(payload, event_id)
        except MalformedPayloadError:
            logger.exception("malformed payload %s", event_id)
            await sync_to_async(_mark_failed)(
                event_id,
                self._consumer_name,
                "MALFORMED_PAYLOAD",
            )
            await message.reject(requeue=False)
            return
        except Exception as exc:
            delivery_count = int(message.headers.get("x-delivery-count") or 0)
            attempts = delivery_count + 1
            if attempts >= settings.EVENTS_DELIVERY_LIMIT:
                error_code = getattr(exc, "error_code", type(exc).__name__)
                logger.exception(
                    "event %s exhausted %d attempts -> DLQ (%s)",
                    event_id,
                    attempts,
                    error_code,
                )
                await sync_to_async(_mark_failed)(
                    event_id,
                    self._consumer_name,
                    str(error_code),
                )
                await message.reject(requeue=False)  # dead-letter -> DLQ
            else:
                logger.warning(
                    "event %s attempt %d failed; requeueing: %s",
                    event_id,
                    attempts,
                    exc,
                )
                await message.reject(requeue=True)
            return

        await message.ack()

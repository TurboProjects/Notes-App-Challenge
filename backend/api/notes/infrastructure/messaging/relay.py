"""Outbox relay: the only bridge between Postgres truth and the broker.
At-least-once by construction:

  claim batch (FOR UPDATE SKIP LOCKED) -> publish (publisher confirms)
  -> stamp published_at. Crash anywhere -> rows stay pending -> retried.

Idle-cheap: sleeps on LISTEN outbox_channel; a slow poll (~10s) is the
durable fallback because NOTIFY is fire-and-forget.
"""

import asyncio
import json
import logging

import aio_pika
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from api.notes.infrastructure.messaging.listener import PgListener
from api.notes.infrastructure.messaging.topology import declare_topology
from api.notes.models import OutboxEvent

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
FALLBACK_POLL_SECONDS = 10.0


def _claim_batch() -> list[OutboxEvent]:
    """Claim pending events with FOR UPDATE SKIP LOCKED.

    The row lock is released when this transaction commits (before publish),
    so a concurrent relay could re-claim a batch mid-publish: the worst case
    is a duplicate publish, which is exactly the at-least-once contract the
    consumers' InboxEvent dedup absorbs. SKIP LOCKED still prevents two
    relays from grinding on the same rows at the same instant.
    """
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(published_at__isnull=True)
            .order_by("id")[:BATCH_SIZE],
        )
        # Bump attempts inside the claim so crashed publishes leave a trace.
        if events:
            OutboxEvent.objects.filter(id__in=[e.id for e in events]).update(
                attempts=F("attempts") + 1,
            )
        return events


def _mark_published(event_ids: list[int]) -> None:
    OutboxEvent.objects.filter(id__in=event_ids).update(published_at=timezone.now())


async def run_relay() -> None:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await declare_topology(channel)
        logger.info("outbox relay started (batch=%d)", BATCH_SIZE)

        async with PgListener(settings.OUTBOX_NOTIFY_CHANNEL) as listener:
            while True:
                events = await sync_to_async(_claim_batch)()
                if not events:
                    # Sleep until NOTIFY or fallback tick: zero idle queries.
                    await listener.wait(wait_seconds=FALLBACK_POLL_SECONDS)
                    continue

                published: list[int] = []
                for event in events:
                    await exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(event.payload).encode("utf-8"),
                            message_id=str(event.event_id),
                            correlation_id=event.correlation_id,
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            content_type="application/json",
                        ),
                        routing_key=event.topic,
                    )
                    published.append(event.id)
                await sync_to_async(_mark_published)(published)
                logger.info("relay published %d events", len(published))


def main() -> None:
    asyncio.run(run_relay())

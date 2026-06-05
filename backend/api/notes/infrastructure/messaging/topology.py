"""RabbitMQ topology (design D1): declared idempotently at startup by every
process that touches the broker, so boot order never matters.

  exchange notes.events (topic) ──┬── question.asked.q ──(x-delivery-limit=5)──┐
                                  └── note.embed.q     ──(x-delivery-limit=5)──┤
  exchange notes.events.dlx (topic) ─┬─ question.asked.dlq ◀────────────────────┘
                                     └─ note.embed.dlq
"""

from dataclasses import dataclass

import aio_pika
from django.conf import settings

QUESTION_ASKED_TOPIC = "question.asked"
NOTE_EMBED_TOPIC = "note.embed.requested"

RAG_CONSUMER = "rag-worker"
EMBED_CONSUMER = "embedding-worker"


@dataclass(frozen=True)
class QueueSpec:
    name: str
    routing_key: str
    dlq_name: str


QUESTION_QUEUE = QueueSpec(
    name="question.asked.q",
    routing_key=QUESTION_ASKED_TOPIC,
    dlq_name="question.asked.dlq",
)
NOTE_EMBED_QUEUE = QueueSpec(
    name="note.embed.q",
    routing_key=NOTE_EMBED_TOPIC,
    dlq_name="note.embed.dlq",
)

ALL_QUEUES = [QUESTION_QUEUE, NOTE_EMBED_QUEUE]


async def declare_topology(
    channel: aio_pika.abc.AbstractChannel,
) -> aio_pika.abc.AbstractExchange:
    """Declare exchanges, quorum work queues and DLQs. Returns the work exchange."""
    exchange = await channel.declare_exchange(
        settings.EVENTS_EXCHANGE,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    dlx = await channel.declare_exchange(
        settings.EVENTS_DLX,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    for spec in ALL_QUEUES:
        dlq = await channel.declare_queue(
            spec.dlq_name,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await dlq.bind(dlx, routing_key=spec.routing_key)

        queue = await channel.declare_queue(
            spec.name,
            durable=True,
            arguments={
                "x-queue-type": "quorum",
                "x-delivery-limit": settings.EVENTS_DELIVERY_LIMIT,
                "x-dead-letter-exchange": settings.EVENTS_DLX,
            },
        )
        await queue.bind(exchange, routing_key=spec.routing_key)
    return exchange

import asyncio
import json

import aio_pika
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from api.notes.infrastructure.messaging.topology import ALL_QUEUES
from api.notes.infrastructure.messaging.topology import declare_topology
from api.notes.models import InboxEvent


def _reset_inbox(event_id: str) -> int:
    """Clear the FAILED inbox rows so consumers can re-claim the event."""
    deleted, _ = InboxEvent.objects.filter(event_id=event_id).delete()
    return deleted


def _is_poison(message: aio_pika.abc.AbstractIncomingMessage) -> bool:
    """Messages without a valid envelope are never auto-redriven."""
    if not message.message_id:
        return True
    try:
        json.loads(message.body)
    except json.JSONDecodeError:
        return True
    return False


async def _redrive(
    dlq_name: str,
    routing_key: str,
    max_messages: int,
) -> tuple[int, int]:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    redriven = parked = 0
    async with connection:
        channel = await connection.channel()
        exchange = await declare_topology(channel)
        dlq = await channel.get_queue(dlq_name)

        for _ in range(max_messages):
            message = await dlq.get(fail=False)
            if message is None:
                break
            if _is_poison(message):
                await message.reject(requeue=True)  # leave parked in the DLQ
                parked += 1
                continue

            await sync_to_async(_reset_inbox)(message.message_id)
            await exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    message_id=message.message_id,
                    correlation_id=message.correlation_id,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=routing_key,
            )
            await message.ack()
            redriven += 1
    return redriven, parked


class Command(BaseCommand):
    help = "Republish messages from a DLQ to the work exchange after a fix."

    def add_arguments(self, parser):
        parser.add_argument(
            "--queue",
            required=True,
            choices=[spec.dlq_name for spec in ALL_QUEUES],
        )
        parser.add_argument("--max", type=int, default=100)

    def handle(self, *args, **options):
        spec = next(s for s in ALL_QUEUES if s.dlq_name == options["queue"])
        try:
            redriven, parked = asyncio.run(
                _redrive(spec.dlq_name, spec.routing_key, options["max"]),
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"redriven={redriven} parked_poison={parked} from {spec.dlq_name}",
            ),
        )

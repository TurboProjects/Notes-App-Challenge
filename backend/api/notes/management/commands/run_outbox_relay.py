from django.core.management.base import BaseCommand

from api.notes.infrastructure.messaging.relay import main


class Command(BaseCommand):
    help = "Run the outbox relay: drains OutboxEvent rows to RabbitMQ."

    def handle(self, *args, **options):
        main()

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.notes.models import InboxEvent
from api.notes.models import OutboxEvent


class Command(BaseCommand):
    help = (
        "Retention sweep: delete published OutboxEvent rows and SUCCEEDED "
        "InboxEvent rows older than --days. FAILED inbox rows are KEPT: "
        "they back the API's derived FAILED status."
    )

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        outbox_deleted, _ = OutboxEvent.objects.filter(
            published_at__lt=cutoff,
        ).delete()
        inbox_deleted, _ = InboxEvent.objects.filter(
            processing_status=InboxEvent.SUCCEEDED,
            processed_at__lt=cutoff,
        ).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"swept outbox={outbox_deleted} inbox={inbox_deleted} "
                f"(older than {options['days']}d)",
            ),
        )

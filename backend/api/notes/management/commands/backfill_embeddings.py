from django.core.management.base import BaseCommand

from api.notes.application.dtos import BackfillEmbeddingsCommand
from api.notes.infrastructure.container import build_backfill_embeddings_use_case


class Command(BaseCommand):
    help = (
        "Bigbang backfill: enqueue note.embed.requested events for notes that "
        "were never indexed (or carry an outdated embedding version). Never "
        "embeds inline — the embedding worker does the work. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--throttle", type=float, default=0.0)
        parser.add_argument("--embedding-version", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        use_case = build_backfill_embeddings_use_case()
        enqueued = use_case.execute(
            BackfillEmbeddingsCommand(
                batch_size=options["batch_size"],
                throttle_seconds=options["throttle"],
                embedding_version=options["embedding_version"],
                dry_run=options["dry_run"],
            ),
        )
        verb = "would enqueue" if options["dry_run"] else "enqueued"
        self.stdout.write(self.style.SUCCESS(f"{verb} {enqueued} notes"))

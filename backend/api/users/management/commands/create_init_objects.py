from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from api.notes.infrastructure.container import build_request_note_indexing_use_case
from api.notes.models import Category
from api.notes.models import Note

from ._seed_notes import SEED_CATEGORIES
from ._seed_notes import SEED_NOTES

# The three categories the app has always shipped with, plus the travel-themed
# ones the demo notes are filed under (defined alongside the note data).
DEFAULT_CATEGORIES = {
    "Random Thoughts": "#EF9C66",
    "School": "#FCDC94",
    "Personal": "#78ABA8",
}


class Command(BaseCommand):
    help = (
        "Seeds a superuser, categories and a set of interconnected demo notes "
        "for the Ask-Your-Notes RAG feature (for testing only)."
    )

    def handle(self, *args, **kwargs):
        admin = self._ensure_superuser()
        categories = self._ensure_categories()
        self._ensure_notes(admin, categories)

    def _ensure_superuser(self):
        User = get_user_model()  # noqa: N806
        username = "admin@example.com"
        email = "admin@example.com"
        password = "123456789ABC"  # noqa: S105  (intentional dev-only credential)

        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Superuser '{username}' created successfully!"),
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Superuser '{username}' already exists."),
            )
        return user

    def _ensure_categories(self):
        """Idempotently create the default + travel categories; return name->obj."""
        categories: dict[str, Category] = {}
        for name, color in {**DEFAULT_CATEGORIES, **SEED_CATEGORIES}.items():
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={"color": color},
            )
            categories[name] = category
        self.stdout.write(
            self.style.SUCCESS(f"Ensured {len(categories)} categories."),
        )
        return categories

    def _ensure_notes(self, user, categories):
        """Seed the demo notes for the superuser and request embedding indexing.

        ORM creation alone does not index (there are no model signals); the note
        controller normally calls RequestNoteIndexingUseCase after save. We do the
        same here, inside a per-note atomic block, so the content-hash update and
        the `note.embed.requested` outbox event commit together with the note:
        the embedding worker then picks them up asynchronously.
        """
        if Note.objects.filter(user=user).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Notes already exist for the superuser; skipping note seed.",
                ),
            )
            return

        request_indexing = build_request_note_indexing_use_case()
        created = 0
        for spec in SEED_NOTES:
            with transaction.atomic():
                note = Note.objects.create(
                    user=user,
                    category=categories.get(spec["category"]),
                    title=spec["title"],
                    content=spec["content"],
                )
                request_indexing.execute(note_id=note.id)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} demo notes and requested embedding indexing.",
            ),
        )

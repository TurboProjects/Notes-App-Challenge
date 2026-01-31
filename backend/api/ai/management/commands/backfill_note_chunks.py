from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.notes.models import Note
from api.ai.models import NoteChunk
from api.ai import services


class Command(BaseCommand):
    help = "Backfill note chunks and embeddings for all notes."

    def handle(self, *args, **options):
        try:
            notes = Note.objects.select_related("user").all()
        except Exception as exc:
            raise CommandError(f"Failed to load notes: {exc}")

        total = notes.count()
        self.stdout.write(f"Found {total} notes. Backfilling chunks and embeddings...")

        for idx, note in enumerate(notes, start=1):
            self.stdout.write(f"[{idx}/{total}] Processing note id={note.id} title={note.title!r}")
            with transaction.atomic():
                # delete old chunks
                NoteChunk.objects.filter(note=note).delete()

                chunks = services.chunk_text(note.title, note.content)
                if not chunks:
                    continue
                try:
                    embeddings = services.embed_texts(chunks)
                except RuntimeError as exc:
                    raise CommandError(str(exc))

                objs = []
                for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    objs.append(
                        NoteChunk(
                            user=note.user,
                            note=note,
                            chunk_index=i,
                            text=chunk,
                            embedding=emb,
                        )
                    )
                NoteChunk.objects.bulk_create(objs)

        self.stdout.write(self.style.SUCCESS("Backfill complete."))

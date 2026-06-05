import logging
import time
from collections.abc import Callable

from api.notes.application.dtos import BackfillEmbeddingsCommand
from api.notes.domain.ports import EventOutbox
from api.notes.domain.ports import NoteIndexRepository

logger = logging.getLogger(__name__)

NOTE_EMBED_TOPIC = "note.embed.requested"


class BackfillEmbeddingsUseCase:
    """Bigbang backfill: ENQUEUES note.embed.requested events in batches.

    Never embeds inline — the embedding worker (the same pipeline that serves
    live edits) does the work. Resumable and idempotent for free: re-runs
    select only notes still missing the target embedding version.
    """

    def __init__(
        self,
        *,
        notes_index: NoteIndexRepository,
        outbox: EventOutbox,
        default_embedding_version: int,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._notes_index = notes_index
        self._outbox = outbox
        self._default_embedding_version = default_embedding_version
        self._sleep = sleep

    def execute(self, command: BackfillEmbeddingsCommand) -> int:
        """Returns the number of notes enqueued (or that would be, on dry-run)."""
        version = command.embedding_version or self._default_embedding_version
        enqueued = 0

        for batch in self._notes_index.iter_notes_needing_index(
            embedding_version=version,
            batch_size=command.batch_size,
        ):
            if command.dry_run:
                enqueued += len(batch)
                continue
            for note_id, content_hash in batch:
                self._outbox.emit(
                    topic=NOTE_EMBED_TOPIC,
                    correlation_id=str(note_id),
                    payload={
                        "schema_version": 1,
                        "note_id": note_id,
                        "content_hash": content_hash,
                    },
                )
            enqueued += len(batch)
            logger.info("backfill: enqueued %d notes (total=%d)", len(batch), enqueued)
            if command.throttle_seconds:
                self._sleep(command.throttle_seconds)

        return enqueued

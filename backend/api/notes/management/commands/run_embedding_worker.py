import asyncio
import logging
from typing import Any

from django.core.management.base import BaseCommand

from api.notes.application.dtos import ReindexNoteCommand
from api.notes.domain.exceptions import NoteNotFoundError
from api.notes.infrastructure.container import build_reindex_note_use_case
from api.notes.infrastructure.messaging.consumer import ConsumerRuntime
from api.notes.infrastructure.messaging.envelopes import parse_note_embed_requested
from api.notes.infrastructure.messaging.topology import EMBED_CONSUMER
from api.notes.infrastructure.messaging.topology import NOTE_EMBED_QUEUE

logger = logging.getLogger(__name__)


async def _handle(payload: dict[str, Any], event_id: str) -> None:
    envelope = parse_note_embed_requested(payload)
    use_case = build_reindex_note_use_case()
    try:
        await use_case.execute(
            ReindexNoteCommand(
                note_id=envelope.note_id,
                content_hash=envelope.content_hash,
            ),
        )
    except NoteNotFoundError:
        # The note was deleted after the event was queued — nothing to index.
        logger.info("note=%s deleted before indexing; skipping", envelope.note_id)


class Command(BaseCommand):
    help = "Run the embedding worker: consumes note.embed.q and (re)indexes notes."

    def handle(self, *args, **options):
        runtime = ConsumerRuntime(
            queue=NOTE_EMBED_QUEUE,
            consumer_name=EMBED_CONSUMER,
            handler=_handle,
        )
        asyncio.run(runtime.run())

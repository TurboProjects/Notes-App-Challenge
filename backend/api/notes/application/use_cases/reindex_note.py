import logging

from api.notes.application.dtos import ReindexNoteCommand
from api.notes.domain.chunking import split_into_chunks
from api.notes.domain.ports import EmbeddingProvider
from api.notes.domain.ports import NoteIndexRepository

logger = logging.getLogger(__name__)


class ReindexNoteUseCase:
    """(Re)chunk + (re)embed one note. Runs under the embedding worker.

    Incremental by design: chunks whose content_hash already exists are kept
    (zero API cost); only new/changed chunks hit the embeddings API; orphans
    are deleted in the same transaction (atomic index swap).
    """

    def __init__(  # noqa: PLR0913 — DI constructor: ports + config knobs
        self,
        *,
        notes_index: NoteIndexRepository,
        embedder: EmbeddingProvider,
        embedding_model: str,
        embedding_version: int,
        chunk_target_tokens: int = 650,
        chunk_overlap_ratio: float = 0.15,
    ):
        self._notes_index = notes_index
        self._embedder = embedder
        self._embedding_model = embedding_model
        self._embedding_version = embedding_version
        self._chunk_target_tokens = chunk_target_tokens
        self._chunk_overlap_ratio = chunk_overlap_ratio

    async def execute(self, command: ReindexNoteCommand) -> None:
        content, current_hash = await self._notes_index.aget_note_content(
            note_id=command.note_id,
        )

        # Stale-event guard: a newer edit already queued its own event.
        if command.content_hash != current_hash:
            logger.info("note=%s stale embed event; skipping", command.note_id)
            return

        pieces = split_into_chunks(
            content,
            target_tokens=self._chunk_target_tokens,
            overlap_ratio=self._chunk_overlap_ratio,
        )

        existing = await self._notes_index.aget_existing_chunk_hashes(
            note_id=command.note_id,
        )
        new_pieces = [p for p in pieces if p.content_hash not in existing]

        embeddings: dict[str, list[float]] = {}
        if new_pieces:
            vectors = await self._embedder.aembed([p.text for p in new_pieces])
            embeddings = {
                piece.content_hash: vector
                for piece, vector in zip(new_pieces, vectors, strict=True)
            }
        logger.info(
            "note=%s chunks=%d new=%d kept=%d",
            command.note_id,
            len(pieces),
            len(new_pieces),
            len(pieces) - len(new_pieces),
        )

        await self._notes_index.areplace_chunks(
            note_id=command.note_id,
            pieces=pieces,
            embeddings=embeddings,
            embedding_model=self._embedding_model,
            embedding_version=self._embedding_version,
        )

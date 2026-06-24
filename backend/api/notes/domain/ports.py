"""Ports (ABCs) implemented by infrastructure adapters.

Sync methods serve the HTTP request path (DRF is sync); async methods serve
the aio-pika workers.
"""

from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterator
from typing import Any

from api.notes.domain.entities import Question
from api.notes.domain.value_objects import ChunkPiece
from api.notes.domain.value_objects import GeneratedAnswer
from api.notes.domain.value_objects import RetrievedChunk


class QuestionRepository(ABC):
    """Persistence for the Question aggregate (Question + Answer + Citations).

    The user-facing status is DERIVED here: Answer exists -> SUCCESS;
    the rag-worker inbox record is FAILED -> FAILED; else PENDING.
    """

    @abstractmethod
    def create(self, *, user_id: str, text: str) -> Question:
        """Persist a new question (request path, inside ATOMIC_REQUESTS)."""

    @abstractmethod
    def get_for_user(self, *, question_id: int, user_id: str) -> Question:
        """Owner-scoped fetch with derived status; raises QuestionNotFoundError."""

    @abstractmethod
    async def aget(self, *, question_id: int) -> Question:
        """Worker-path fetch; raises QuestionNotFoundError."""

    @abstractmethod
    async def asave_answer(
        self,
        *,
        question_id: int,
        generated: GeneratedAnswer,
        retrieved: list[RetrievedChunk],
        event_id: str,
        consumer: str,
    ) -> None:
        """One transaction: persist Answer + only-cited Citations, mark the
        consumer's InboxEvent SUCCEEDED (with LLM telemetry), NOTIFY listeners."""


class ChunkSearchRepository(ABC):
    """Hybrid retrieval pipeline (vector + FTS -> RRF -> neighbors -> dedup)."""

    @abstractmethod
    async def asearch(
        self,
        *,
        user_id: str,
        query_embedding: list[float],
        query_text: str,
    ) -> list[RetrievedChunk]: ...


class NoteIndexRepository(ABC):
    """Persistence for the chunk index (the embedding worker's port)."""

    @abstractmethod
    def get_content_and_hash(self, *, note_id: int) -> tuple[str, str]:
        """Sync (request path): returns (content, stored content_hash);
        raises NoteNotFoundError."""

    @abstractmethod
    def set_content_hash(self, *, note_id: int, content_hash: str) -> None:
        """Sync (request path): persist the recomputed content_hash."""

    @abstractmethod
    async def aget_note_content(self, *, note_id: int) -> tuple[str, str]:
        """Returns (content, current content_hash); raises NoteNotFoundError."""

    @abstractmethod
    async def aget_existing_chunk_hashes(self, *, note_id: int) -> dict[str, int]:
        """content_hash -> chunk id for the note's current chunks."""

    @abstractmethod
    async def areplace_chunks(
        self,
        *,
        note_id: int,
        pieces: list[ChunkPiece],
        embeddings: dict[str, list[float]],
        embedding_model: str,
        embedding_version: int,
    ) -> None:
        """One transaction: keep unchanged chunks, upsert new ones (embeddings
        keyed by piece content_hash), delete orphans, stamp Note.indexed_at."""

    @abstractmethod
    def iter_notes_needing_index(
        self,
        *,
        embedding_version: int,
        batch_size: int,
    ) -> Iterator[list[tuple[int, str]]]:
        """Batches of (note_id, content_hash) with indexed_at IS NULL or an
        older embedding version."""


class EmbeddingProvider(ABC):
    @abstractmethod
    async def aembed(self, texts: list[str]) -> list[list[float]]:
        """L2-normalized embeddings, one per input text."""


class AnswerGenerator(ABC):
    @abstractmethod
    async def agenerate(
        self,
        *,
        question_text: str,
        chunks: list[RetrievedChunk],
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> GeneratedAnswer:
        """Structured-output generation; cites only the chunk ids actually used.
        Streams new answer-text suffixes through on_delta as they arrive.
        Raises AnswerGenerationError on provider failure."""


class AnswerDeltaPublisher(ABC):
    """Ephemeral streaming deltas for live SSE consumers."""

    @abstractmethod
    async def apublish(self, *, question_id: int, seq: int, text: str) -> None:
        """Best-effort publish of an answer-text delta; must never raise into
        the answer pipeline: a lost delta only degrades the streaming UX."""


class EventOutbox(ABC):
    """Transactional outbox writer (request path or management command)."""

    @abstractmethod
    def emit(
        self,
        *,
        topic: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Insert an OutboxEvent in the CURRENT transaction and schedule a
        post-commit NOTIFY to wake the relay."""

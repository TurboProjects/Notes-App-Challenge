"""Application commands (frozen dataclasses: no validation library at this
layer by design; transport validation happens in DRF serializers, domain
validation in pydantic entities)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AskQuestionCommand:
    user_id: str  # opaque user key (UUID in this app)
    text: str


@dataclass(frozen=True)
class AnswerQuestionCommand:
    question_id: int
    event_id: str
    consumer: str


@dataclass(frozen=True)
class ReindexNoteCommand:
    note_id: int
    content_hash: str


@dataclass(frozen=True)
class BackfillEmbeddingsCommand:
    batch_size: int = 100
    throttle_seconds: float = 0.0
    embedding_version: int | None = None
    dry_run: bool = False

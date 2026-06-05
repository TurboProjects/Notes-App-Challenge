from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict

from api.notes.domain.enums import QuestionStatus


class Citation(BaseModel):
    """A source the LLM actually cited, frozen at answer time.

    chunk_id survives as None after re-chunking (SET_NULL); note_id and
    snippet keep the citation resolvable and auditable forever.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    note_id: int | None
    note_title: str = ""
    chunk_id: int | None
    snippet: str
    relevance_score: float | None
    cited_order: int


class Answer(BaseModel):
    """The generated answer. Its existence IS the success state — no status
    field by design (see ADR-0001)."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    text: str
    created_at: datetime | None = None
    citations: list[Citation] = []


class Question(BaseModel):
    """Aggregate root. Immutable user input; status/error_code are derived
    read-model attributes populated by the repository, never stored.

    user_id is an opaque string in the domain (the users app keys users by
    UUID); boundaries convert with str()."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: str
    text: str
    created_at: datetime | None = None
    answer: Answer | None = None
    status: QuestionStatus = QuestionStatus.PENDING
    error_code: str | None = None

    @classmethod
    def create(cls, *, user_id: str, text: str) -> "Question":
        return cls(user_id=user_id, text=text.strip())


class NoteChunk(BaseModel):
    """A chunk of a note's content (the unit of retrieval and citation)."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    note_id: int
    chunk_index: int
    text: str
    content_hash: str

import hashlib
from dataclasses import dataclass


def sha256_of(text: str) -> str:
    """Canonical content hash used to debounce re-indexing (note and chunk level)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChunkPiece:
    """A chunk of note content produced by the splitter, before embedding."""

    index: int
    text: str
    content_hash: str


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk selected by the retrieval pipeline for the LLM context.

    relevance_score is the fused RRF score for search winners and None for
    chunks pulled in by neighbor expansion (fetched, never searched).
    """

    chunk_id: int
    note_id: int
    note_title: str
    chunk_index: int
    text: str
    relevance_score: float | None


@dataclass(frozen=True)
class GeneratedAnswer:
    """The LLM's structured output, already mapped out of the SDK schema."""

    text: str
    cited_chunk_ids: tuple[int, ...]
    model: str
    prompt_tokens: int
    completion_tokens: int

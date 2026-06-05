"""Pure chunking logic: ~500-800 target tokens per chunk, ~15% overlap,
splitting on paragraph boundaries first and sentences as fallback.

Token counts are approximated (~4 chars/token) to keep the domain free of
tokenizer dependencies; the target range is wide enough that the
approximation is harmless for retrieval quality.
"""

import re

from api.notes.domain.value_objects import ChunkPiece
from api.notes.domain.value_objects import sha256_of

_CHARS_PER_TOKEN = 4
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def split_into_chunks(
    content: str,
    *,
    target_tokens: int = 650,
    overlap_ratio: float = 0.15,
) -> list[ChunkPiece]:
    """Split note content into overlapping chunks on natural boundaries."""
    text = content.strip()
    if not text:
        return []

    target_chars = target_tokens * _CHARS_PER_TOKEN
    overlap_chars = int(target_chars * overlap_ratio)

    # Paragraphs first; oversized paragraphs split by sentence.
    units: list[str] = []
    for raw_paragraph in re.split(r"\n\s*\n", text):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= target_chars:
            units.append(paragraph)
        else:
            units.extend(s.strip() for s in _SENTENCE_RE.split(paragraph) if s.strip())

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if current and len(candidate) > target_chars:
            chunks.append(current)
            # Overlap: carry the tail of the previous chunk into the next one.
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail}\n\n{unit}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)

    return [
        ChunkPiece(index=i, text=chunk, content_hash=sha256_of(chunk))
        for i, chunk in enumerate(chunks)
    ]

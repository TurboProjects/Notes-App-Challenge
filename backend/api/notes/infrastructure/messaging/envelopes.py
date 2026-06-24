"""Thin versioned message envelopes.

Deliberately NOT pydantic: payloads carry only ids and hashes, so explicit
structural checks are enough. Malformed payloads raise MalformedPayloadError
and the consumer parks the message as poison (straight to the DLQ, no retries).
The *real* validation happens when ids hydrate domain entities.
"""

from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1


class MalformedPayloadError(Exception):
    """The message payload does not match the expected envelope shape."""


@dataclass(frozen=True)
class QuestionAskedV1:
    question_id: int
    user_id: str  # opaque user key (UUID in this app)


@dataclass(frozen=True)
class NoteEmbedRequestedV1:
    note_id: int
    content_hash: str


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        message = f"missing or non-int '{key}'"
        raise MalformedPayloadError(message)
    return value


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        message = f"missing or empty '{key}'"
        raise MalformedPayloadError(message)
    return value


def _check_schema_version(payload: dict[str, Any]) -> None:
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        message = f"unsupported schema_version: {version!r}"
        raise MalformedPayloadError(message)


def parse_question_asked(payload: dict[str, Any]) -> QuestionAskedV1:
    _check_schema_version(payload)
    return QuestionAskedV1(
        question_id=_require_int(payload, "question_id"),
        user_id=_require_str(payload, "user_id"),
    )


def parse_note_embed_requested(payload: dict[str, Any]) -> NoteEmbedRequestedV1:
    _check_schema_version(payload)
    return NoteEmbedRequestedV1(
        note_id=_require_int(payload, "note_id"),
        content_hash=_require_str(payload, "content_hash"),
    )

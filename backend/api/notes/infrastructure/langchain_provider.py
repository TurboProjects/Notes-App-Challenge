"""LangChain adapters: embeddings + streamed structured-output generation.

ADR-0007: ChatOpenAI is bound to a hand-written strict JSON schema
(response_format) with "answer" declared first, so its tokens stream to
completion before cited_chunk_ids; the growing JSON is parsed incrementally
(parse_partial_json) and new "answer" suffixes surface through the port's
on_delta callback. No pydantic here — it stays in the domain (ADR-0005).
"""

import json
import logging
import math
from collections.abc import Awaitable
from collections.abc import Callable
from typing import override

import openai
from django.conf import settings
from langchain_core.messages import AIMessageChunk
from langchain_core.utils.json import parse_partial_json
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from api.notes.domain.exceptions import AnswerGenerationError
from api.notes.domain.ports import AnswerGenerator
from api.notes.domain.ports import EmbeddingProvider
from api.notes.domain.value_objects import GeneratedAnswer
from api.notes.domain.value_objects import RetrievedChunk

logger = logging.getLogger(__name__)

_MAX_COMPLETION_TOKENS = 1024

_SYSTEM_PROMPT = (
    "You answer the user's question using ONLY the provided note chunks as "
    "sources. Each chunk is labeled [chunk <id>] with its note title. "
    "Cite the ids of the chunks you actually used in cited_chunk_ids — only "
    "those, in order of importance. If the chunks don't contain the answer, "
    "say so honestly and cite nothing."
)

# Strict structured-output schema. "answer" is declared FIRST on purpose:
# the model emits properties in schema order, so the answer text streams to
# completion before cited_chunk_ids begins (ADR-0007).
_CITED_ANSWER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "cited_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "cited_chunk_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["answer", "cited_chunk_ids"],
            "additionalProperties": False,
        },
    },
}


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def extract_answer_delta(
    accumulated_json: str,
    last_emitted: str,
) -> tuple[str, str]:
    """New suffix of the "answer" field in a growing partial-JSON string.

    Returns (delta, cursor). "Unparseable yet" means "no new delta", never an
    error — a broken partial parse must not kill the stream. A non-monotonic
    answer (should not happen while accumulating) resyncs the cursor without
    emitting, so the delta channel stays append-only.
    """
    try:
        parsed = parse_partial_json(accumulated_json)
    except ValueError:
        return "", last_emitted
    if not isinstance(parsed, dict):
        return "", last_emitted
    answer = parsed.get("answer")
    if not isinstance(answer, str) or answer == last_emitted:
        return "", last_emitted
    if answer.startswith(last_emitted):
        return answer[len(last_emitted) :], answer
    logger.warning("non-monotonic partial answer; resyncing delta cursor")
    return "", answer


def _embeddings_client() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
        api_key=settings.EMBEDDING_API_KEY,
    )


def _chat_client() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.GENERATION_MODEL,
        api_key=settings.GENERATION_API_KEY,
        max_tokens=_MAX_COMPLETION_TOKENS,
        # Without "minimal" a reasoning model burns billed reasoning tokens
        # and delays the first streamed delta (ADR-0007).
        reasoning_effort="minimal",
        stream_usage=True,
        use_responses_api=False,  # response_format streaming rides Chat Completions
    )


class LangChainEmbeddingProvider(EmbeddingProvider):
    @override
    async def aembed(self, texts: list[str]) -> list[list[float]]:
        # pydantic ValidationError (a ValueError) covers a missing/empty key
        # at client construction; OpenAIError covers the API call itself.
        try:
            vectors = await _embeddings_client().aembed_documents(texts)
        except (openai.OpenAIError, ValueError) as exc:
            error_code = f"OPENAI_EMBEDDING_{type(exc).__name__.upper()}"
            raise AnswerGenerationError(error_code, str(exc)) from exc
        # text-embedding-3 vectors come normalized; normalize defensively
        # anyway so cosine == inner product always holds.
        return [_l2_normalize(vector) for vector in vectors]


class LangChainAnswerGenerator(AnswerGenerator):
    @override
    async def agenerate(
        self,
        *,
        question_text: str,
        chunks: list[RetrievedChunk],
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> GeneratedAnswer:
        context = "\n\n".join(
            f'[chunk {chunk.chunk_id}] (note: "{chunk.note_title}")\n{chunk.text}'
            for chunk in chunks
        )
        messages = [
            ("system", _SYSTEM_PROMPT),
            ("human", f"Question: {question_text}\n\nSources:\n{context}"),
        ]

        full: AIMessageChunk | None = None
        emitted = ""
        try:
            llm = _chat_client().bind(response_format=_CITED_ANSWER_SCHEMA)
            async for chunk in llm.astream(messages):
                full = chunk if full is None else full + chunk
                if on_delta is not None:
                    delta, emitted = extract_answer_delta(full.text, emitted)
                    if delta:
                        await on_delta(delta)
        except (openai.OpenAIError, ValueError) as exc:
            error_code = f"OPENAI_{type(exc).__name__.upper()}"
            raise AnswerGenerationError(error_code, str(exc)) from exc

        if full is None:
            empty_stream = "OPENAI_EMPTY_STREAM"
            raise AnswerGenerationError(empty_stream)

        unparseable = "OPENAI_UNPARSEABLE_OUTPUT"
        try:
            parsed = json.loads(full.text)
        except json.JSONDecodeError as exc:
            raise AnswerGenerationError(unparseable, str(exc)) from exc
        if not isinstance(parsed, dict) or not isinstance(parsed.get("answer"), str):
            raise AnswerGenerationError(unparseable)

        usage = full.usage_metadata or {}
        model_name = full.response_metadata.get("model_name")
        return GeneratedAnswer(
            text=parsed["answer"],
            cited_chunk_ids=tuple(parsed.get("cited_chunk_ids") or ()),
            model=model_name or settings.GENERATION_MODEL,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )

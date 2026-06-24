"""Driven adapters: Django ORM implementations of the domain ports.

Async methods wrap sync transactional code with sync_to_async: Django
transactions are thread-bound, and the workers call these from the aio-pika
event loop.
"""

import json
import logging
from collections.abc import Iterator
from typing import override

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.postgres.search import SearchVector
from django.db import IntegrityError
from django.db import connection
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from api.notes.domain import entities
from api.notes.domain.enums import QuestionStatus
from api.notes.domain.exceptions import NoteNotFoundError
from api.notes.domain.exceptions import QuestionNotFoundError
from api.notes.domain.ports import ChunkSearchRepository
from api.notes.domain.ports import NoteIndexRepository
from api.notes.domain.ports import QuestionRepository
from api.notes.domain.value_objects import ChunkPiece
from api.notes.domain.value_objects import GeneratedAnswer
from api.notes.domain.value_objects import RetrievedChunk
from api.notes.infrastructure.messaging.topology import RAG_CONSUMER
from api.notes.models import Answer
from api.notes.models import Citation
from api.notes.models import InboxEvent
from api.notes.models import Note
from api.notes.models import NoteChunk
from api.notes.models import Question

logger = logging.getLogger(__name__)


def _to_citation_entity(citation: Citation) -> entities.Citation:
    return entities.Citation(
        id=citation.id,
        note_id=citation.note_id,
        note_title=citation.note.title if citation.note_id else "",
        chunk_id=citation.chunk_id,
        snippet=citation.snippet,
        relevance_score=citation.relevance_score,
        cited_order=citation.cited_order,
    )


class DjangoQuestionRepository(QuestionRepository):
    """Persists the Question aggregate and DERIVES the user-facing status:
    Answer exists -> SUCCESS; rag-worker inbox FAILED -> FAILED; else PENDING."""

    @override
    def create(self, *, user_id: str, text: str) -> entities.Question:
        row = Question.objects.create(user_id=user_id, text=text.strip())
        return entities.Question(
            id=row.id,
            user_id=user_id,
            text=row.text,
            created_at=row.created_at,
            status=QuestionStatus.PENDING,
        )

    @override
    def get_for_user(self, *, question_id: int, user_id: str) -> entities.Question:
        try:
            row = (
                Question.objects.select_related("answer")
                .prefetch_related("answer__citations__note")
                .get(id=question_id, user_id=user_id)
            )
        except Question.DoesNotExist as exc:
            raise QuestionNotFoundError(str(question_id)) from exc

        answer_entity = None
        status = QuestionStatus.PENDING
        error_code = None

        answer = getattr(row, "answer", None)
        if answer is not None:
            status = QuestionStatus.SUCCESS
            answer_entity = entities.Answer(
                id=answer.id,
                text=answer.text,
                created_at=answer.created_at,
                citations=[
                    _to_citation_entity(c) for c in answer.citations.all()
                ],
            )
        else:
            failed = (
                InboxEvent.objects.filter(
                    consumer=RAG_CONSUMER,
                    correlation_id=str(question_id),
                    processing_status=InboxEvent.FAILED,
                )
                .order_by("-processed_at")
                .first()
            )
            if failed is not None:
                status = QuestionStatus.FAILED
                error_code = failed.error_code or "GENERATION_FAILED"

        return entities.Question(
            id=row.id,
            user_id=str(row.user_id),
            text=row.text,
            created_at=row.created_at,
            answer=answer_entity,
            status=status,
            error_code=error_code,
        )

    @override
    async def aget(self, *, question_id: int) -> entities.Question:
        try:
            row = await Question.objects.aget(id=question_id)
        except Question.DoesNotExist as exc:
            raise QuestionNotFoundError(str(question_id)) from exc
        return entities.Question(
            id=row.id,
            user_id=str(row.user_id),
            text=row.text,
            created_at=row.created_at,
        )

    @override
    async def asave_answer(
        self,
        *,
        question_id: int,
        generated: GeneratedAnswer,
        retrieved: list[RetrievedChunk],
        event_id: str,
        consumer: str,
    ) -> None:
        await sync_to_async(self._save_answer)(
            question_id,
            generated,
            retrieved,
            event_id,
            consumer,
        )

    @staticmethod
    def _save_answer(
        question_id: int,
        generated: GeneratedAnswer,
        retrieved: list[RetrievedChunk],
        event_id: str,
        consumer: str,
    ) -> None:
        """One transaction: Answer + only-cited Citations + inbox SUCCEEDED.
        The NOTIFY is queued in the same tx and delivered at COMMIT."""
        by_id = {chunk.chunk_id: chunk for chunk in retrieved}
        with transaction.atomic():
            try:
                with transaction.atomic():
                    answer = Answer.objects.create(
                        question_id=question_id,
                        text=generated.text,
                    )
            except IntegrityError:
                # OneToOne hit: a concurrent duplicate already answered:
                # structurally idempotent, nothing else to do.
                logger.info("question=%s already answered; skipping", question_id)
                return

            # A concurrent re-index may have deleted a cited chunk between
            # retrieval and now: degrade to chunk=None (the snippet and the
            # denormalized note keep the citation auditable).
            cited_ids = [c for c in generated.cited_chunk_ids if c in by_id]
            still_existing = set(
                NoteChunk.objects.filter(id__in=cited_ids).values_list(
                    "id",
                    flat=True,
                ),
            )
            citations = [
                Citation(
                    answer=answer,
                    chunk_id=chunk_id if chunk_id in still_existing else None,
                    note_id=by_id[chunk_id].note_id,
                    snippet=by_id[chunk_id].text,
                    relevance_score=by_id[chunk_id].relevance_score,
                    cited_order=order,
                )
                for order, chunk_id in enumerate(cited_ids, start=1)
            ]
            Citation.objects.bulk_create(citations)

            InboxEvent.objects.filter(event_id=event_id, consumer=consumer).update(
                processing_status=InboxEvent.SUCCEEDED,
                processed_at=timezone.now(),
                result_metadata={
                    "model": generated.model,
                    "prompt_tokens": generated.prompt_tokens,
                    "completion_tokens": generated.completion_tokens,
                    "retrieved_chunks": len(retrieved),
                    "cited_chunks": len(citations),
                },
            )

            payload = json.dumps({"kind": "status", "question_id": question_id})
            with connection.cursor() as cursor:
                cursor.execute(
                    f'NOTIFY "{settings.QUESTION_EVENTS_CHANNEL}", %s',
                    [payload],
                )


class PgChunkSearchRepository(ChunkSearchRepository):
    """The retrieval pipeline as ONE SQL statement with CTEs:

    vector top-30 + FTS top-30 -> RRF (k=60) -> top-10 -> neighbor expansion
    (chunk_index +/- 1, same note) -> dedup -> reorder (note_id, chunk_index).
    """

    _SQL = """
    WITH vec AS (
        SELECT id, row_number() OVER (ORDER BY dist) AS rank
        FROM (
            SELECT c.id, c.embedding <=> %(query_vec)s::halfvec AS dist
            FROM notes_notechunk c
            JOIN notes_note n ON n.id = c.note_id
            WHERE n.user_id = %(user_id)s::uuid
              AND c.embedding_version = %(version)s
            ORDER BY dist
            LIMIT %(vector_k)s
        ) v
    ),
    fts AS (
        SELECT id, row_number() OVER (ORDER BY score DESC) AS rank
        FROM (
            SELECT c.id,
                   ts_rank(c.content_tsv,
                           websearch_to_tsquery('english', %(query_text)s)) AS score
            FROM notes_notechunk c
            JOIN notes_note n ON n.id = c.note_id
            WHERE n.user_id = %(user_id)s::uuid
              AND c.embedding_version = %(version)s
              AND c.content_tsv @@ websearch_to_tsquery('english', %(query_text)s)
            ORDER BY score DESC
            LIMIT %(fts_k)s
        ) f
    ),
    fused AS (
        SELECT COALESCE(vec.id, fts.id) AS chunk_id,
               (COALESCE(1.0 / (%(rrf_k)s + vec.rank), 0)
                + COALESCE(1.0 / (%(rrf_k)s + fts.rank), 0))::float AS score
        FROM vec
        FULL OUTER JOIN fts ON vec.id = fts.id
        ORDER BY score DESC
        LIMIT %(fused_k)s
    ),
    expanded AS (
        SELECT neighbor.id AS chunk_id,
               MAX(CASE WHEN neighbor.id = fused.chunk_id
                        THEN fused.score END) AS score
        FROM fused
        JOIN notes_notechunk winner ON winner.id = fused.chunk_id
        JOIN notes_notechunk neighbor
          ON neighbor.note_id = winner.note_id
         AND neighbor.chunk_index
             BETWEEN winner.chunk_index - %(window)s
                 AND winner.chunk_index + %(window)s
        GROUP BY neighbor.id
    )
    SELECT c.id, c.note_id, n.title, c.chunk_index, c.text, e.score
    FROM expanded e
    JOIN notes_notechunk c ON c.id = e.chunk_id
    JOIN notes_note n ON n.id = c.note_id
    ORDER BY c.note_id, c.chunk_index
    """

    @override
    async def asearch(
        self,
        *,
        user_id: str,
        query_embedding: list[float],
        query_text: str,
    ) -> list[RetrievedChunk]:
        return await sync_to_async(self._search)(user_id, query_embedding, query_text)

    def _search(
        self,
        user_id: str,
        query_embedding: list[float],
        query_text: str,
    ) -> list[RetrievedChunk]:
        params = {
            "query_vec": "[" + ",".join(map(str, query_embedding)) + "]",
            "query_text": query_text,
            "user_id": user_id,
            "version": settings.EMBEDDING_VERSION,
            "vector_k": settings.RETRIEVAL_VECTOR_TOP_K,
            "fts_k": settings.RETRIEVAL_FTS_TOP_K,
            "rrf_k": settings.RETRIEVAL_RRF_K,
            "fused_k": settings.RETRIEVAL_FUSED_TOP_K,
            "window": settings.RETRIEVAL_NEIGHBOR_WINDOW,
        }
        with connection.cursor() as cursor:
            cursor.execute(self._SQL, params)
            rows = cursor.fetchall()
        return [
            RetrievedChunk(
                chunk_id=row[0],
                note_id=row[1],
                note_title=row[2],
                chunk_index=row[3],
                text=row[4],
                relevance_score=row[5],
            )
            for row in rows
        ]


class DjangoNoteIndexRepository(NoteIndexRepository):
    @override
    def get_content_and_hash(self, *, note_id: int) -> tuple[str, str]:
        try:
            row = Note.objects.values("content", "content_hash").get(id=note_id)
        except Note.DoesNotExist as exc:
            raise NoteNotFoundError(str(note_id)) from exc
        return row["content"], row["content_hash"]

    @override
    def set_content_hash(self, *, note_id: int, content_hash: str) -> None:
        Note.objects.filter(id=note_id).update(content_hash=content_hash)

    @override
    async def aget_note_content(self, *, note_id: int) -> tuple[str, str]:
        try:
            row = await Note.objects.values("content", "content_hash").aget(id=note_id)
        except Note.DoesNotExist as exc:
            raise NoteNotFoundError(str(note_id)) from exc
        return row["content"], row["content_hash"]

    @override
    async def aget_existing_chunk_hashes(self, *, note_id: int) -> dict[str, int]:
        # Only chunks at the CURRENT embedding version count as reusable:
        # a version bump therefore re-embeds everything (zero-downtime
        # migration path).
        return {
            row["content_hash"]: row["id"]
            async for row in NoteChunk.objects.filter(
                note_id=note_id,
                embedding_version=settings.EMBEDDING_VERSION,
            ).values("content_hash", "id")
        }

    @override
    async def areplace_chunks(
        self,
        *,
        note_id: int,
        pieces: list[ChunkPiece],
        embeddings: dict[str, list[float]],
        embedding_model: str,
        embedding_version: int,
    ) -> None:
        await sync_to_async(self._replace_chunks)(
            note_id,
            pieces,
            embeddings,
            embedding_model,
            embedding_version,
        )

    @staticmethod
    def _replace_chunks(
        note_id: int,
        pieces: list[ChunkPiece],
        embeddings: dict[str, list[float]],
        embedding_model: str,
        embedding_version: int,
    ) -> None:
        """Atomic index swap: readers never see a half-indexed note.

        Unchanged chunks keep their embedding VALUES (copied across the
        delete+insert), the zero-API-cost part of incremental re-indexing.
        """
        with transaction.atomic():
            existing_vectors = dict(
                NoteChunk.objects.filter(note_id=note_id).values_list(
                    "content_hash",
                    "embedding",
                ),
            )
            NoteChunk.objects.filter(note_id=note_id).delete()

            rows = []
            for piece in pieces:
                vector = embeddings.get(piece.content_hash)
                if vector is None:
                    vector = existing_vectors.get(piece.content_hash)
                if vector is None:
                    # Shouldn't happen (use case embeds every new piece);
                    # skip defensively rather than fail the whole note.
                    logger.warning(
                        "note=%s piece=%d has no embedding; skipped",
                        note_id,
                        piece.index,
                    )
                    continue
                rows.append(
                    NoteChunk(
                        note_id=note_id,
                        chunk_index=piece.index,
                        text=piece.text,
                        content_hash=piece.content_hash,
                        embedding=vector,
                        embedding_model=embedding_model,
                        embedding_version=embedding_version,
                    ),
                )
            NoteChunk.objects.bulk_create(rows)
            # Generated FTS column, populated in the same transaction.
            NoteChunk.objects.filter(note_id=note_id).update(
                content_tsv=SearchVector("text", config="english"),
            )
            # Embedding model/version live on the chunks (and in settings):
            # the Note only records that it has been indexed.
            Note.objects.filter(id=note_id).update(indexed_at=timezone.now())

    @override
    def iter_notes_needing_index(
        self,
        *,
        embedding_version: int,
        batch_size: int,
    ) -> Iterator[list[tuple[int, str]]]:
        # A note needs (re)indexing when it was never indexed, or when any of
        # its chunks carry an older embedding version (the version lives on the
        # chunks now, not the Note). Keyset pagination by id; distinct collapses
        # the chunk join.
        last_id = 0
        while True:
            batch = list(
                Note.objects.filter(id__gt=last_id)
                .filter(
                    Q(indexed_at__isnull=True)
                    | Q(chunks__embedding_version__lt=embedding_version),
                )
                .order_by("id")
                .values_list("id", "content_hash")
                .distinct()[:batch_size],
            )
            if not batch:
                return
            last_id = batch[-1][0]
            yield batch

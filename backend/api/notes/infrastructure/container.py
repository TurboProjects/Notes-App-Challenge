"""
Composition root: plain factory functions, one wiring per process. Tests
build use cases with in-memory fakes of the ports.
"""

from django.conf import settings

from api.notes.application.use_cases import AnswerQuestionUseCase
from api.notes.application.use_cases import AskQuestionUseCase
from api.notes.application.use_cases import BackfillEmbeddingsUseCase
from api.notes.application.use_cases import ReindexNoteUseCase
from api.notes.application.use_cases import RequestNoteIndexingUseCase
from api.notes.infrastructure.langchain_provider import LangChainAnswerGenerator
from api.notes.infrastructure.langchain_provider import LangChainEmbeddingProvider
from api.notes.infrastructure.messaging.delta_publisher import PgAnswerDeltaPublisher
from api.notes.infrastructure.messaging.outbox import DjangoEventOutbox
from api.notes.infrastructure.repositories import DjangoNoteIndexRepository
from api.notes.infrastructure.repositories import DjangoQuestionRepository
from api.notes.infrastructure.repositories import PgChunkSearchRepository


def build_question_repository() -> DjangoQuestionRepository:
    return DjangoQuestionRepository()


# ---- API process ------------------------------------------------------------


def build_ask_question_use_case() -> AskQuestionUseCase:
    return AskQuestionUseCase(
        questions=DjangoQuestionRepository(),
        outbox=DjangoEventOutbox(),
    )


def build_request_note_indexing_use_case() -> RequestNoteIndexingUseCase:
    return RequestNoteIndexingUseCase(
        notes_index=DjangoNoteIndexRepository(),
        outbox=DjangoEventOutbox(),
    )


# ---- rag-worker process ------------------------------------------------------


def build_answer_question_use_case() -> AnswerQuestionUseCase:
    return AnswerQuestionUseCase(
        questions=DjangoQuestionRepository(),
        search=PgChunkSearchRepository(),
        embedder=LangChainEmbeddingProvider(),
        generator=LangChainAnswerGenerator(),
        delta_publisher=PgAnswerDeltaPublisher(),
    )


# ---- embedding-worker process ------------------------------------------------


def build_reindex_note_use_case() -> ReindexNoteUseCase:
    return ReindexNoteUseCase(
        notes_index=DjangoNoteIndexRepository(),
        embedder=LangChainEmbeddingProvider(),
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_version=settings.EMBEDDING_VERSION,
        chunk_target_tokens=settings.CHUNK_TARGET_TOKENS,
        chunk_overlap_ratio=settings.CHUNK_OVERLAP_RATIO,
    )


# ---- management commands -----------------------------------------------------


def build_backfill_embeddings_use_case() -> BackfillEmbeddingsUseCase:
    return BackfillEmbeddingsUseCase(
        notes_index=DjangoNoteIndexRepository(),
        outbox=DjangoEventOutbox(),
        default_embedding_version=settings.EMBEDDING_VERSION,
    )

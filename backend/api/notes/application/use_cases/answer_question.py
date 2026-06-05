import logging

from api.notes.application.dtos import AnswerQuestionCommand
from api.notes.domain.ports import AnswerDeltaPublisher
from api.notes.domain.ports import AnswerGenerator
from api.notes.domain.ports import ChunkSearchRepository
from api.notes.domain.ports import EmbeddingProvider
from api.notes.domain.ports import QuestionRepository
from api.notes.domain.value_objects import GeneratedAnswer

logger = logging.getLogger(__name__)

NO_SOURCES_MESSAGE = (
    "I couldn't find anything in your notes related to this question. "
    "Try adding some notes about it first, or rephrasing the question."
)


class AnswerQuestionUseCase:
    """The RAG pipeline: embed -> hybrid retrieve -> generate -> persist.

    Runs under the aio-pika rag-worker. Idempotency is handled by the consumer
    runtime (InboxEvent claim) before this use case executes; the Answer
    OneToOne constraint backstops double-answering structurally.
    """

    def __init__(
        self,
        *,
        questions: QuestionRepository,
        search: ChunkSearchRepository,
        embedder: EmbeddingProvider,
        generator: AnswerGenerator,
        delta_publisher: AnswerDeltaPublisher,
    ):
        self._questions = questions
        self._search = search
        self._embedder = embedder
        self._generator = generator
        self._delta_publisher = delta_publisher

    async def execute(self, command: AnswerQuestionCommand) -> None:
        question = await self._questions.aget(question_id=command.question_id)

        [query_embedding] = await self._embedder.aembed([question.text])
        chunks = await self._search.asearch(
            user_id=question.user_id,
            query_embedding=query_embedding,
            query_text=question.text,
        )

        if not chunks:
            # Empty-retrieval short-circuit: a valid outcome, not a failure:
            # skip the generation call entirely.
            logger.info("question=%s no chunks retrieved; skipping LLM", question.id)
            generated = GeneratedAnswer(
                text=NO_SOURCES_MESSAGE,
                cited_chunk_ids=(),
                model="",
                prompt_tokens=0,
                completion_tokens=0,
            )
        else:
            seq = 0

            async def _on_delta(text: str) -> None:
                nonlocal seq
                seq += 1
                await self._delta_publisher.apublish(
                    question_id=command.question_id,
                    seq=seq,
                    text=text,
                )

            generated = await self._generator.agenerate(
                question_text=question.text,
                chunks=chunks,
                on_delta=_on_delta,
            )

        await self._questions.asave_answer(
            question_id=command.question_id,
            generated=generated,
            retrieved=chunks,
            event_id=command.event_id,
            consumer=command.consumer,
        )

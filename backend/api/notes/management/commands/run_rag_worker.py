import asyncio
from typing import Any

from django.core.management.base import BaseCommand

from api.notes.application.dtos import AnswerQuestionCommand
from api.notes.infrastructure.container import build_answer_question_use_case
from api.notes.infrastructure.messaging.consumer import ConsumerRuntime
from api.notes.infrastructure.messaging.envelopes import parse_question_asked
from api.notes.infrastructure.messaging.topology import QUESTION_QUEUE
from api.notes.infrastructure.messaging.topology import RAG_CONSUMER


async def _handle(payload: dict[str, Any], event_id: str) -> None:
    envelope = parse_question_asked(payload)
    use_case = build_answer_question_use_case()
    await use_case.execute(
        AnswerQuestionCommand(
            question_id=envelope.question_id,
            event_id=event_id,
            consumer=RAG_CONSUMER,
        ),
    )


class Command(BaseCommand):
    help = "Run the RAG worker: consumes question.asked.q and answers questions."

    def handle(self, *args, **options):
        runtime = ConsumerRuntime(
            queue=QUESTION_QUEUE,
            consumer_name=RAG_CONSUMER,
            handler=_handle,
        )
        asyncio.run(runtime.run())

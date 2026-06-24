from api.notes.application.dtos import AskQuestionCommand
from api.notes.domain.entities import Question
from api.notes.domain.ports import EventOutbox
from api.notes.domain.ports import QuestionRepository

QUESTION_ASKED_TOPIC = "question.asked"


class AskQuestionUseCase:
    """Persist the question and request async answering, atomically.

    Both writes share the request transaction (ATOMIC_REQUESTS), which is the
    whole point of the transactional outbox: no dual-write window.
    """

    def __init__(self, *, questions: QuestionRepository, outbox: EventOutbox):
        self._questions = questions
        self._outbox = outbox

    def execute(self, command: AskQuestionCommand) -> Question:
        question = self._questions.create(
            user_id=command.user_id,
            text=command.text.strip(),
        )
        self._outbox.emit(
            topic=QUESTION_ASKED_TOPIC,
            correlation_id=str(question.id),
            payload={
                "schema_version": 1,
                "question_id": question.id,
                "user_id": command.user_id,
            },
        )
        return question

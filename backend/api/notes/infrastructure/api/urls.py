from django.urls import path

from api.notes.infrastructure.api.controllers import QuestionCreateController
from api.notes.infrastructure.api.controllers import QuestionDetailController
from api.notes.infrastructure.api.controllers import StreamTicketController
from api.notes.infrastructure.api.sse import question_stream

urlpatterns = [
    path("questions/", QuestionCreateController.as_view(), name="question-create"),
    path(
        "questions/<int:question_id>/",
        QuestionDetailController.as_view(),
        name="question-detail",
    ),
    path(
        "questions/<int:question_id>/stream-ticket/",
        StreamTicketController.as_view(),
        name="question-stream-ticket",
    ),
    path(
        "questions/<int:question_id>/stream",
        question_stream,
        name="question-stream",
    ),
]

"""Thin DRF controllers: transport validation -> command -> use case -> response.

The error-handling decorator maps domain exceptions to HTTP status codes so
the domain stays HTTP-agnostic (ADR-0004).
"""

import functools

from django.core import signing
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from api.notes.application.dtos import AskQuestionCommand
from api.notes.domain.exceptions import QuestionNotFoundError
from api.notes.infrastructure.api.serializers import QuestionCreateSerializer
from api.notes.infrastructure.api.serializers import QuestionSerializer
from api.notes.infrastructure.container import build_ask_question_use_case
from api.notes.infrastructure.container import build_question_repository


def with_domain_errors(view_method):
    """Domain exception -> HTTP status. 404 for not-found/not-owner: question
    existence is never leaked to non-owners."""

    @functools.wraps(view_method)
    def wrapper(*args, **kwargs):
        try:
            return view_method(*args, **kwargs)
        except QuestionNotFoundError as exc:
            raise NotFound from exc

    return wrapper


class QuestionCreateController(APIView):
    """POST /api/v1/questions/ -> 202 Accepted + Location (async-request pattern)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "questions"

    def post(self, request):
        serializer = QuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_case = build_ask_question_use_case()
        question = use_case.execute(
            AskQuestionCommand(
                user_id=str(request.user.id),
                text=serializer.validated_data["text"],
            ),
        )
        location = reverse("question-detail", args=[question.id])
        return Response(
            {"id": question.id, "status": question.status},
            status=status.HTTP_202_ACCEPTED,
            headers={"Location": location},
        )


class QuestionDetailController(APIView):
    """GET /api/v1/questions/{id}/ — polling fallback. Status is DERIVED by
    the repository (Answer exists -> SUCCESS; inbox FAILED -> FAILED; else
    PENDING)."""

    permission_classes = [IsAuthenticated]

    @with_domain_errors
    def get(self, request, question_id: int):
        question = build_question_repository().get_for_user(
            question_id=question_id,
            user_id=str(request.user.id),
        )
        return Response(QuestionSerializer(question).data)


class StreamTicketController(APIView):
    """POST /api/v1/questions/{id}/stream-ticket/ -> short-lived signed ticket.

    EventSource cannot send Authorization headers, so the SSE endpoint
    authenticates with this stateless ticket instead (design D2): scoped to
    ONE question's stream, dead in STREAM_TICKET_MAX_AGE seconds.
    """

    permission_classes = [IsAuthenticated]

    @with_domain_errors
    def post(self, request, question_id: int):
        from django.conf import settings  # noqa: PLC0415

        # Ownership check (404 for non-owners) before minting anything.
        build_question_repository().get_for_user(
            question_id=question_id,
            user_id=str(request.user.id),
        )
        ticket = signing.dumps(
            {"q": question_id, "u": str(request.user.id)},
            salt=settings.STREAM_TICKET_SALT,
        )
        return Response(
            {"ticket": ticket, "expires_in": settings.STREAM_TICKET_MAX_AGE},
            status=status.HTTP_201_CREATED,
        )

"""Integration tests for the ask-your-notes API and repositories (real DB).

Spec: openspec/changes/add-ask-your-notes/specs/ask-your-notes/spec.md.
"""

from django.core import signing
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.notes.domain.enums import QuestionStatus
from api.notes.domain.value_objects import GeneratedAnswer
from api.notes.domain.value_objects import RetrievedChunk
from api.notes.infrastructure.repositories import DjangoQuestionRepository
from api.notes.models import Answer
from api.notes.models import Citation
from api.notes.models import InboxEvent
from api.notes.models import Note
from api.notes.models import NoteChunk
from api.notes.models import OutboxEvent
from api.notes.models import Question
from api.notes.test.factories import CategoryFactory
from api.users.test.factories import UserFactory


class AskQuestionEndpointTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("question-create")

    def test_accepted_with_location_and_outbox_event(self):
        response = self.client.post(self.url, {"text": "what did I plan?"})

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "PENDING")
        question_id = response.data["id"]
        self.assertIn(f"/api/v1/questions/{question_id}/", response["Location"])

        event = OutboxEvent.objects.get(topic="question.asked")
        self.assertEqual(event.correlation_id, str(question_id))
        self.assertIsNone(event.published_at)

    def test_empty_text_rejected_without_side_effects(self):
        response = self.client.post(self.url, {"text": "   "})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Question.objects.count(), 0)
        self.assertEqual(OutboxEvent.objects.count(), 0)


class QuestionDetailEndpointTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.question = Question.objects.create(user=self.user, text="status?")
        self.url = reverse("question-detail", args=[self.question.id])

    def test_pending_by_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertIsNone(response.data["answer"])

    def test_success_derived_from_answer_existence(self):
        answer = Answer.objects.create(question=self.question, text="all good")
        Citation.objects.create(
            answer=answer,
            note=None,
            chunk=None,
            snippet="snippet",
            relevance_score=None,
            cited_order=1,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.data["status"], "SUCCESS")
        self.assertEqual(response.data["answer"]["text"], "all good")
        self.assertEqual(len(response.data["answer"]["citations"]), 1)

    def test_failed_derived_from_inbox_record(self):
        InboxEvent.objects.create(
            event_id="00000000-0000-0000-0000-000000000001",
            consumer="rag-worker",
            correlation_id=str(self.question.id),
            processing_status=InboxEvent.FAILED,
            error_code="OPENAI_TIMEOUT",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.data["status"], "FAILED")
        self.assertEqual(response.data["error"], {"code": "OPENAI_TIMEOUT"})

    def test_non_owner_gets_404_without_leaking_existence(self):
        self.client.force_authenticate(user=UserFactory())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StreamTicketEndpointTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.question = Question.objects.create(user=self.user, text="q")

    def test_mints_scoped_ticket(self):
        url = reverse("question-stream-ticket", args=[self.question.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        claims = signing.loads(response.data["ticket"], salt="sse-stream-ticket")
        self.assertEqual(claims["q"], self.question.id)
        self.assertEqual(claims["u"], str(self.user.id))

    def test_non_owner_cannot_mint(self):
        self.client.force_authenticate(user=UserFactory())
        url = reverse("question-stream-ticket", args=[self.question.id])
        self.assertEqual(
            self.client.post(url).status_code,
            status.HTTP_404_NOT_FOUND,
        )


class SaveAnswerRepositoryTests(APITestCase):
    """asave_answer (run through its sync core): Answer + ONLY cited citations
    + inbox SUCCEEDED, atomically."""

    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory()
        self.note = Note.objects.create(
            title="Plans",
            content="The plan is to ship.",
            category=self.category,
            user=self.user,
        )
        self.question = Question.objects.create(user=self.user, text="plan?")
        self.inbox = InboxEvent.objects.create(
            event_id="00000000-0000-0000-0000-000000000002",
            consumer="rag-worker",
            correlation_id=str(self.question.id),
        )

    def test_persists_only_cited_chunks_and_marks_inbox(self):
        from django.conf import settings

        real_chunk = NoteChunk.objects.create(
            note=self.note,
            chunk_index=0,
            text="The plan is to ship.",
            content_hash="h-0",
            embedding=[0.0] * settings.EMBEDDING_DIMENSIONS,
            embedding_model="test",
            embedding_version=settings.EMBEDDING_VERSION,
        )
        retrieved = [
            RetrievedChunk(
                chunk_id=real_chunk.id,
                note_id=self.note.id,
                note_title="Plans",
                chunk_index=0,
                text="The plan is to ship.",
                relevance_score=0.03,
            ),
            RetrievedChunk(
                chunk_id=999_999,  # deleted by a concurrent re-index
                note_id=self.note.id,
                note_title="Plans",
                chunk_index=1,
                text="Vanished chunk text.",
                relevance_score=None,
            ),
            RetrievedChunk(
                chunk_id=555_555,  # retrieved but NOT cited
                note_id=self.note.id,
                note_title="Plans",
                chunk_index=2,
                text="Unused context.",
                relevance_score=0.01,
            ),
        ]
        generated = GeneratedAnswer(
            text="Ship it.",
            cited_chunk_ids=(real_chunk.id, 999_999),  # 2 of 3 retrieved cited
            model="gpt-test",
            prompt_tokens=10,
            completion_tokens=5,
        )

        DjangoQuestionRepository._save_answer(
            self.question.id,
            generated,
            retrieved,
            str(self.inbox.event_id),
            "rag-worker",
        )

        answer = Answer.objects.get(question=self.question)
        citations = list(answer.citations.order_by("cited_order"))
        self.assertEqual(len(citations), 2)  # only the cited ones, never top-k
        self.assertEqual(citations[0].chunk_id, real_chunk.id)
        # The vanished chunk degrades to chunk=None but stays auditable.
        self.assertIsNone(citations[1].chunk)
        self.assertEqual(citations[1].snippet, "Vanished chunk text.")
        self.inbox.refresh_from_db()
        self.assertEqual(self.inbox.processing_status, InboxEvent.SUCCEEDED)
        self.assertEqual(self.inbox.result_metadata["model"], "gpt-test")

        repo = DjangoQuestionRepository()
        entity = repo.get_for_user(
            question_id=self.question.id,
            user_id=str(self.user.id),
        )
        self.assertEqual(entity.status, QuestionStatus.SUCCESS)


class NoteIndexingTriggerTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = CategoryFactory()

    def test_note_create_emits_embed_event(self):
        note = Note.objects.create(
            title="T",
            content="Some content.",
            category=self.category,
            user=self.user,
        )
        event = OutboxEvent.objects.get(topic="note.embed.requested")
        self.assertEqual(event.correlation_id, str(note.id))
        self.assertEqual(event.payload["content_hash"], note.content_hash)

    def test_title_only_edit_does_not_emit(self):
        note = Note.objects.create(
            title="T",
            content="Same content.",
            category=self.category,
            user=self.user,
        )
        OutboxEvent.objects.all().delete()

        note.title = "New title"
        note.save()

        self.assertEqual(
            OutboxEvent.objects.filter(topic="note.embed.requested").count(),
            0,
        )


class HybridSearchIntegrationTests(APITestCase):
    """The single-statement retrieval SQL against real pgvector + FTS."""

    def setUp(self):
        from django.conf import settings
        from django.contrib.postgres.search import SearchVector

        self.user = UserFactory()
        self.category = CategoryFactory()
        self.note = Note.objects.create(
            title="Trip",
            content="Iceland hot springs plan.",
            category=self.category,
            user=self.user,
        )
        dims = settings.EMBEDDING_DIMENSIONS
        base = [0.0] * dims
        for index, text in enumerate(
            ["Pack warm clothes.", "Visit the hot springs.", "Fly home."],
        ):
            vector = base.copy()
            vector[index] = 1.0
            NoteChunk.objects.create(
                note=self.note,
                chunk_index=index,
                text=text,
                content_hash=f"hash-{index}",
                embedding=vector,
                embedding_model="test",
                embedding_version=settings.EMBEDDING_VERSION,
            )
        NoteChunk.objects.update(
            content_tsv=SearchVector("text", config="english"),
        )

    def test_neighbor_expansion_and_dedup(self):
        from django.conf import settings
        from django.test import override_settings

        from api.notes.infrastructure.repositories import PgChunkSearchRepository

        query = [0.0] * settings.EMBEDDING_DIMENSIONS
        query[1] = 1.0  # exactly matches chunk_index=1

        # Fuse down to ONE winner so its siblings can only arrive as neighbors.
        with override_settings(RETRIEVAL_FUSED_TOP_K=1):
            results = PgChunkSearchRepository()._search(
                str(self.user.id),
                query,
                "hot springs",
            )

        # Winner (index 1) + neighbors (0 and 2), deduped, ordered by position.
        self.assertEqual([r.chunk_index for r in results], [0, 1, 2])
        winner = next(r for r in results if r.chunk_index == 1)
        neighbor = next(r for r in results if r.chunk_index == 0)
        self.assertIsNotNone(winner.relevance_score)
        self.assertIsNone(neighbor.relevance_score)  # fetched, never searched

    def test_owner_scoping(self):
        from django.conf import settings

        from api.notes.infrastructure.repositories import PgChunkSearchRepository

        query = [0.0] * settings.EMBEDDING_DIMENSIONS
        query[0] = 1.0
        results = PgChunkSearchRepository()._search(
            str(UserFactory().id),  # another user
            query,
            "hot springs",
        )
        self.assertEqual(results, [])

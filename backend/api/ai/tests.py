from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from api.notes.models import Note, Category
from api.ai.models import NoteChunk
from api.ai import services
from api.users.test.factories import UserFactory
from api.notes.test.factories import CategoryFactory


User = get_user_model()


class QueryAPIViewTest(APITestCase):
    """Test POST /api/v1/ai/query/ (question + summarized response)."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.category = CategoryFactory()
        self.note = Note.objects.create(
            title="To-dos for today",
            content="Buy milk\nCall Bob\nFinish report",
            category=self.category,
            user=self.user,
        )
        # Create chunks and embeddings for this note
        chunks = services.chunk_text(self.note.title, self.note.content)
        self.assertGreater(len(chunks), 0, "Expected at least one chunk")
        embeddings = services.embed_texts(chunks)
        self.assertEqual(len(embeddings), len(chunks))
        for i, (text, emb) in enumerate(zip(chunks, embeddings)):
            NoteChunk.objects.create(
                user=self.user,
                note=self.note,
                chunk_index=i,
                text=text,
                embedding=emb,
            )

    def test_query_returns_answer_and_sources(self):
        """Sending a question returns 200 with answer and sources."""
        response = self.client.post(
            "/api/v1/ai/query/",
            {"query": "What are my tasks for today?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("answer", response.data)
        self.assertIn("sources", response.data)
        self.assertIsInstance(response.data["answer"], str)
        self.assertIsInstance(response.data["sources"], list)

    def test_query_summarizes_from_notes(self):
        """With matching note chunks, answer or sources are non-empty."""
        response = self.client.post(
            "/api/v1/ai/query/",
            {"query": "What are my tasks for today?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Either we get a non-empty answer (LLM or fallback) or non-empty sources
        has_answer = bool(response.data.get("answer"))
        has_sources = len(response.data.get("sources", [])) > 0
        self.assertTrue(
            has_answer or has_sources,
            f"Expected non-empty answer or sources; got {response.data}",
        )

    def test_query_without_query_returns_400(self):
        """Missing query returns 400."""
        response = self.client.post(
            "/api/v1/ai/query/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_query_unauthenticated_returns_403(self):
        """Unauthenticated request is rejected."""
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/v1/ai/query/",
            {"query": "What are my tasks?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

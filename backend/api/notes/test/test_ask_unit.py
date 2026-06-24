"""Unit tests for the ask-your-notes domain and use cases: fake ports, no DB."""

import asyncio

from django.test import SimpleTestCase

from api.notes.application.dtos import AnswerQuestionCommand
from api.notes.application.dtos import AskQuestionCommand
from api.notes.application.dtos import ReindexNoteCommand
from api.notes.application.use_cases import AnswerQuestionUseCase
from api.notes.application.use_cases import AskQuestionUseCase
from api.notes.application.use_cases import ReindexNoteUseCase
from api.notes.application.use_cases import RequestNoteIndexingUseCase
from api.notes.application.use_cases.answer_question import NO_SOURCES_MESSAGE
from api.notes.domain.chunking import split_into_chunks
from api.notes.domain.entities import Question
from api.notes.domain.value_objects import GeneratedAnswer
from api.notes.domain.value_objects import RetrievedChunk
from api.notes.domain.value_objects import sha256_of
from api.notes.infrastructure.messaging.envelopes import MalformedPayloadError
from api.notes.infrastructure.messaging.envelopes import parse_note_embed_requested
from api.notes.infrastructure.messaging.envelopes import parse_question_asked


class FakeOutbox:
    def __init__(self):
        self.events = []

    def emit(self, *, topic, correlation_id, payload):
        self.events.append((topic, correlation_id, payload))


class FakeQuestionRepository:
    def __init__(self, question=None):
        self.question = question
        self.created = []
        self.saved = []

    def create(self, *, user_id, text):
        question = Question(id=1, user_id=user_id, text=text)
        self.created.append(question)
        return question

    async def aget(self, *, question_id):
        return self.question

    async def asave_answer(self, **kwargs):
        self.saved.append(kwargs)


class FakeSearch:
    def __init__(self, chunks):
        self.chunks = chunks

    async def asearch(self, **kwargs):
        return self.chunks


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    async def aembed(self, texts):
        self.calls.append(texts)
        return [[0.1] * 4 for _ in texts]


class FakeGenerator:
    def __init__(self, answer=None, deltas=()):
        self.answer = answer
        self.deltas = deltas
        self.calls = []

    async def agenerate(self, *, question_text, chunks, on_delta=None):
        self.calls.append((question_text, chunks))
        if on_delta is not None:
            for delta in self.deltas:
                await on_delta(delta)
        return self.answer


class FakeDeltaPublisher:
    def __init__(self):
        self.published = []

    async def apublish(self, *, question_id, seq, text):
        self.published.append((question_id, seq, text))


class ChunkingTests(SimpleTestCase):
    def test_empty_content_yields_no_chunks(self):
        self.assertEqual(split_into_chunks("   "), [])

    def test_short_content_is_one_chunk_with_hash(self):
        [piece] = split_into_chunks("Buy milk and eggs.")
        self.assertEqual(piece.index, 0)
        self.assertEqual(len(piece.content_hash), 64)

    def test_long_content_splits_with_overlap(self):
        paragraph = "A sentence about the project deadline. " * 30
        content = "\n\n".join(paragraph for _ in range(4))
        pieces = split_into_chunks(content, target_tokens=200, overlap_ratio=0.15)
        self.assertGreater(len(pieces), 1)
        self.assertEqual([p.index for p in pieces], list(range(len(pieces))))
        # Overlap: the tail of chunk N appears at the head of chunk N+1.
        tail = pieces[0].text[-40:]
        self.assertIn(tail, pieces[1].text)


class EnvelopeTests(SimpleTestCase):
    def test_question_asked_roundtrip(self):
        envelope = parse_question_asked(
            {"schema_version": 1, "question_id": 7, "user_id": "abc-uuid"},
        )
        self.assertEqual(envelope.question_id, 7)
        self.assertEqual(envelope.user_id, "abc-uuid")

    def test_unknown_schema_version_is_malformed(self):
        with self.assertRaises(MalformedPayloadError):
            parse_question_asked(
                {"schema_version": 99, "question_id": 7, "user_id": "u"},
            )

    def test_missing_fields_are_malformed(self):
        with self.assertRaises(MalformedPayloadError):
            parse_note_embed_requested({"schema_version": 1, "note_id": 1})


class AskQuestionUseCaseTests(SimpleTestCase):
    def test_persists_question_and_emits_event_with_correlation(self):
        questions = FakeQuestionRepository()
        outbox = FakeOutbox()
        use_case = AskQuestionUseCase(questions=questions, outbox=outbox)

        question = use_case.execute(AskQuestionCommand(user_id="u-1", text=" hi "))

        self.assertEqual(question.text, "hi")
        [(topic, correlation_id, payload)] = outbox.events
        self.assertEqual(topic, "question.asked")
        self.assertEqual(correlation_id, "1")
        self.assertEqual(payload["user_id"], "u-1")
        self.assertEqual(payload["schema_version"], 1)


class AnswerQuestionUseCaseTests(SimpleTestCase):
    def _run(self, chunks, generated, deltas=()):
        questions = FakeQuestionRepository(
            question=Question(id=1, user_id="u-1", text="what?"),
        )
        generator = FakeGenerator(answer=generated, deltas=deltas)
        publisher = FakeDeltaPublisher()
        use_case = AnswerQuestionUseCase(
            questions=questions,
            search=FakeSearch(chunks),
            embedder=FakeEmbedder(),
            generator=generator,
            delta_publisher=publisher,
        )
        asyncio.run(
            use_case.execute(
                AnswerQuestionCommand(question_id=1, event_id="e-1", consumer="rag"),
            ),
        )
        return questions, generator, publisher

    def test_empty_retrieval_short_circuits_without_llm_call(self):
        questions, generator, publisher = self._run(chunks=[], generated=None)

        self.assertEqual(generator.calls, [])  # the LLM was never called
        self.assertEqual(publisher.published, [])  # and no deltas streamed
        [saved] = questions.saved
        self.assertEqual(saved["generated"].text, NO_SOURCES_MESSAGE)
        self.assertEqual(saved["generated"].cited_chunk_ids, ())

    def test_generates_and_persists_with_retrieved_chunks(self):
        chunk = RetrievedChunk(
            chunk_id=10,
            note_id=5,
            note_title="Plans",
            chunk_index=0,
            text="the plan",
            relevance_score=0.03,
        )
        generated = GeneratedAnswer(
            text="The plan is X.",
            cited_chunk_ids=(10,),
            model="gpt-test",
            prompt_tokens=11,
            completion_tokens=7,
        )
        questions, generator, _ = self._run(chunks=[chunk], generated=generated)

        self.assertEqual(len(generator.calls), 1)
        [saved] = questions.saved
        self.assertEqual(saved["generated"].cited_chunk_ids, (10,))
        self.assertEqual(saved["event_id"], "e-1")

    def test_deltas_published_in_seq_order(self):
        chunk = RetrievedChunk(
            chunk_id=10,
            note_id=5,
            note_title="Plans",
            chunk_index=0,
            text="the plan",
            relevance_score=0.03,
        )
        generated = GeneratedAnswer(
            text="Hello!",
            cited_chunk_ids=(10,),
            model="gpt-test",
            prompt_tokens=11,
            completion_tokens=7,
        )

        _, _, publisher = self._run(
            chunks=[chunk],
            generated=generated,
            deltas=("Hel", "lo", "!"),
        )

        self.assertEqual(
            publisher.published,
            [(1, 1, "Hel"), (1, 2, "lo"), (1, 3, "!")],
        )


class FakeNoteIndex:
    def __init__(self, *, content, content_hash, existing=None):
        self.content = content
        self.content_hash = content_hash
        self.existing = existing or {}
        self.replaced = []
        self.set_calls = []

    def get_content_and_hash(self, *, note_id):
        return self.content, self.content_hash

    def set_content_hash(self, *, note_id, content_hash):
        self.set_calls.append((note_id, content_hash))
        self.content_hash = content_hash

    async def aget_note_content(self, *, note_id):
        return self.content, self.content_hash

    async def aget_existing_chunk_hashes(self, *, note_id):
        return self.existing

    async def areplace_chunks(self, **kwargs):
        self.replaced.append(kwargs)


class RequestNoteIndexingUseCaseTests(SimpleTestCase):
    def test_unchanged_content_is_debounced(self):
        content = "Stable note body."
        index = FakeNoteIndex(content=content, content_hash=sha256_of(content))
        outbox = FakeOutbox()
        use_case = RequestNoteIndexingUseCase(notes_index=index, outbox=outbox)

        emitted = use_case.execute(note_id=1)

        self.assertFalse(emitted)
        self.assertEqual(outbox.events, [])
        self.assertEqual(index.set_calls, [])

    def test_changed_content_sets_hash_and_emits(self):
        index = FakeNoteIndex(content="New body.", content_hash="OLD")
        outbox = FakeOutbox()
        use_case = RequestNoteIndexingUseCase(notes_index=index, outbox=outbox)

        emitted = use_case.execute(note_id=7)

        self.assertTrue(emitted)
        expected_hash = sha256_of("New body.")
        self.assertEqual(index.set_calls, [(7, expected_hash)])
        [(topic, correlation_id, payload)] = outbox.events
        self.assertEqual(topic, "note.embed.requested")
        self.assertEqual(correlation_id, "7")
        self.assertEqual(payload["content_hash"], expected_hash)
        self.assertEqual(payload["note_id"], 7)
        self.assertEqual(payload["schema_version"], 1)


class ReindexNoteUseCaseTests(SimpleTestCase):
    def _use_case(self, index, embedder=None):
        return ReindexNoteUseCase(
            notes_index=index,
            embedder=embedder or FakeEmbedder(),
            embedding_model="test-model",
            embedding_version=1,
        )

    def test_stale_event_is_skipped(self):
        index = FakeNoteIndex(content="text", content_hash="CURRENT")
        use_case = self._use_case(index)

        asyncio.run(
            use_case.execute(ReindexNoteCommand(note_id=1, content_hash="OLD")),
        )

        self.assertEqual(index.replaced, [])

    def test_unchanged_chunks_are_not_re_embedded(self):
        content = "Stable paragraph."
        [piece] = split_into_chunks(content)
        index = FakeNoteIndex(
            content=content,
            content_hash="HASH",
            existing={piece.content_hash: 99},
        )
        embedder = FakeEmbedder()
        use_case = self._use_case(index, embedder)

        asyncio.run(
            use_case.execute(ReindexNoteCommand(note_id=1, content_hash="HASH")),
        )

        self.assertEqual(embedder.calls, [])  # zero API cost
        [replaced] = index.replaced
        self.assertEqual(replaced["embeddings"], {})
        self.assertEqual(len(replaced["pieces"]), 1)

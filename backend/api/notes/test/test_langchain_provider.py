"""Unit tests for the LangChain provider's pure streaming helper — no network.

extract_answer_delta diffs the "answer" field out of a growing partial-JSON
buffer (ADR-0007). Its contract: never raise mid-stream; "unparseable yet"
means "no new delta".
"""

from django.test import SimpleTestCase

from api.notes.infrastructure.langchain_provider import extract_answer_delta


class ExtractAnswerDeltaTests(SimpleTestCase):
    def test_monotonic_growth_yields_suffix_deltas(self):
        delta, cursor = extract_answer_delta('{"answer": "Hel', "")
        self.assertEqual((delta, cursor), ("Hel", "Hel"))

        delta, cursor = extract_answer_delta('{"answer": "Hello wor', cursor)
        self.assertEqual((delta, cursor), ("lo wor", "Hello wor"))

    def test_complete_json_emits_the_final_suffix(self):
        delta, cursor = extract_answer_delta(
            '{"answer": "Hi.", "cited_chunk_ids": [1, 2]}',
            "Hi",
        )
        self.assertEqual((delta, cursor), (".", "Hi."))

    def test_unparseable_prefixes_are_noops(self):
        for raw in ("", "not json", '{"answer"', "{"):
            delta, cursor = extract_answer_delta(raw, "kept")
            self.assertEqual((delta, cursor), ("", "kept"), msg=repr(raw))

    def test_unchanged_answer_is_a_noop(self):
        delta, cursor = extract_answer_delta('{"answer": "same', "same")
        self.assertEqual((delta, cursor), ("", "same"))

    def test_mid_escape_sequence_is_safe(self):
        delta, cursor = extract_answer_delta('{"answer": "He said \\"', "He said ")
        self.assertEqual((delta, cursor), ('"', 'He said "'))

    def test_non_monotonic_answer_resyncs_without_emitting(self):
        # Should not happen while accumulating one stream; if it does, the
        # append-only delta channel must not duplicate text.
        delta, cursor = extract_answer_delta('{"answer": "xyz"}', "abc")
        self.assertEqual((delta, cursor), ("", "xyz"))

    def test_non_dict_json_is_a_noop(self):
        delta, cursor = extract_answer_delta('["a", "b"]', "kept")
        self.assertEqual((delta, cursor), ("", "kept"))

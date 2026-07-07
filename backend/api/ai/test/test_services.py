import unittest

from api.ai import services


class LLMServicesTests(unittest.TestCase):
    def test_trim_text_truncates_and_keeps_end(self):
        long = "Line1\n" + "A" * 2000 + "\nEndLine"
        contexts = [{"note_id": 1, "chunk_index": 0, "text": long}]
        # Ensure OPENAI_API_KEY unset so fallback path is taken
        from django.conf import settings

        orig = getattr(settings, "OPENAI_API_KEY", None)
        if hasattr(settings, "OPENAI_API_KEY"):
            delattr(settings, "OPENAI_API_KEY")
        try:
            res = services.llm_summarize("Check trimming", contexts)
            self.assertIsInstance(res, dict)
            self.assertIn("answer", res)
            # trimmed text should be shorter than original and retain ends
            original_len = len(long)
            self.assertTrue(len(res["answer"]) < original_len)
            self.assertTrue(res["answer"].startswith("Line1"))
            self.assertIn("EndLine", res["answer"])
        finally:
            if orig is not None:
                setattr(settings, "OPENAI_API_KEY", orig)

    def test_llm_summarize_fallback_no_api_key(self):
        contexts = [
            {"note_id": 1, "chunk_index": 0, "text": "First note text."},
            {"note_id": 2, "chunk_index": 0, "text": "Second note text."},
        ]
        from django.conf import settings

        orig = getattr(settings, "OPENAI_API_KEY", None)
        if hasattr(settings, "OPENAI_API_KEY"):
            delattr(settings, "OPENAI_API_KEY")
        try:
            res = services.llm_summarize("What did I plan?", contexts)
            self.assertIsInstance(res, dict)
            self.assertIn("answer", res)
            self.assertIn("sources", res)
            self.assertTrue("First note text." in res["answer"])
        finally:
            if orig is not None:
                setattr(settings, "OPENAI_API_KEY", orig)

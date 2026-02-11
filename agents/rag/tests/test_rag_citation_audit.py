import importlib
import os
import sys
import unittest
from pathlib import Path


class RAGCitationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = {
            "EMBEDDING_TIMEOUT": "30",
            "NEO4J_TIMEOUT": "15",
            "LLM_TIMEOUT": "120",
            "LLM_MAX_RETRIES": "3",
            "EMBEDDING_MAX_RETRIES": "3",
            "NEO4J_MAX_RETRIES": "3",
            "MAX_QUERY_LENGTH": "10000",
            "LLM_CONCURRENCY": "2",
        }
        for key, value in required.items():
            os.environ.setdefault(key, value)

        rag_dir = Path(__file__).resolve().parents[1]
        if str(rag_dir) not in sys.path:
            sys.path.insert(0, str(rag_dir))

        try:
            cls.mod = importlib.import_module("rag_analysis")
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Missing optional dependency: {exc}")

    def test_citation_audit_valid_and_invalid(self):
        answer = "Result from [chunk_1] and [chunk_2], but [fake_9] is wrong."
        audit = self.mod.RAGAnalysis._citation_audit(answer, {"chunk_1", "chunk_2"})
        self.assertEqual(audit["valid_count"], 2)
        self.assertIn("fake_9", audit["invalid_ids"])
        self.assertEqual(audit["cited_count"], 3)


if __name__ == "__main__":
    unittest.main()

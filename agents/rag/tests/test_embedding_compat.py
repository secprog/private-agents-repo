import importlib
import math
import os
import sys
import unittest
from pathlib import Path


class EmbeddingCompatTests(unittest.TestCase):
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

    def test_validate_probe_embedding_rejects_non_finite(self):
        with self.assertRaises(RuntimeError):
            self.mod.RAGAnalysis._validate_probe_embedding([1.0, math.nan], "test-model")

    def test_validate_probe_embedding_rejects_zero_norm(self):
        with self.assertRaises(RuntimeError):
            self.mod.RAGAnalysis._validate_probe_embedding([0.0, 0.0, 0.0], "test-model")

    def test_validate_probe_embedding_returns_dimension(self):
        dim = self.mod.RAGAnalysis._validate_probe_embedding([0.1, 0.2, 0.3], "test-model")
        self.assertEqual(dim, 3)


if __name__ == "__main__":
    unittest.main()

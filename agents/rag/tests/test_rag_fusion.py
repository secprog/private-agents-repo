import importlib
import os
import sys
import unittest
from pathlib import Path


class RAGFusionTests(unittest.TestCase):
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

    def test_score_aware_rrf_is_deterministic(self):
        analyzer = object.__new__(self.mod.RAGAnalysis)
        ranked_lists = {
            "semantic": [
                {"id": "c2", "score": 0.70, "text": "b"},
                {"id": "c1", "score": 0.70, "text": "a"},
            ],
            "lexical": [
                {"id": "c1", "score": 3.2, "text": "a"},
                {"id": "c2", "score": 3.2, "text": "b"},
            ],
        }
        weights = {"semantic": 1.2, "lexical": 1.0}
        out1 = analyzer._score_aware_rrf(ranked_lists, weights=weights, top_k=5)
        out2 = analyzer._score_aware_rrf(ranked_lists, weights=weights, top_k=5)
        self.assertEqual([row["id"] for row in out1], [row["id"] for row in out2])

    def test_confidence_monotonicity(self):
        source_map = {
            "c1": {"semantic", "lexical", "graph"},
            "c2": {"semantic"},
            "c3": {"semantic"},
        }
        confident_docs = [
            {"id": "c1", "bm25_score": 1.0},
            {"id": "c2", "bm25_score": 0.2},
            {"id": "c3", "bm25_score": 0.1},
        ]
        flat_docs = [
            {"id": "c1", "bm25_score": 0.4},
            {"id": "c2", "bm25_score": 0.39},
            {"id": "c3", "bm25_score": 0.38},
        ]

        c1 = self.mod.RAGAnalysis._compute_confidence(
            confident_docs,
            source_map,
            score_key_candidates=["bm25_score", "rrf_score", "score"],
        )
        c2 = self.mod.RAGAnalysis._compute_confidence(
            flat_docs,
            source_map,
            score_key_candidates=["bm25_score", "rrf_score", "score"],
        )
        self.assertGreater(c1, c2)


if __name__ == "__main__":
    unittest.main()

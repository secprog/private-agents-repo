"""
RAG Analysis Module - Document retrieval and knowledge extraction
"""

import os
import logging
import json
import asyncio
import collections
import math
import re
import time
import hashlib
from typing import List, Dict, Any
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from google.adk.models import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
import litellm
from transformers import AutoTokenizer
from models import (
    VectorSearchResponse,
    HydeSearchResponse,
    HybridSearchResponse,
    LexicalSearchResponse,
    GraphSearchResponse,
    EntityExtractionResponse,
    GraphBasedRetrievalResponse,
    GraphRagAnswerResponse,
    BM25RerankResponse,
    CrossEncoderRerankResponse,
    RRFResponse,
    QueryExpansionResponse,
    ChunkContextResponse,
    SearchResult,
    ErrorResponse,
    CommunityRetrievalResponse,
    PayloadSearchResponse,
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} env-var missing")
    return value


def _require_positive_int_env(name: str) -> int:
    value = _require_env(name)
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got: {value}") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be > 0, got: {parsed}")
    return parsed


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        val = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got: {raw}") from exc
    if val < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got: {val}")
    return val


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name, str(default))
    try:
        val = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number, got: {raw}") from exc
    if val < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got: {val}")
    return val


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    raise RuntimeError(
        f"{name} must be boolean string true/false/1/0/yes/no, got: {raw}"
    )


# Timeout and sizing configuration (strict env-only)
EMBEDDING_TIMEOUT = _require_positive_int_env("EMBEDDING_TIMEOUT")
NEO4J_TIMEOUT = _require_positive_int_env("NEO4J_TIMEOUT")
LLM_TIMEOUT = _require_positive_int_env("LLM_TIMEOUT")
LLM_MAX_RETRIES = _require_positive_int_env("LLM_MAX_RETRIES")
EMBEDDING_MAX_RETRIES = _require_positive_int_env("EMBEDDING_MAX_RETRIES")
NEO4J_MAX_RETRIES = _require_positive_int_env("NEO4J_MAX_RETRIES")
MAX_QUERY_LEN = _require_positive_int_env("MAX_QUERY_LENGTH")
LLM_CONCURRENCY = _require_positive_int_env("LLM_CONCURRENCY")
RRF_K = _env_int("RRF_K", 40)
RRF_SCORE_ALPHA = _env_float("RRF_SCORE_ALPHA", 0.25, minimum=0.0)
LOW_CONFIDENCE_SCORE_GAP = _env_float("LOW_CONFIDENCE_SCORE_GAP", 0.004, minimum=0.0)
LOW_CONFIDENCE_THRESHOLD = _env_float("LOW_CONFIDENCE_THRESHOLD", 0.62, minimum=0.0)
CROSS_ENCODER_MAX_DOCS = _env_int("CROSS_ENCODER_MAX_DOCS", 12)
CROSS_ENCODER_CONCURRENCY = _env_int("CROSS_ENCODER_CONCURRENCY", 4)
MAX_CONTEXT_TOKENS = _env_int("MAX_CONTEXT_TOKENS", 12000)
CONTEXT_MIN_SOURCES = _env_int("CONTEXT_MIN_SOURCES", 2)
CONTEXT_CANDIDATE_MULTIPLIER = _env_int("CONTEXT_CANDIDATE_MULTIPLIER", 4)
EMBEDDING_INPUT_MAX_CHARS = _env_int("EMBEDDING_INPUT_MAX_CHARS", 8000)
LUCENE_ESCAPE_ENABLED = _env_bool("LUCENE_ESCAPE_ENABLED", True)
ENTITY_FUZZY_FALLBACK = _env_bool("ENTITY_FUZZY_FALLBACK", True)
CITATION_REPAIR_ENABLED = _env_bool("CITATION_REPAIR_ENABLED", True)
DEBUG_RETRIEVAL_METRICS = _env_bool("DEBUG_RETRIEVAL_METRICS", False)
ENTITY_FUZZY_EDIT_DISTANCE = _env_int("ENTITY_FUZZY_EDIT_DISTANCE", 1)
MIN_CITATIONS = _env_int("MIN_CITATIONS", 2)
TOKENIZER_HF_MODEL = _require_env("LLM_MODEL").strip()
TOKENIZER_HF_USE_FAST = _env_bool("TOKENIZER_HF_USE_FAST", True)
TOKENIZER_HF_TRUST_REMOTE_CODE = _env_bool("TOKENIZER_HF_TRUST_REMOTE_CODE", False)
TOKENIZER_HF_REVISION = os.getenv("TOKENIZER_HF_REVISION", "").strip() or None
_TOKENIZER_CACHE: Dict[str, Any] = {"tokenizer": None}


def _get_runtime_tokenizer():
    tok = _TOKENIZER_CACHE.get("tokenizer")
    if tok is not None:
        return tok
    kwargs: Dict[str, Any] = {
        "use_fast": TOKENIZER_HF_USE_FAST,
        "trust_remote_code": TOKENIZER_HF_TRUST_REMOTE_CODE,
    }
    if TOKENIZER_HF_REVISION:
        kwargs["revision"] = TOKENIZER_HF_REVISION
    try:
        tok = AutoTokenizer.from_pretrained(TOKENIZER_HF_MODEL, **kwargs)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load tokenizer for LLM_MODEL '{TOKENIZER_HF_MODEL}'."
        ) from exc
    _TOKENIZER_CACHE["tokenizer"] = tok
    return tok


class LiteLLMEmbeddings:
    """Embeddings using LiteLLM."""

    def __init__(self):
        api_base = os.getenv("LITELLM_API_BASE")
        api_version = os.getenv("LITELLM_API_VERSION")
        api_key = os.getenv("LITELLM_API_KEY")
        self.model = _require_env("LITELLM_EMBEDDING_MODEL")

        self.api_key = api_key
        self.api_base = api_base
        self.api_version = api_version
        logger.info(f"LiteLLM Embeddings initialized with model: {self.model}")

    @staticmethod
    def _normalize_embedding_input(text: str) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").strip())
        if len(normalized) > EMBEDDING_INPUT_MAX_CHARS:
            normalized = normalized[:EMBEDDING_INPUT_MAX_CHARS]
        return normalized

    async def embed_query(self, text: str):
        """Generate embedding for a single query text with retry and timeout."""
        normalized_text = self._normalize_embedding_input(text)
        kwargs: Dict[str, Any] = {"model": self.model, "input": [normalized_text]}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if self.api_version:
            kwargs["api_version"] = self.api_version
        max_retries = EMBEDDING_MAX_RETRIES
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    litellm.aembedding(**kwargs),
                    timeout=EMBEDDING_TIMEOUT,
                )
                return response.data[0]["embedding"]
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Embedding attempt {attempt+1} failed: {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Embedding failed after {max_retries} attempts: {e}")
                    raise


class Neo4jConnection:
    """Neo4j database connection for graph and vector operations."""

    def __init__(self):
        self.uri = _require_env("NEO4J_URI")
        self.user = _require_env("NEO4J_USERNAME")
        self.password = _require_env("NEO4J_PASSWORD")
        self.database = _require_env("NEO4J_DATABASE")

        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            logger.info(f"Neo4j connection initialized: {self.database}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Neo4j driver: {e}") from e

    async def query(self, cypher, params=None):
        """Execute a Cypher query and return results without blocking the event loop."""
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized")

        max_retries = NEO4J_MAX_RETRIES
        for attempt in range(max_retries):
            try:
                async with self.driver.session(database=self.database) as session:
                    async def _run_and_collect():
                        result = await session.run(cypher, params or {})
                        return [dict(record) async for record in result]

                    return await asyncio.wait_for(
                        _run_and_collect(),
                        timeout=NEO4J_TIMEOUT,
                    )
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Neo4j query timed out (attempt {attempt + 1}), retrying in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise RuntimeError(
                        f"Neo4j query timed out after {max_retries} attempts"
                    ) from None
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Neo4j query failed (attempt {attempt + 1}): {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise RuntimeError(
                        f"Neo4j query failed after {max_retries} attempts: {e}"
                    ) from e
        raise RuntimeError("Neo4j query failed for unknown reason")

    async def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            try:
                await self.driver.close()
                logger.info("Neo4j connection closed")
            finally:
                self.driver = None


def _text_overlap_ratio(a: str, b: str) -> float:
    """Compute token-level overlap ratio between two texts (Jaccard similarity)."""
    if not a or not b:
        return 0.0
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union


def _lucene_escape(text: str) -> str:
    if not LUCENE_ESCAPE_ENABLED:
        return text
    return re.sub(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)', r"\\\1", text or "")


def _normalize_query_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _build_lucene_query(text: str) -> str:
    normalized = _normalize_query_text(text)
    if not normalized:
        return ""
    quoted_phrases = re.findall(r'"([^"]+)"', normalized)
    remainder = re.sub(r'"[^"]+"', " ", normalized)
    terms = [t for t in re.split(r"\s+", remainder) if t]
    parts: list[str] = []
    for phrase in quoted_phrases:
        clean = _normalize_query_text(phrase)
        if clean:
            parts.append(f"\"{_lucene_escape(clean)}\"")
    for term in terms:
        parts.append(_lucene_escape(term))
    if not parts:
        return _lucene_escape(normalized)
    return " OR ".join(parts)


def _build_entity_fuzzy_query(entities: list[str]) -> str:
    terms: list[str] = []
    for ent in entities:
        tokens = re.findall(r"[A-Za-z0-9_]+", ent or "")
        for token in tokens:
            if len(token) < 3:
                continue
            fuzz = 2 if len(token) >= 9 else ENTITY_FUZZY_EDIT_DISTANCE
            terms.append(f"{_lucene_escape(token)}~{fuzz}")
    return " OR ".join(terms[:20])


class RAGAnalysis:
    """RAG analysis tools for document retrieval and knowledge extraction."""

    _CACHE_TTL = 300  # 5 minutes
    _CACHE_MAX = 128

    def __init__(self):
        self.llm = LiteLlm(model=_require_env("LLM_MODEL"))
        self.embeddings = LiteLLMEmbeddings()
        self.neo4j = Neo4jConnection()
        self._expansion_cache: Dict[str, Dict] = (
            {}
        )  # key -> {"t": timestamp, "v": result}
        self._hyde_cache: Dict[str, Dict] = (
            {}
        )  # query -> {"t": timestamp, "v": hypothetical_doc}
        self._entity_cache: Dict[str, Dict] = (
            {}
        )  # text_hash -> {"t": timestamp, "v": result}
        self._llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
        self._cross_encoder_semaphore = asyncio.Semaphore(CROSS_ENCODER_CONCURRENCY)
        self._embedding_compat_checked = False
        self._embedding_compat_lock = asyncio.Lock()
        logger.info("RAGAnalysis initialized")

    def _cache_get(self, cache: Dict[str, Dict], key: str):
        """Get a value from a TTL cache, or None if missing/expired."""
        entry = cache.get(key)
        if entry and (time.time() - entry["t"]) < self._CACHE_TTL:
            return entry["v"]
        return None

    def _cache_put(self, cache: Dict[str, Dict], key: str, value):
        """Put a value into a TTL cache with LRU eviction."""
        if len(cache) >= self._CACHE_MAX:
            oldest = min(cache, key=lambda k: cache[k]["t"])
            del cache[oldest]
        cache[key] = {"t": time.time(), "v": value}

    @staticmethod
    def _normalize_scores(results: List[Dict], score_key: str = "score") -> List[Dict]:
        """Normalize scores to 0-1 range using min-max within a result list."""
        if not results:
            return results
        scores = [r.get(score_key, 0) for r in results]
        min_s, max_s = min(scores), max(scores)
        span = max_s - min_s
        if span == 0:
            return results
        normalized = []
        for r in results:
            r_copy = r.copy()
            r_copy[score_key] = (r.get(score_key, 0) - min_s) / span
            normalized.append(r_copy)
        return normalized

    @staticmethod
    def _safe_json_loads(payload: str) -> Dict[str, Any]:
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    @staticmethod
    def _validate_probe_embedding(probe: List[float], model_name: str) -> int:
        if not probe:
            raise RuntimeError("Embedding probe returned an empty vector.")
        if not all(math.isfinite(float(v)) for v in probe):
            raise RuntimeError(
                f"Embedding probe contains non-finite values (model={model_name})"
            )
        norm = math.sqrt(sum(float(v) * float(v) for v in probe))
        if not math.isfinite(norm) or norm <= 0:
            raise RuntimeError(
                f"Embedding probe has invalid norm (must be finite and > 0) (model={model_name})"
            )
        return len(probe)

    async def _ensure_embedding_compatibility(self) -> None:
        if self._embedding_compat_checked:
            return
        async with self._embedding_compat_lock:
            if self._embedding_compat_checked:
                return
            probe = await self.embeddings.embed_query("dimension probe")
            probe_dim = self._validate_probe_embedding(probe, self.embeddings.model)
            runtime_deployment = self.embeddings.model
            cfg_rows = await self.neo4j.query(
                """
                MATCH (cfg:__EmbeddingConfig__ {id:'active'})
                RETURN cfg.model AS model, cfg.deployment AS deployment, cfg.dimension AS dimension
                LIMIT 1
                """
            )
            if cfg_rows:
                cfg = cfg_rows[0]
                reasons: List[str] = []
                cfg_dim = cfg.get("dimension")
                try:
                    cfg_dim_int = int(cfg_dim) if cfg_dim is not None else None
                except (TypeError, ValueError):
                    cfg_dim_int = None
                if cfg_dim_int is not None and cfg_dim_int != probe_dim:
                    reasons.append(f"config_dim={cfg_dim_int} probe_dim={probe_dim}")
                cfg_model = cfg.get("model")
                cfg_deployment = cfg.get("deployment")
                if cfg_model and str(cfg_model) != str(self.embeddings.model):
                    reasons.append(
                        f"config_model={cfg_model} runtime_model={self.embeddings.model}"
                    )
                if cfg_deployment and runtime_deployment and str(cfg_deployment) != str(
                    runtime_deployment
                ):
                    reasons.append(
                        f"config_deployment={cfg_deployment} runtime_deployment={runtime_deployment}"
                    )
                if reasons:
                    raise RuntimeError(
                        "Embedding config handshake mismatch: " + "; ".join(reasons)
                    )
            idx_rows = await self.neo4j.query(
                """
                SHOW INDEXES
                YIELD name, type, options
                WHERE type='VECTOR'
                  AND name IN ['chunk_embedding_index', 'payload_embedding_index']
                RETURN name, options
                """
            )
            for row in idx_rows:
                options = row.get("options") or {}
                cfg = options.get("indexConfig") if isinstance(options, dict) else {}
                dim_raw = cfg.get("vector.dimensions") if isinstance(cfg, dict) else None
                if dim_raw is None:
                    continue
                try:
                    idx_dim = int(dim_raw)
                except (TypeError, ValueError):
                    continue
                if idx_dim != probe_dim:
                    raise RuntimeError(
                        "Embedding/index dimension mismatch: "
                        f"index={row.get('name')} index_dim={idx_dim} probe_dim={probe_dim}, "
                        f"model={self.embeddings.model}"
                    )
            self._embedding_compat_checked = True

    async def verify_runtime(self) -> None:
        """Fail fast on critical runtime mismatches before serving requests."""
        await self._ensure_embedding_compatibility()

    @staticmethod
    def _normalize_entity_token(ent: str) -> str:
        cleaned = re.sub(r"\s+", " ", (ent or "").strip())
        return cleaned.strip(".,;:()[]{}\"'")

    def _score_aware_rrf(
        self,
        ranked_lists: Dict[str, List[Dict[str, Any]]],
        *,
        weights: Dict[str, float],
        top_k: int,
        k: int = RRF_K,
        alpha: float = RRF_SCORE_ALPHA,
    ) -> List[Dict[str, Any]]:
        rrf_scores: Dict[str, float] = {}
        source_counts: Dict[str, int] = {}
        lexical_scores: Dict[str, float] = {}
        all_docs: Dict[str, Dict[str, Any]] = {}
        source_contribs: Dict[str, Dict[str, float]] = {}

        for source_name, docs in ranked_lists.items():
            if not isinstance(docs, list) or not docs:
                continue
            weight = float(weights.get(source_name, 1.0))
            normalized_docs = self._normalize_scores(docs, "score")
            norm_by_id: Dict[str, float] = {}
            for d in normalized_docs:
                if not isinstance(d, dict) or not d.get("id"):
                    continue
                try:
                    norm_by_id[d["id"]] = float(d.get("score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    norm_by_id[d["id"]] = 0.0
            def _safe_score(doc: Dict[str, Any]) -> float:
                try:
                    return float(doc.get("score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            sorted_docs = sorted(
                docs,
                key=lambda d: _safe_score(d) if isinstance(d, dict) else 0.0,
                reverse=True,
            )
            for rank, doc in enumerate(sorted_docs, start=1):
                if not isinstance(doc, dict):
                    continue
                doc_id = doc.get("id")
                if not doc_id:
                    continue
                contribution = weight * (
                    ((1.0 - alpha) * (1.0 / (k + rank)))
                    + (alpha * norm_by_id.get(doc_id, 0.0))
                )
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + contribution
                source_counts[doc_id] = source_counts.get(doc_id, 0) + 1
                if source_name == "lexical":
                    lexical_scores[doc_id] = max(
                        lexical_scores.get(doc_id, 0.0),
                        float(doc.get("score", 0.0) or 0.0),
                    )
                all_docs.setdefault(doc_id, doc)
                source_contribs.setdefault(doc_id, {})[source_name] = contribution

        ranked_ids = sorted(
            rrf_scores.keys(),
            key=lambda doc_id: (
                -rrf_scores.get(doc_id, 0.0),
                -source_counts.get(doc_id, 0),
                -lexical_scores.get(doc_id, 0.0),
                doc_id,
            ),
        )
        fused = []
        for doc_id in ranked_ids:
            if len(fused) >= top_k:
                break
            doc = all_docs.get(doc_id, {}).copy()
            doc["rrf_score"] = round(rrf_scores[doc_id], 6)
            doc["source_contributions"] = {
                src: round(val, 6) for src, val in source_contribs.get(doc_id, {}).items()
            }
            fused.append(doc)
        return fused

    @staticmethod
    def _token_count(text: str, model_name: str) -> int:
        _ = model_name
        raw = text or ""
        if not raw.strip():
            return 0
        tok = _get_runtime_tokenizer()
        encoded = tok(raw, add_special_tokens=False, truncation=False)
        return len(encoded.get("input_ids", []))

    def _select_diverse_rows(
        self, ranked_rows: List[Dict[str, Any]], source_map: Dict[str, set[str]], top_k: int
    ) -> List[Dict[str, Any]]:
        selected: List[Dict[str, Any]] = []
        seen_sources: set[str] = set()
        for row in ranked_rows:
            cid = row.get("id")
            if not cid:
                continue
            srcs = source_map.get(cid, set())
            if srcs - seen_sources and len(seen_sources) < CONTEXT_MIN_SOURCES:
                selected.append(row)
                seen_sources.update(srcs)
            if len(seen_sources) >= CONTEXT_MIN_SOURCES:
                break
        for row in ranked_rows:
            if len(selected) >= top_k:
                break
            if row in selected:
                continue
            selected.append(row)
        return selected[:top_k]

    @staticmethod
    def _compute_confidence(
        ranked_docs: List[Dict[str, Any]],
        source_map: Dict[str, set[str]],
        *,
        score_key_candidates: List[str],
    ) -> float:
        if not ranked_docs:
            return 0.0
        top_docs = ranked_docs[:5]
        top_scores = []
        for doc in top_docs:
            score = 0.0
            for key in score_key_candidates:
                try:
                    score = float(doc.get(key, 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                if score:
                    break
            top_scores.append(max(0.0, score))
        if not top_scores:
            return 0.0
        top1 = top_scores[0]
        top5 = top_scores[-1]
        gap = max(0.0, top1 - top5)
        gap_norm = min(1.0, gap / 0.03)

        agreement_vals = []
        for doc in top_docs:
            cid = doc.get("id")
            if not cid:
                continue
            agreement_vals.append(min(1.0, len(source_map.get(cid, set())) / 3.0))
        source_agreement = (
            sum(agreement_vals) / len(agreement_vals) if agreement_vals else 0.0
        )

        total = sum(top_scores)
        if total <= 0:
            entropy_norm = 0.0
        else:
            probs = [s / total for s in top_scores if s > 0]
            entropy = -sum(p * math.log(p + 1e-12) for p in probs)
            max_entropy = math.log(len(top_scores)) if len(top_scores) > 1 else 1.0
            entropy_norm = 1.0 - min(1.0, entropy / max_entropy)
        confidence = (0.45 * gap_norm) + (0.35 * source_agreement) + (0.20 * entropy_norm)
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _citation_audit(answer_text: str, allowed_ids: set[str]) -> Dict[str, Any]:
        cited = set(re.findall(r"\[([^\]]+)\]", answer_text or ""))
        valid = sorted(cited & allowed_ids)
        invalid = sorted(cited - allowed_ids)
        return {
            "cited_count": len(cited),
            "valid_count": len(valid),
            "invalid_ids": invalid,
            "meets_minimum": len(valid) >= min(MIN_CITATIONS, len(allowed_ids)),
        }

    @staticmethod
    def _filter_entities(entities: List[str], max_count: int = 20) -> List[str]:
        """Filter and deduplicate extracted entities."""
        seen: set = set()
        filtered: List[str] = []
        for ent in entities:
            ent = ent.strip()
            if len(ent) < 2 or len(ent) > 80:
                continue
            key = ent.lower()
            if key in seen:
                continue
            seen.add(key)
            filtered.append(ent)
            if len(filtered) >= max_count:
                break
        return filtered

    @staticmethod
    def _extract_cypher(text: str) -> str:
        candidate = (text or "").strip()
        code_block = re.search(
            r"```(?:cypher)?\s*(.*?)\s*```", candidate, re.DOTALL | re.IGNORECASE
        )
        if code_block:
            candidate = code_block.group(1).strip()
        return candidate.rstrip(";")

    @staticmethod
    def _is_read_only_cypher(cypher: str) -> bool:
        # Block explicit write keywords
        write_ops = re.compile(
            r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD\s+CSV)\b",
            re.IGNORECASE,
        )
        if write_ops.search(cypher):
            return False
        # Block CALL { ... } subqueries (can embed writes)
        if re.search(r"\bCALL\s*\{", cypher, re.IGNORECASE):
            return False
        # For CALL statements, only allow known read-only procedures
        allowed_calls = re.compile(
            r"\bCALL\s+db\.index\.(fulltext\.queryNodes|vector\.queryNodes)\b",
            re.IGNORECASE,
        )
        for call_match in re.finditer(r"\bCALL\s+[\w.]+", cypher, re.IGNORECASE):
            if not allowed_calls.match(call_match.group(0)):
                return False
        return True

    async def _llm_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_output_tokens: int = 800,
        response_mime_type: str | None = None,
    ) -> str:
        config_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type

        content = types.Content(role="user", parts=[types.Part(text=prompt)])
        llm_request = LlmRequest(
            model=self.llm.model,
            contents=[content],
            config=types.GenerateContentConfig(**config_kwargs),
        )

        async def _run_request() -> str:
            out = ""
            async for resp in self.llm.generate_content_async(llm_request):
                if resp.content and resp.content.parts:
                    for part in resp.content.parts:
                        if hasattr(part, "text") and part.text:
                            out += part.text
            return out.strip()

        for attempt in range(LLM_MAX_RETRIES):
            try:
                async with self._llm_semaphore:
                    return await asyncio.wait_for(
                        _run_request(),
                        timeout=LLM_TIMEOUT,
                    )
            except Exception as e:
                if attempt < LLM_MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        f"LLM text attempt {attempt + 1} failed: {e}, retrying in {wait}s"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"LLM text failed after {LLM_MAX_RETRIES} attempts: {e}"
                    )
                    raise
        return ""

    async def vector_search(
        self, search_query: str, top_k: int = 10, min_score: float = 0.0
    ) -> str:
        """
        Search for documents using semantic similarity.

        Args:
            search_query: Query string to search for
            top_k: Number of results to return
            min_score: Minimum similarity score threshold (0.0-1.0). Results below this are excluded.

        Returns:
            JSON string with search results
        """
        if len(search_query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(search_query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(
                f"Vector search: '{search_query[:100]}' (top_k={top_k}, min_score={min_score})"
            )
            await self._ensure_embedding_compatibility()

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            # Generate embedding for query
            embedding = await self.embeddings.embed_query(search_query)

            # Search for similar documents
            cypher = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            ORDER BY score DESC
            """
            results = await self.neo4j.query(
                cypher, {"k": top_k, "embedding": embedding}
            )

            if not results:
                return VectorSearchResponse(
                    results=[], count=0, query=search_query
                ).model_dump_json()

            if min_score > 0:
                results = [r for r in results if r.get("score", 0) >= min_score]

            items = [
                SearchResult(
                    id=r["id"], text=r.get("text", ""), score=r.get("score", 0)
                )
                for r in results
            ]
            return VectorSearchResponse(
                results=items, count=len(items), query=search_query
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def hyde_search(
        self, search_query: str, top_k: int = 10, min_score: float = 0.0
    ) -> str:
        """
        Search using Hypothetical Document Embeddings (HyDE).

        Instead of embedding the raw query, this asks the LLM to generate a
        hypothetical passage that would answer the query, then embeds that
        passage for vector search. This bridges the vocabulary gap between
        short questions and long-form document text, improving recall by 10-20%.

        Best for: complex, conceptual, or abstract questions where direct
        query embedding may miss relevant documents.

        Args:
            search_query: Natural language query
            top_k: Number of results to return
            min_score: Minimum similarity score threshold (0.0-1.0). Results below this are excluded.

        Returns:
            JSON string with search results including the hypothetical document used.
        """
        if len(search_query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(search_query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(
                f"HyDE search: '{search_query[:100]}' (top_k={top_k}, min_score={min_score})"
            )
            await self._ensure_embedding_compatibility()

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            # Check cache for hypothetical document (LLM generation is the expensive part)
            hyde_cache_key = hashlib.sha256(search_query.strip().lower().encode()).hexdigest()
            hypothetical_doc = self._cache_get(self._hyde_cache, hyde_cache_key)

            if hypothetical_doc is None:
                prompt = f"""Write a short, factual paragraph (3-5 sentences) that directly answers the following question. Write it as if it were an excerpt from a real document. Do not include phrases like "this document" or "according to". Just state the information plainly.

Question: {search_query}

Paragraph:"""
                hypothetical_doc = await self._llm_text(
                    prompt,
                    temperature=0.0,
                    max_output_tokens=300,
                )

                if not hypothetical_doc.strip():
                    raise RuntimeError(
                        "HyDE generation returned empty response; cannot continue"
                    )

                self._cache_put(
                    self._hyde_cache, hyde_cache_key, hypothetical_doc.strip()
                )
            else:
                logger.info("HyDE cache hit")

            # Embed the hypothetical document instead of the raw query
            embedding = await self.embeddings.embed_query(hypothetical_doc.strip())

            cypher = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            ORDER BY score DESC
            """
            results = await self.neo4j.query(
                cypher, {"k": top_k, "embedding": embedding}
            )

            if not results:
                return HydeSearchResponse(
                    results=[], count=0, hypothetical_document=hypothetical_doc.strip()
                ).model_dump_json()

            if min_score > 0:
                results = [r for r in results if r.get("score", 0) >= min_score]

            items = [
                SearchResult(
                    id=r["id"], text=r.get("text", ""), score=r.get("score", 0)
                )
                for r in results
            ]
            return HydeSearchResponse(
                results=items,
                count=len(items),
                hypothetical_document=hypothetical_doc.strip(),
            ).model_dump_json()

        except Exception as e:
            logger.error(f"HyDE search failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def graph_search(self, search_query: str) -> str:
        """
        Search structured data using natural language converted to Cypher.

        Args:
            search_query: Natural language query

        Returns:
            JSON string with search results
        """
        if len(search_query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(search_query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(f"Graph search: '{search_query[:100]}'")

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            prompt = (
                "Generate a read-only Cypher query for Neo4j to answer this question.\n"
                "Only use MATCH/OPTIONAL MATCH/WITH/RETURN/ORDER BY/LIMIT/CALL for read operations.\n"
                "Never use CREATE, MERGE, DELETE, DETACH, SET, REMOVE, DROP, FOREACH, or LOAD CSV.\n\n"
                "Graph schema:\n"
                "  Node labels: __Chunk__, __Entity__, __Community__, __Document__, __Payload__\n"
                "  Relationships: MENTIONS (Chunk->Entity), PART_OF (Chunk->Document), "
                "IN_COMMUNITY (Entity->Community), HAS_PAYLOAD (Chunk->Payload), REL (Entity->Entity)\n"
                "  Properties: __Chunk__(text, id, chunk_index), __Entity__(name, description), "
                "__Community__(title, summary), __Document__(id)\n\n"
                f"Question: {search_query}\n\n"
                "Return ONLY the Cypher query."
            )

            response_text = await self._llm_text(
                prompt,
                temperature=0.1,
                max_output_tokens=500,
            )
            if not response_text:
                return ErrorResponse(error="Failed to generate query").model_dump_json()

            cypher = self._extract_cypher(response_text)
            if not cypher:
                return ErrorResponse(error="Generated query was empty").model_dump_json()
            if not self._is_read_only_cypher(cypher):
                return ErrorResponse(
                    error="Blocked non-read-only Cypher query",
                    details={"query": cypher},
                ).model_dump_json()

            results = await self.neo4j.query(cypher)

            return GraphSearchResponse(
                query=cypher, results=results, count=len(results)
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def detect_entities(self, text: str) -> str:
        """
        Extract named entities from text using LLM.

        Args:
            text: Text to extract entities from

        Returns:
            JSON string with extracted entities
        """
        if len(text) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Text too long ({len(text)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(f"Detecting entities in text (length: {len(text)})")

            # Check cache by text hash
            entity_cache_key = hashlib.sha256(text.strip().lower().encode()).hexdigest()
            cached = self._cache_get(self._entity_cache, entity_cache_key)
            if cached is not None:
                logger.info("Entity detection cache hit")
                return cached

            prompt = f"""Extract all named entities from the text below. Include people, organizations, locations, products, technologies, and domain-specific terms.

Text: {text}

Return ONLY a JSON array with entity names, e.g.: ["Entity1", "Entity2"]
Do not include any explanation, just the JSON array."""

            response_text = await self._llm_text(
                prompt,
                temperature=0.0,
                max_output_tokens=1000,
            )

            if not response_text:
                raise RuntimeError("Entity detection returned empty response")

            try:
                entities = json.loads(response_text.strip())
            except json.JSONDecodeError:
                raise RuntimeError(
                    "Entity detection did not return valid JSON array"
                ) from None
            if not isinstance(entities, list):
                raise RuntimeError("Entity detection output is not a JSON list")
            entities = self._filter_entities(entities)
            result = EntityExtractionResponse(
                entities=entities, count=len(entities), text_preview=text[:200]
            ).model_dump_json()

            self._cache_put(self._entity_cache, entity_cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Entity detection failed: {e}")
            return ErrorResponse(error=str(e), details={"entities": []}).model_dump_json()

    async def lexical_search(
        self, search_query: str, top_k: int = 10, min_score: float = 0.0
    ) -> str:
        """
        Search for documents using full-text lexical matching.

        Args:
            search_query: Query string (supports Lucene query syntax)
            top_k: Number of results to return
            min_score: Minimum relevance score threshold. Results below this are excluded.

        Returns:
            JSON string with search results ranked by text relevance
        """
        if len(search_query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(search_query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(
                f"Lexical search: '{search_query[:100]}' (top_k={top_k}, min_score={min_score})"
            )

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            cypher = """
            CALL db.index.fulltext.queryNodes('chunk_text_ft', $query)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            LIMIT $limit
            """
            results = await self.neo4j.query(
                cypher, {"query": _build_lucene_query(search_query), "limit": top_k}
            )

            if not results:
                return LexicalSearchResponse(
                    results=[], count=0, query=search_query
                ).model_dump_json()

            if min_score > 0:
                results = [r for r in results if r.get("score", 0) >= min_score]

            items = [
                SearchResult(
                    id=r["id"], text=r.get("text", ""), score=r.get("score", 0)
                )
                for r in results
            ]
            return LexicalSearchResponse(
                results=items, count=len(items), query=search_query
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def reciprocal_rank_fusion(
        self,
        ranked_lists_json: str,
        k: int = RRF_K,
        top_k: int = 10,
        weights_json: str = "null",
    ) -> str:
        """
        Fuse multiple ranked result lists using Reciprocal Rank Fusion (RRF).

        RRF combines multiple ranking lists by summing reciprocal ranks:
        score(doc) = Σ weight_i / (k + rank_i(doc))

        Args:
            ranked_lists_json: JSON object with named ranked lists. Each list contains objects with "id" field.
                Example: {"vector": [{"id": "doc1", "text": "..."}, ...], "lexical": [{"id": "doc2", ...}]}
            k: RRF constant (default 60). Higher values reduce impact of high ranks.
            top_k: Number of results to return after fusion.
            weights_json: Optional JSON object with weights per source. Default is equal weight (1.0).
                Example: {"vector": 1.5, "lexical": 1.0, "graph": 0.8}

        Returns:
            JSON string with fused results including source contributions.
        """
        try:
            logger.info(f"Reciprocal Rank Fusion (k={k}, top_k={top_k})")

            # Parse ranked lists
            try:
                ranked_lists = json.loads(ranked_lists_json)
            except json.JSONDecodeError as e:
                return ErrorResponse(error=f"Invalid ranked_lists_json: {e}").model_dump_json()

            if not isinstance(ranked_lists, dict):
                return ErrorResponse(
                    error="ranked_lists_json must be a JSON object with named lists"
                ).model_dump_json()

            if not ranked_lists:
                return RRFResponse(
                    results=[], count=0, sources=[], weights={}, k=k
                ).model_dump_json()

            weights: Dict[str, float] = {}
            if weights_json and weights_json != "null":
                try:
                    parsed_weights = json.loads(weights_json)
                except json.JSONDecodeError as e:
                    return ErrorResponse(error=f"Invalid weights_json: {e}").model_dump_json()
                if not isinstance(parsed_weights, dict):
                    return ErrorResponse(error="weights_json must be a JSON object").model_dump_json()
                for key, value in parsed_weights.items():
                    try:
                        weights[key] = float(value)
                    except (TypeError, ValueError):
                        return ErrorResponse(
                            error=f"Invalid weight for source '{key}': {value!r}"
                        ).model_dump_json()

            for source in ranked_lists.keys():
                weights.setdefault(source, 1.0)

            fused_candidates = self._score_aware_rrf(
                ranked_lists,
                weights=weights,
                top_k=max(top_k * 3, top_k),
                k=k,
            )
            if not fused_candidates:
                return RRFResponse(
                    results=[],
                    count=0,
                    sources=list(ranked_lists.keys()),
                    weights=weights,
                    k=k,
                ).model_dump_json()

            fused_results = []
            for doc in fused_candidates:
                if len(fused_results) >= top_k:
                    break
                doc_text = doc.get("text", "")
                if any(
                    _text_overlap_ratio(doc_text, kept.get("text", "")) > 0.8
                    for kept in fused_results
                ):
                    continue
                fused_results.append(doc)

            return RRFResponse(
                results=fused_results,
                count=len(fused_results),
                sources=list(ranked_lists.keys()),
                weights=weights,
                k=k,
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Reciprocal Rank Fusion failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def bm25_rerank(
        self,
        query: str,
        documents_json: str,
        k1: float = 1.5,
        b: float = 0.75,
        top_k: int = 10,
    ) -> str:
        """
        Re-rank documents using BM25 scoring algorithm.

        BM25 is a bag-of-words ranking function that scores documents based on
        term frequency, inverse document frequency, and document length normalization.

        Args:
            query: Search query string
            documents_json: JSON array of documents with "id" and "text" fields.
                Example: [{"id": "doc1", "text": "document content..."}, ...]
            k1: Term frequency saturation parameter (default 1.5). Higher values
                increase the impact of term frequency. Typical range: 1.2-2.0
            b: Document length normalization (default 0.75). 0 = no normalization,
                1 = full normalization. Typical range: 0.5-0.8
            top_k: Number of top results to return after re-ranking.

        Returns:
            JSON string with re-ranked documents including BM25 scores.
        """
        import math
        from collections import Counter

        try:
            logger.info(
                f"BM25 rerank: query='{query[:50]}...' k1={k1}, b={b}, top_k={top_k}"
            )

            # Parse documents
            try:
                documents = json.loads(documents_json)
            except json.JSONDecodeError as e:
                return ErrorResponse(error=f"Invalid documents_json: {e}").model_dump_json()

            if not isinstance(documents, list):
                return ErrorResponse(error="documents_json must be a JSON array").model_dump_json()

            if not documents:
                return BM25RerankResponse(
                    results=[], count=0, params={"k1": k1, "b": b, "avgdl": 0}, query_terms=[]
                ).model_dump_json()

            # Tokenize (simple whitespace + lowercase)
            def tokenize(text: str) -> List[str]:
                return text.lower().split()

            # Tokenize query
            query_terms = tokenize(query)
            if not query_terms:
                return BM25RerankResponse(
                    results=documents[:top_k], count=min(len(documents), top_k),
                    params={"k1": k1, "b": b, "avgdl": 0}, query_terms=[],
                ).model_dump_json()

            # Tokenize all documents and compute stats
            doc_tokens: List[List[str]] = []
            doc_lengths: List[int] = []
            for doc in documents:
                text = doc.get("text", "")
                tokens = tokenize(text)
                doc_tokens.append(tokens)
                doc_lengths.append(len(tokens))

            N = len(documents)  # Total number of documents
            avgdl = sum(doc_lengths) / N if N > 0 else 1  # Average document length

            # Compute document frequency for each query term
            df: Dict[str, int] = {}  # term -> number of docs containing it
            for term in set(query_terms):
                df[term] = sum(1 for tokens in doc_tokens if term in tokens)

            # Compute IDF for each query term
            # Using BM25 IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
            idf: Dict[str, float] = {}
            for term in set(query_terms):
                n = df.get(term, 0)
                idf[term] = math.log((N - n + 0.5) / (n + 0.5) + 1)

            # Score each document
            scores: List[tuple] = []
            for i, doc in enumerate(documents):
                tokens = doc_tokens[i]
                doc_len = doc_lengths[i]

                # Term frequencies in this document
                tf = Counter(tokens)

                # BM25 score
                score = 0.0
                term_scores: Dict[str, float] = {}
                for term in query_terms:
                    if term not in tf:
                        continue

                    freq = tf[term]
                    term_idf = idf.get(term, 0)

                    # BM25 term score
                    numerator = freq * (k1 + 1)
                    denominator = freq + k1 * (1 - b + b * (doc_len / avgdl))
                    term_score = term_idf * (numerator / denominator)

                    score += term_score
                    term_scores[term] = round(term_score, 4)

                scores.append((i, score, term_scores))

            # Sort by score descending and take top_k
            scores.sort(key=lambda x: x[1], reverse=True)
            top_results = scores[:top_k]

            # Build result
            reranked = []
            for idx, score, term_scores in top_results:
                doc = documents[idx].copy()
                doc["bm25_score"] = round(score, 6)
                doc["term_contributions"] = term_scores
                reranked.append(doc)

            return BM25RerankResponse(
                results=reranked,
                count=len(reranked),
                params={"k1": k1, "b": b, "avgdl": round(avgdl, 2)},
                query_terms=query_terms,
            ).model_dump_json()

        except Exception as e:
            logger.error(f"BM25 rerank failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def cross_encoder_rerank(
        self, query: str, documents_json: str, top_k: int = 10
    ) -> str:
        """
        Re-rank documents using LLM-based cross-encoder scoring.

        Cross-encoders jointly encode the query and document together, allowing
        for deeper semantic understanding than bi-encoder (embedding) approaches.
        This uses the LLM to score query-document relevance.

        Args:
            query: Search query string
            documents_json: JSON array of documents with "id" and "text" fields.
                Example: [{"id": "doc1", "text": "document content..."}, ...]
            top_k: Number of top results to return after re-ranking.

        Returns:
            JSON string with re-ranked documents including relevance scores.
        """
        if len(query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(f"Cross-encoder rerank: query='{query[:100]}' top_k={top_k}")

            # Parse documents
            try:
                documents = json.loads(documents_json)
            except json.JSONDecodeError as e:
                return ErrorResponse(error=f"Invalid documents_json: {e}").model_dump_json()

            if not isinstance(documents, list):
                return ErrorResponse(error="documents_json must be a JSON array").model_dump_json()

            if not documents:
                return CrossEncoderRerankResponse(results=[], count=0).model_dump_json()

            # Score each document using LLM (concurrently)
            async def _score_doc(doc):
                doc_text = doc.get("text", "")[:6000]  # Limit text length
                fallback_score = doc.get("bm25_score", doc.get("rrf_score", doc.get("score", 0.0)))
                try:
                    fallback_score = float(fallback_score)
                except (TypeError, ValueError):
                    fallback_score = 0.0

                prompt = f"""Rate the relevance of this document to the query on a scale of 0-100.

Scoring guide:
0-25: Not relevant or only tangentially mentioned
25-50: Related topic but does not answer the query
50-75: Directly relevant, answers part of the query
75-100: Highly relevant, directly and fully answers the query

Query: {query}

Document: {doc_text}

Return ONLY a number between 0 and 100, nothing else."""
                async with self._cross_encoder_semaphore:
                    response_text = await self._llm_text(
                        prompt,
                        temperature=0.0,
                        max_output_tokens=10,
                    )

                try:
                    numeric_match = re.search(r"-?\d+(?:\.\d+)?", response_text or "")
                    score = (
                        float(numeric_match.group(0)) if numeric_match else fallback_score
                    )
                    score = max(0, min(100, score))  # Clamp to 0-100
                except ValueError:
                    score = fallback_score

                return (doc, score)

            scored_docs = await asyncio.gather(
                *[_score_doc(doc) for doc in documents[:CROSS_ENCODER_MAX_DOCS]]
            )

            # Sort by score descending and take top_k
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            top_results = scored_docs[:top_k]

            # Build result
            reranked = []
            for doc, score in top_results:
                doc_copy = doc.copy()
                doc_copy["cross_encoder_score"] = round(score, 2)
                reranked.append(doc_copy)

            return CrossEncoderRerankResponse(
                results=reranked, count=len(reranked)
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Cross-encoder rerank failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def query_expand(
        self, query: str, expansion_type: str = "all", max_terms: int = 10
    ) -> str:
        """
        Expand a search query with synonyms, related terms, and alternate phrasings.

        Query expansion improves recall by adding terms that users might not have
        included but are semantically related to the original query.

        Args:
            query: Original search query
            expansion_type: Type of expansion - "synonyms", "related", "rephrase", or "all" (default)
            max_terms: Maximum number of expansion terms to generate (default 10)

        Returns:
            JSON string with original query, expanded terms, and suggested expanded queries.
        """
        if len(query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(f"Query expansion: '{query[:100]}' type={expansion_type}")

            # Check cache
            cache_key = hashlib.sha256(f"{query.strip().lower()}:{expansion_type}:{max_terms}".encode()).hexdigest()
            cached = self._cache_get(self._expansion_cache, cache_key)
            if cached is not None:
                logger.info("Query expansion cache hit")
                return cached

            prompt = f"""Expand this search query to improve search recall.

Original query: {query}

Generate expansions based on type "{expansion_type}":
- synonyms: Alternative words with same meaning
- related: Related concepts and terms
- rephrase: Alternative phrasings of the query
- all: All of the above

Return a JSON object with this exact structure:
{{
    "synonyms": ["term1", "term2"],
    "related_terms": ["term1", "term2"],
    "rephrased_queries": ["query1", "query2"],
    "expanded_query": "original query with key expansion terms added"
}}

Generate up to {max_terms} terms total across all categories.
Return ONLY valid JSON, no explanation."""

            response_text = await self._llm_text(
                prompt,
                temperature=0.3,
                max_output_tokens=500,
                response_mime_type="application/json",
            )

            if not response_text:
                raise RuntimeError("Query expansion returned empty response")

            # Parse response
            try:
                expansion = json.loads(response_text.strip())
            except json.JSONDecodeError:
                raise RuntimeError("Query expansion did not return valid JSON") from None
            if not isinstance(expansion, dict):
                raise RuntimeError("Query expansion output is not a JSON object")
            result = QueryExpansionResponse(
                original_query=query,
                synonyms=expansion.get("synonyms", []),
                related_terms=expansion.get("related_terms", []),
                rephrased_queries=expansion.get("rephrased_queries", []),
                expanded_query=expansion.get("expanded_query", query),
            ).model_dump_json()

            self._cache_put(self._expansion_cache, cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return ErrorResponse(error=str(e), details={"original_query": query}).model_dump_json()

    async def graph_based_retrieval(self, entities: List[str], limit: int = 10) -> str:
        """
        Retrieve documents based on entity relationships in the graph.

        Args:
            entities: List of entity names to search for
            limit: Maximum number of results

        Returns:
            JSON string with retrieved documents
        """
        try:
            logger.info(f"Graph-based retrieval for entities: {entities[:10]}")

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            if not entities:
                return GraphBasedRetrievalResponse(
                    results=[], count=0, entities=[]
                ).model_dump_json()
            entities = [
                self._normalize_entity_token(e)
                for e in entities
                if isinstance(e, str) and self._normalize_entity_token(e)
            ]

            cypher = """
            UNWIND $entities AS ent
            MATCH (e:__Entity__)
            WHERE toLower(e.name) = toLower(ent)
               OR any(alias IN coalesce(e.aliases, []) WHERE toLower(alias) = toLower(ent))
            OPTIONAL MATCH (e)<-[:MENTIONS]-(c_direct:__Chunk__)
            OPTIONAL MATCH (e)-[:REL]-(:__Entity__)<-[:MENTIONS]-(c_rel:__Chunk__)
            WITH collect(DISTINCT {chunk: c_direct, weight: 2.0}) +
                 collect(DISTINCT {chunk: c_rel, weight: 1.0}) AS chunk_entries
            UNWIND chunk_entries AS entry
            WITH entry.chunk AS c, sum(entry.weight) AS score
            WHERE c IS NOT NULL
            RETURN c.id AS id, c.text AS text, score
            ORDER BY score DESC
            LIMIT $limit
            """
            results = await self.neo4j.query(
                cypher, {"entities": entities, "limit": limit}
            )
            if not results and ENTITY_FUZZY_FALLBACK and entities:
                fuzzy_query = _build_entity_fuzzy_query(entities)
                results = await self.neo4j.query(
                    """
                    CALL db.index.fulltext.queryNodes('entity_name_ft', $query)
                    YIELD node, score
                    WITH node ORDER BY score DESC LIMIT 30
                    MATCH (node)<-[:MENTIONS]-(c:__Chunk__)
                    RETURN c.id AS id, c.text AS text, count(*) AS score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    {"query": fuzzy_query, "limit": limit},
                )

            items = [
                SearchResult(
                    id=r["id"], text=r.get("text", ""), score=r.get("score", 0)
                )
                for r in results
            ]
            return GraphBasedRetrievalResponse(
                results=items, count=len(items), entities=entities
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Graph-based retrieval failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def community_based_retrieval(
        self, entities: List[str], limit: int = 10
    ) -> str:
        """
        Retrieve chunks via community assignments around the provided entities.

        Args:
            entities: List of entity names
            limit: Maximum number of chunks to return

        Returns:
            JSON string with chunk results scored by matched community/entity evidence
        """
        try:
            logger.info(f"Community-based retrieval for entities: {entities[:10]}")

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            if not entities:
                return CommunityRetrievalResponse(
                    results=[], count=0
                ).model_dump_json()
            entities = [
                self._normalize_entity_token(e)
                for e in entities
                if isinstance(e, str) and self._normalize_entity_token(e)
            ]

            cypher = """
            UNWIND $entities AS ent
            MATCH (e:__Entity__)
            WHERE toLower(e.name) = toLower(ent)
               OR any(alias IN coalesce(e.aliases, []) WHERE toLower(alias) = toLower(ent))
            MATCH (e)-[:IN_COMMUNITY*1..2]->(c:__Community__)
            WITH DISTINCT ent, c
            MATCH (m:__Entity__)-[:IN_COMMUNITY*1..2]->(c)
            MATCH (ch:__Chunk__)-[:MENTIONS]->(m)
            WITH ch, c, collect(DISTINCT ent) AS matched_entities
            RETURN ch.id AS id,
                   ch.text AS text,
                   toFloat(size(matched_entities)) AS score,
                   c.id AS community_id,
                   c.title AS community_title,
                   c.summary AS community_summary
            ORDER BY score DESC
            LIMIT $limit
            """
            results = await self.neo4j.query(
                cypher, {"entities": entities, "limit": limit}
            )
            if not results and ENTITY_FUZZY_FALLBACK and entities:
                fuzzy_query = _build_entity_fuzzy_query(entities)
                results = await self.neo4j.query(
                    """
                    CALL db.index.fulltext.queryNodes('entity_name_ft', $query)
                    YIELD node, score
                    WITH node ORDER BY score DESC LIMIT 30
                    MATCH (node)-[:IN_COMMUNITY*1..2]->(c:__Community__)
                    MATCH (m:__Entity__)-[:IN_COMMUNITY*1..2]->(c)
                    MATCH (ch:__Chunk__)-[:MENTIONS]->(m)
                    RETURN ch.id AS id,
                           ch.text AS text,
                           max(score) AS score,
                           c.id AS community_id,
                           c.title AS community_title,
                           c.summary AS community_summary
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    {"query": fuzzy_query, "limit": limit},
                )
            return CommunityRetrievalResponse(
                results=results, count=len(results)
            ).model_dump_json()
        except Exception as e:
            logger.error(f"Community-based retrieval failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def get_chunk_context(self, chunk_id: str, window: int = 1) -> str:
        """
        Retrieve a chunk and its neighboring chunks from the same document for fuller context.

        When a retrieved chunk sits at a topic boundary, the answer may be split
        across adjacent chunks. This tool fetches the target chunk plus its
        neighbors (previous/next by chunk_index within the same document).

        Args:
            chunk_id: The ID of the chunk to expand context for.
            window: Number of neighboring chunks on each side to include (default 1).

        Returns:
            JSON string with the target chunk and surrounding context chunks.
        """
        try:
            logger.info(
                f"Chunk context expansion: chunk_id='{chunk_id}', window={window}"
            )

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            # Get the target chunk and its position within its document
            cypher = """
            MATCH (target:__Chunk__ {id: $chunk_id})
            OPTIONAL MATCH (target)-[:PART_OF]->(doc:__Document__)
            OPTIONAL MATCH (f:__File__)-[:HAS_CHUNK]->(target)
            WITH target,
                 doc,
                 f,
                 coalesce(
                    target.chunk_index,
                    toInteger(last(split(target.id, '_chunk_'))),
                    0
                 ) AS target_idx
            WITH target, target_idx,
                 CASE
                   WHEN doc IS NOT NULL THEN [
                        (doc)<-[:PART_OF]-(s:__Chunk__) |
                        {
                          id: s.id,
                          text: s.text,
                          chunk_index: coalesce(
                            s.chunk_index,
                            toInteger(last(split(s.id, '_chunk_'))),
                            0
                          )
                        }
                   ]
                   WHEN f IS NOT NULL THEN [
                        (f)-[:HAS_CHUNK]->(s:__Chunk__) |
                        {
                          id: s.id,
                          text: s.text,
                          chunk_index: coalesce(
                            s.chunk_index,
                            toInteger(last(split(s.id, '_chunk_'))),
                            0
                          )
                        }
                   ]
                   ELSE []
                 END AS sibling_chunks
            WITH target, target_idx,
                 [c IN sibling_chunks
                    WHERE c.chunk_index >= target_idx - $window
                      AND c.chunk_index <= target_idx + $window
                 ] AS in_window
            WITH CASE WHEN size(in_window) > 0
                      THEN in_window
                      ELSE [{id: target.id, text: target.text, chunk_index: target_idx}]
                 END AS chunks
            UNWIND chunks AS c
            RETURN c.id AS id, c.text AS text, c.chunk_index AS chunk_index
            ORDER BY c.chunk_index
            """
            results = await self.neo4j.query(
                cypher, {"chunk_id": chunk_id, "window": window}
            )

            if not results:
                return ErrorResponse(error=f"Chunk '{chunk_id}' not found").model_dump_json()

            return ChunkContextResponse(
                chunk_id=chunk_id, chunks=results, count=len(results)
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Chunk context expansion failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def payload_search(
        self, search_query: str, top_k: int = 5, min_score: float = 0.0
    ) -> str:
        """
        Search image/table payloads using vector and lexical signals over alt text.
        """
        if len(search_query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(search_query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            logger.info(
                f"Payload search: '{search_query[:100]}' (top_k={top_k}, min_score={min_score})"
            )
            await self._ensure_embedding_compatibility()

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            emb = await self.embeddings.embed_query(search_query)
            vector_hits, lexical_hits = await asyncio.gather(
                self.neo4j.query(
                    """
                    CALL db.index.vector.queryNodes('payload_embedding_index', $k, $embedding)
                    YIELD node, score
                    RETURN node.assetId AS id, node.alt_text AS alt_text, node.type AS type, score
                    ORDER BY score DESC
                    """,
                    {"k": max(top_k, 1), "embedding": emb},
                ),
                self.neo4j.query(
                    """
                    CALL db.index.fulltext.queryNodes('payload_text_ft', $query)
                    YIELD node, score
                    RETURN node.assetId AS id, node.alt_text AS alt_text, node.type AS type, score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    {"query": _build_lucene_query(search_query), "limit": max(top_k, 1)},
                ),
            )

            fused_candidates = self._score_aware_rrf(
                {"vector": vector_hits, "lexical": lexical_hits},
                weights={"vector": 1.2, "lexical": 1.0},
                top_k=max(top_k * 3, top_k),
                k=RRF_K,
            )
            meta: Dict[str, Dict[str, Any]] = {
                row.get("id"): row
                for row in vector_hits + lexical_hits
                if isinstance(row, dict) and row.get("id")
            }
            ranked_ids = [r.get("id") for r in fused_candidates if r.get("id")][:top_k]
            if not ranked_ids:
                return PayloadSearchResponse(results=[], count=0).model_dump_json()

            chunk_links = await self.neo4j.query(
                """
                UNWIND $ids AS pid
                MATCH (p:__Payload__ {assetId: pid})<-[:HAS_PAYLOAD]-(c:__Chunk__)
                RETURN p.assetId AS id, c.id AS chunk_id
                """,
                {"ids": ranked_ids},
            )
            chunks_by_payload: Dict[str, List[str]] = {}
            for row in chunk_links:
                chunks_by_payload.setdefault(row["id"], []).append(row["chunk_id"])

            results = []
            for pid in ranked_ids:
                score = next(
                    (
                        float(c.get("rrf_score", 0.0))
                        for c in fused_candidates
                        if c.get("id") == pid
                    ),
                    0.0,
                )
                if min_score > 0 and score < min_score:
                    continue
                item = meta.get(pid, {}).copy()
                item["rrf_score"] = round(score, 6)
                item["chunk_ids"] = chunks_by_payload.get(pid, [])
                results.append(item)

            return PayloadSearchResponse(
                results=results, count=len(results)
            ).model_dump_json()
        except Exception as e:
            logger.error(f"Payload search failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        weights_json: str = "null",
        debug: bool = False,
    ) -> str:
        """
        Run vector, lexical, and graph-based searches in parallel, fuse with RRF, and rerank with BM25.

        This is a single-tool fast path that guarantees a high-quality multi-source
        retrieval pipeline without requiring multiple sequential tool calls.

        Args:
            query: Natural language search query.
            top_k: Number of final results to return.
            min_score: Minimum RRF score threshold. Results below this are excluded.
            weights_json: Optional JSON object with per-source weights.
                Default: {"vector": 1.2, "lexical": 1.0, "graph": 0.8}

        Returns:
            JSON string with fused, deduplicated, and reranked search results.
        """
        if len(query) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(query)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            query = _normalize_query_text(query)
            logger.info(f"Hybrid search: '{query[:100]}' (top_k={top_k})")
            await self._ensure_embedding_compatibility()

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            # Parse custom weights or use defaults
            weights = {"vector": 1.2, "lexical": 1.0, "graph": 1.0}
            if weights_json and weights_json != "null":
                try:
                    parsed = json.loads(weights_json)
                except json.JSONDecodeError as e:
                    return ErrorResponse(error=f"Invalid weights_json: {e}").model_dump_json()
                if not isinstance(parsed, dict):
                    return ErrorResponse(error="weights_json must be a JSON object").model_dump_json()
                for key, value in parsed.items():
                    try:
                        weights[key] = float(value)
                    except (TypeError, ValueError):
                        return ErrorResponse(
                            error=f"Invalid weight for source '{key}': {value!r}"
                        ).model_dump_json()

            # Detect entities for graph retrieval
            entities_resp = self._safe_json_loads(await self.detect_entities(query))
            if entities_resp.get("error"):
                return ErrorResponse(
                    error=f"Entity detection failed: {entities_resp.get('error')}"
                ).model_dump_json()
            entities = (
                entities_resp.get("entities", [])
                if isinstance(entities_resp.get("entities"), list)
                else []
            )
            entities = [
                self._normalize_entity_token(e)
                for e in entities
                if isinstance(e, str) and self._normalize_entity_token(e)
            ]
            if len(entities) >= 3:
                weights["graph"] = weights.get("graph", 1.0) + 0.15

            # Run searches in parallel
            fetch_k = max(top_k * 3, 15)
            coros = [
                self.vector_search(query, top_k=fetch_k),
                self.lexical_search(query, top_k=fetch_k),
            ]
            if entities:
                coros.append(self.graph_based_retrieval(entities, limit=fetch_k))

            raw_results = await asyncio.gather(*coros)

            vector_resp = self._safe_json_loads(raw_results[0])
            lexical_resp = self._safe_json_loads(raw_results[1])
            graph_resp = (
                self._safe_json_loads(raw_results[2])
                if len(raw_results) > 2
                else {}
            )
            for source, payload in (
                ("vector", vector_resp),
                ("lexical", lexical_resp),
                ("graph", graph_resp),
            ):
                if payload.get("error"):
                    return ErrorResponse(
                        error=f"{source} retrieval failed: {payload.get('error')}"
                    ).model_dump_json()

            vector_results = vector_resp.get("results", [])
            lexical_results = lexical_resp.get("results", [])
            graph_results = (
                graph_resp.get("results", [])
                if len(raw_results) > 2
                else []
            )
            if lexical_results:
                try:
                    lex_top = max(float(r.get("score", 0.0) or 0.0) for r in lexical_results)
                except (TypeError, ValueError):
                    lex_top = 0.0
                if lex_top >= 8.0:
                    weights["lexical"] = weights.get("lexical", 1.0) + 0.2

            ranked_lists: Dict[str, list] = {
                "vector": vector_results,
                "lexical": lexical_results,
            }
            if graph_results:
                ranked_lists["graph"] = graph_results
            source_map: Dict[str, set[str]] = collections.defaultdict(set)
            for source_name, docs in ranked_lists.items():
                for doc in docs if isinstance(docs, list) else []:
                    if isinstance(doc, dict) and doc.get("id"):
                        source_map[doc["id"]].add(source_name)

            fused_candidates = self._score_aware_rrf(
                ranked_lists,
                weights=weights,
                top_k=max(top_k * 3, 20),
                k=RRF_K,
            )
            if not fused_candidates:
                return HybridSearchResponse(results=[], count=0).model_dump_json()

            fused = []
            for doc in fused_candidates:
                if len(fused) >= top_k * 2:
                    break
                doc_text = doc.get("text", "")
                if any(
                    _text_overlap_ratio(doc_text, kept.get("text", "")) > 0.8
                    for kept in fused
                ):
                    continue
                fused.append(doc.copy())

            # BM25 rerank the fused results for final quality pass
            if fused:
                bm25_resp = self._safe_json_loads(
                    await self.bm25_rerank(query, json.dumps(fused), top_k=top_k)
                )
                final = bm25_resp.get("results", fused[:top_k])
            else:
                final = []

            if min_score > 0:
                final = [
                    r
                    for r in final
                    if r.get("rrf_score", 0) >= min_score
                ]

            items = [
                SearchResult(
                    id=r["id"],
                    text=r.get("text", ""),
                    score=r.get("bm25_score", r.get("rrf_score", 0)),
                )
                for r in final
                if isinstance(r, dict) and "id" in r
            ]
            confidence = self._compute_confidence(
                final if final else fused,
                source_map,
                score_key_candidates=["bm25_score", "rrf_score", "score"],
            )
            ranked_rrf = [
                float(r.get("rrf_score", 0.0) or 0.0)
                for r in fused
                if isinstance(r, dict)
            ]
            gap = (
                ranked_rrf[0] - ranked_rrf[min(4, len(ranked_rrf) - 1)]
                if len(ranked_rrf) >= 2
                else 0.0
            )
            retrieval_debug = None
            if debug or DEBUG_RETRIEVAL_METRICS:
                retrieval_debug = {
                    "weights": weights,
                    "source_hits": {
                        "vector": len(vector_results),
                        "lexical": len(lexical_results),
                        "graph": len(graph_results),
                    },
                    "confidence": round(confidence, 6),
                    "score_gap_top1_top5": round(gap, 6),
                    "cross_encoder_used": False,
                    "context_tokens": 0,
                    "citation_audit": None,
                }
            return HybridSearchResponse(
                results=items,
                count=len(items),
                method="hybrid_rrf_bm25",
                retrieval_debug=retrieval_debug,
            ).model_dump_json()

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

    async def graphrag_answer(
        self,
        question: str,
        top_k: int = 8,
        use_hyde: bool = True,
        weights_json: str = "null",
        debug: bool = False,
    ) -> str:
        """
        End-to-end GraphRAG pipeline:
        entity detection -> multi-retrieval -> RRF fusion -> BM25 rerank -> context assembly -> answer synthesis.

        Args:
            question: Natural language question to answer.
            top_k: Number of chunks to use for context.
            use_hyde: Use HyDE search instead of direct vector search.
            weights_json: Optional JSON weights for RRF fusion per source.
                Default: {"semantic": 1.3, "lexical": 1.0, "graph": 1.15, "community": 1.05}
        """
        if len(question) > MAX_QUERY_LEN:
            return ErrorResponse(error=f"Query too long ({len(question)} chars, max {MAX_QUERY_LEN})").model_dump_json()
        try:
            question = _normalize_query_text(question)
            logger.info(
                f"GraphRAG answer: '{question[:100]}' (top_k={top_k}, use_hyde={use_hyde})"
            )
            await self._ensure_embedding_compatibility()

            if not self.neo4j.driver:
                return ErrorResponse(error="Neo4j not configured").model_dump_json()

            entities_resp = self._safe_json_loads(await self.detect_entities(question))
            if entities_resp.get("error"):
                return ErrorResponse(
                    error=f"Entity detection failed: {entities_resp.get('error')}"
                ).model_dump_json()
            entities = (
                entities_resp.get("entities", [])
                if isinstance(entities_resp.get("entities"), list)
                else []
            )
            entities = [
                self._normalize_entity_token(e)
                for e in entities
                if isinstance(e, str) and self._normalize_entity_token(e)
            ]

            # Build coroutines for parallel execution
            fetch_k = max(top_k * 2, 10)
            semantic_coro = (
                self.hyde_search(question, top_k=fetch_k)
                if use_hyde
                else self.vector_search(question, top_k=fetch_k)
            )
            lexical_coro = self.lexical_search(question, top_k=fetch_k)
            payload_coro = self.payload_search(question, top_k=min(6, max(top_k, 3)))

            coros = [semantic_coro, lexical_coro]
            coro_keys = ["semantic", "lexical"]
            if entities:
                coros.append(self.graph_based_retrieval(entities, limit=fetch_k))
                coro_keys.append("graph")
                coros.append(self.community_based_retrieval(entities, limit=max(top_k, 10)))
                coro_keys.append("community")
            coros.append(payload_coro)
            coro_keys.append("payload")

            raw_responses = await asyncio.gather(*coros)
            responses: Dict[str, Dict[str, Any]] = {
                k: self._safe_json_loads(v) for k, v in zip(coro_keys, raw_responses)
            }
            for source, payload in responses.items():
                if payload.get("error"):
                    return ErrorResponse(
                        error=f"{source} retrieval failed: {payload.get('error')}"
                    ).model_dump_json()

            semantic_resp = responses["semantic"]
            lexical_resp = responses["lexical"]
            graph_resp = responses.get("graph", {"results": []})
            community_resp = responses.get("community", {"results": []})
            payload_resp = responses.get("payload", {"results": []})

            semantic_results = semantic_resp.get("results", [])
            lexical_results = lexical_resp.get("results", [])
            graph_results = graph_resp.get("results", [])
            community_results = community_resp.get("results", [])

            ranked_lists = {
                "semantic": semantic_results,
                "lexical": lexical_results,
                "graph": graph_results,
                "community": community_results,
            }
            source_map: Dict[str, set[str]] = collections.defaultdict(set)
            for source_name, docs in ranked_lists.items():
                for doc in docs if isinstance(docs, list) else []:
                    if isinstance(doc, dict) and doc.get("id"):
                        source_map[doc["id"]].add(source_name)

            # Configurable weights with sensible defaults
            weights = {
                "semantic": 1.3,
                "lexical": 1.0,
                "graph": 1.15,
                "community": 0.95,
            }
            if len(entities) >= 3:
                weights["graph"] += 0.15
                weights["community"] += 0.1
            if lexical_results:
                try:
                    lex_top = max(float(r.get("score", 0.0) or 0.0) for r in lexical_results)
                except (TypeError, ValueError):
                    lex_top = 0.0
                if lex_top >= 8.0:
                    weights["lexical"] += 0.2
            if weights_json and weights_json != "null":
                try:
                    parsed = json.loads(weights_json)
                except json.JSONDecodeError as e:
                    return ErrorResponse(error=f"Invalid weights_json: {e}").model_dump_json()
                if not isinstance(parsed, dict):
                    return ErrorResponse(error="weights_json must be a JSON object").model_dump_json()
                for key, value in parsed.items():
                    try:
                        weights[key] = float(value)
                    except (TypeError, ValueError):
                        return ErrorResponse(
                            error=f"Invalid weight for source '{key}': {value!r}"
                        ).model_dump_json()

            fused_results = self._score_aware_rrf(
                ranked_lists,
                weights=weights,
                top_k=max(top_k * 3, 20),
                k=RRF_K,
            )

            # Inject payload-derived chunk signal so multimodal evidence influences ranking.
            payload_chunk_scores: Dict[str, float] = {}
            for item in payload_resp.get("results", []):
                if not isinstance(item, dict):
                    continue
                payload_score = item.get("rrf_score", item.get("score", 0.0)) or 0.0
                try:
                    payload_score = float(payload_score)
                except (TypeError, ValueError):
                    payload_score = 0.0
                for cid in item.get("chunk_ids", []) or []:
                    if isinstance(cid, str) and cid:
                        payload_chunk_scores[cid] = max(
                            payload_chunk_scores.get(cid, 0.0), payload_score
                        )
                        source_map[cid].add("payload")

            if payload_chunk_scores:
                existing_ids = set()
                for doc in fused_results:
                    if not isinstance(doc, dict):
                        continue
                    cid = doc.get("id")
                    if not cid:
                        continue
                    existing_ids.add(cid)
                    if cid in payload_chunk_scores:
                        base = doc.get("rrf_score", 0.0) or 0.0
                        try:
                            base = float(base)
                        except (TypeError, ValueError):
                            base = 0.0
                        doc["rrf_score"] = round(
                            base + 0.15 * payload_chunk_scores[cid], 6
                        )

                missing_payload_ids = [
                    cid for cid in payload_chunk_scores.keys() if cid not in existing_ids
                ]
                if missing_payload_ids:
                    payload_chunk_rows = await self.neo4j.query(
                        """
                        UNWIND $ids AS cid
                        MATCH (c:__Chunk__ {id: cid})
                        RETURN c.id AS id, c.text AS text
                        """,
                        {"ids": missing_payload_ids[: max(top_k * 2, 10)]},
                    )
                    for row in payload_chunk_rows:
                        cid = row.get("id")
                        if not cid:
                            continue
                        fused_results.append(
                            {
                                "id": cid,
                                "text": row.get("text", ""),
                                "rrf_score": round(
                                    0.15 * payload_chunk_scores.get(cid, 0.0), 6
                                ),
                                "from_payload": True,
                            }
                        )

                fused_results.sort(
                    key=lambda d: (d.get("rrf_score", 0) if isinstance(d, dict) else 0),
                    reverse=True,
                )

            # Post-fusion BM25 reranking for final quality pass
            if fused_results:
                reranked_resp = self._safe_json_loads(
                    await self.bm25_rerank(
                        question, json.dumps(fused_results), top_k=max(top_k * 2, 10)
                    )
                )
                fused_results = reranked_resp.get("results", fused_results)
            ranked_scores = [
                float(r.get("bm25_score", r.get("rrf_score", 0.0)) or 0.0)
                for r in fused_results
                if isinstance(r, dict)
            ]
            score_gap = (
                ranked_scores[0] - ranked_scores[min(4, len(ranked_scores) - 1)]
                if len(ranked_scores) >= 2
                else 0.0
            )
            confidence = self._compute_confidence(
                fused_results,
                source_map,
                score_key_candidates=["bm25_score", "rrf_score", "score"],
            )
            cross_encoder_used = False
            if fused_results and (
                score_gap < LOW_CONFIDENCE_SCORE_GAP
                or confidence < LOW_CONFIDENCE_THRESHOLD
            ):
                cross_encoder_used = True
                cross_resp = self._safe_json_loads(
                    await self.cross_encoder_rerank(
                        question,
                        json.dumps(fused_results[:CROSS_ENCODER_MAX_DOCS]),
                        top_k=min(CROSS_ENCODER_MAX_DOCS, max(top_k * 2, 10)),
                    )
                )
                fused_results = cross_resp.get("results", fused_results)

            # Deduplicate chunk IDs while preserving rank order
            seen_ids: set = set()
            chunk_ids: List[str] = []
            for r in fused_results:
                cid = r.get("id") if isinstance(r, dict) else None
                if cid and cid not in seen_ids:
                    chunk_ids.append(cid)
                    seen_ids.add(cid)
            if not chunk_ids:
                return GraphRagAnswerResponse(
                    answer="I could not find relevant chunks in the current GraphRAG indexes.",
                    citations=[],
                    retrieved_chunks=[],
                    retrieval={
                        "entities": entities,
                        "semantic_hits": len(semantic_resp.get("results", [])),
                        "lexical_hits": len(lexical_resp.get("results", [])),
                        "graph_hits": len(graph_resp.get("results", [])),
                        "community_hits": len(community_resp.get("results", [])),
                    },
                ).model_dump_json()

            context_fetch_k = max(top_k * CONTEXT_CANDIDATE_MULTIPLIER, top_k)
            context_rows = await self.neo4j.query(
                """
                UNWIND range(0, size($ids)-1) AS idx
                WITH idx, $ids[idx] AS cid
                MATCH (c:__Chunk__ {id: cid})
                OPTIONAL MATCH (c)-[:MENTIONS]->(e:__Entity__)
                OPTIONAL MATCH (e)-[:IN_COMMUNITY*1..2]->(comm:__Community__)
                OPTIONAL MATCH (c)-[:HAS_PAYLOAD]->(p:__Payload__)
                WITH idx, c,
                     collect(DISTINCT e.name)[0..8] AS entities,
                     [s IN collect(DISTINCT comm.summary) WHERE s IS NOT NULL AND s <> ""][0..3] AS community_summaries,
                     [x IN collect(DISTINCT {type: p.type, alt_text: p.alt_text}) WHERE x.alt_text IS NOT NULL AND x.alt_text <> ""][0..3] AS payloads
                RETURN idx, c.id AS id, c.text AS text, entities, community_summaries, payloads
                ORDER BY idx
                LIMIT $limit
                """,
                {"ids": chunk_ids, "limit": max(context_fetch_k, 1)},
            )

            selected_rows = self._select_diverse_rows(
                context_rows, source_map, top_k=max(context_fetch_k, top_k)
            )

            # Expand top short/fragmented chunks with neighboring context.
            expanded_texts: Dict[str, str] = {}
            expand_ids = [
                r.get("id")
                for r in selected_rows[: max(top_k, 5)]
                if r.get("id") and len((r.get("text") or "").strip()) < 280
            ]
            if expand_ids:
                ctx_coros = [
                    self.get_chunk_context(
                        cid,
                        window=2
                        if len(
                            next(
                                (
                                    (row.get("text") or "")
                                    for row in selected_rows
                                    if row.get("id") == cid
                                ),
                                "",
                            ).strip()
                        )
                        < 160
                        else 1,
                    )
                    for cid in expand_ids
                ]
                ctx_results = await asyncio.gather(*ctx_coros)
                for cid, ctx_raw in zip(expand_ids, ctx_results):
                    ctx_resp = self._safe_json_loads(ctx_raw)
                    chunks = ctx_resp.get("chunks", [])
                    if len(chunks) > 1:
                        expanded_texts[cid] = " ".join(
                            c.get("text", "") for c in chunks if isinstance(c, dict)
                        )

            blocks = []
            citation_ids = []
            running_tokens = 0
            for row in selected_rows:
                cid = row.get("id")
                if not cid:
                    continue
                text = expanded_texts.get(cid, row.get("text") or "")
                lines = [f"[{cid}]", text]
                ents = row.get("entities") or []
                if ents:
                    lines.append(f"Entities: {', '.join(ents)}")
                comms = row.get("community_summaries") or []
                if comms:
                    lines.append("Community context: " + " | ".join(comms))
                payloads = row.get("payloads") or []
                payload_lines = [
                    f"{p.get('type', 'payload')}: {p.get('alt_text', '')}"
                    for p in payloads
                    if isinstance(p, dict)
                ]
                if payload_lines:
                    lines.append("Payloads: " + " | ".join(payload_lines))
                block = "\n".join(lines).strip()
                block_tokens = self._token_count(block, self.llm.model)
                if blocks and running_tokens + block_tokens > MAX_CONTEXT_TOKENS:
                    continue
                blocks.append(block)
                citation_ids.append(cid)
                running_tokens += block_tokens
                if len(blocks) >= top_k and running_tokens >= int(MAX_CONTEXT_TOKENS * 0.85):
                    break

            if not blocks:
                return ErrorResponse(
                    error="Failed to build context from retrieved chunks"
                ).model_dump_json()

            answer_prompt = (
                "You are a GraphRAG assistant. Answer the question using ONLY the context below.\n\n"
                "Rules:\n"
                "1. Cite evidence inline using chunk IDs like [chunk_id]\n"
                "2. If sources contradict each other, note the conflict and state which appears more reliable\n"
                "3. If the context only partially answers the question, explicitly state what is covered and what is missing\n"
                "4. Prioritize information from earlier (higher-ranked) context blocks\n"
                "5. Do not speculate beyond what the context supports\n"
                "6. Keep answers concise and well-structured\n"
                f"7. Include at least {MIN_CITATIONS} valid citations when enough evidence exists\n\n"
                f"Question: {question}\n\n"
                "Context:\n" + "\n\n---\n\n".join(blocks)
            )
            answer_text = await self._llm_text(
                answer_prompt,
                temperature=0.1,
                max_output_tokens=900,
            )
            citation_audit = self._citation_audit(answer_text, set(citation_ids))
            if CITATION_REPAIR_ENABLED:
                if not citation_audit["meets_minimum"]:
                    repair_prompt = (
                        "Rewrite the answer using only the same context and facts, "
                        "and include inline citations in [chunk_id] format using only the IDs below.\n"
                        f"Include at least {MIN_CITATIONS} valid citations when possible.\n"
                        f"Allowed IDs: {citation_ids}\n\n"
                        f"Question: {question}\n\n"
                        f"Current answer:\n{answer_text}"
                    )
                    repaired = await self._llm_text(
                        repair_prompt,
                        temperature=0.0,
                        max_output_tokens=900,
                    )
                    repaired_audit = self._citation_audit(repaired, set(citation_ids))
                    if repaired_audit["valid_count"] >= citation_audit["valid_count"]:
                        answer_text = repaired
                        citation_audit = repaired_audit

            cited = sorted(
                {
                    ref
                    for ref in re.findall(r"\[([^\]]+)\]", answer_text or "")
                    if ref in citation_ids
                }
            )
            return GraphRagAnswerResponse(
                answer=answer_text,
                citations=cited,
                retrieved_chunks=citation_ids,
                retrieval={
                    "entities": entities,
                    "semantic_hits": len(semantic_resp.get("results", [])),
                    "lexical_hits": len(lexical_resp.get("results", [])),
                    "graph_hits": len(graph_resp.get("results", [])),
                    "community_hits": len(community_resp.get("results", [])),
                    "payload_hits": len(payload_resp.get("results", [])),
                },
                retrieval_debug=(
                    {
                        "weights": weights,
                        "confidence": round(confidence, 6),
                        "score_gap_top1_top5": round(score_gap, 6),
                        "cross_encoder_used": cross_encoder_used,
                        "context_tokens": running_tokens,
                        "citation_audit": citation_audit,
                        "source_hits": {
                            "semantic": len(semantic_resp.get("results", [])),
                            "lexical": len(lexical_resp.get("results", [])),
                            "graph": len(graph_resp.get("results", [])),
                            "community": len(community_resp.get("results", [])),
                            "payload": len(payload_resp.get("results", [])),
                        },
                    }
                    if (debug or DEBUG_RETRIEVAL_METRICS)
                    else None
                ),
            ).model_dump_json()
        except Exception as e:
            logger.error(f"GraphRAG answer failed: {e}")
            return ErrorResponse(error=str(e)).model_dump_json()

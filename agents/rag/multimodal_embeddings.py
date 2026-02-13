"""
Multimodal embedding helpers backed by LiteLLM.
"""

from __future__ import annotations

import math
import os
from typing import Any

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes"}


def _l2_normalize(values: list[float]) -> list[float]:
    if not values:
        raise RuntimeError("Embedding output is empty")
    norm = math.sqrt(sum(float(v) * float(v) for v in values))
    if not math.isfinite(norm) or norm <= 0:
        raise RuntimeError("Invalid embedding norm")
    return [float(v) / norm for v in values]


def _validate_embedding(values: list[float]) -> None:
    if not values:
        raise RuntimeError("Embedding output is empty")
    if not all(math.isfinite(float(v)) for v in values):
        raise RuntimeError("Embedding output contains non-finite values")
    norm = math.sqrt(sum(float(v) * float(v) for v in values))
    if not math.isfinite(norm) or norm <= 0:
        raise RuntimeError("Embedding output has invalid norm")


def _embedding_model() -> str:
    model = os.getenv("MULTIMODAL_EMBEDDING_MODEL", "").strip()
    if not model:
        raise RuntimeError("MULTIMODAL_EMBEDDING_MODEL env-var missing")
    return model


def _litellm_timeout() -> float:
    return float(os.getenv("MULTIMODAL_EMBEDDING_TIMEOUT", "120"))


def _litellm_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {"timeout": _litellm_timeout()}
    api_key = os.getenv("LITELLM_API_KEY")
    api_base = os.getenv("LITELLM_API_BASE")
    api_version = os.getenv("LITELLM_API_VERSION")
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    if api_version:
        kwargs["api_version"] = api_version
    return kwargs


def _extract_embedding(response: Any) -> list[float]:
    data: list[Any]
    if isinstance(response, dict):
        data = response.get("data") or []
    else:
        data = getattr(response, "data", []) or []
    if not data:
        raise RuntimeError("Embedding response had no data")
    first = data[0]
    if isinstance(first, dict):
        emb = first.get("embedding") or []
    else:
        emb = getattr(first, "embedding", []) or []
    if not emb:
        raise RuntimeError("Embedding response had no vector")
    values = [float(v) for v in emb]
    _validate_embedding(values)
    return values


def _input_type(mode: str) -> str | None:
    if mode == "text":
        return os.getenv("MULTIMODAL_TEXT_INPUT_TYPE", "query").strip() or None
    if mode == "image":
        return os.getenv("MULTIMODAL_IMAGE_INPUT_TYPE", "document").strip() or None
    if mode == "video":
        return os.getenv("MULTIMODAL_VIDEO_INPUT_TYPE", "document").strip() or None
    raise RuntimeError(f"Unsupported multimodal input type mode: {mode}")


def _embed_with_litellm(payload: Any, *, mode: str) -> list[float]:
    try:
        import litellm
    except Exception as exc:
        raise RuntimeError("litellm is required for multimodal embeddings") from exc

    kwargs: dict[str, Any] = {
        "model": _embedding_model(),
        "input": [payload],
        **_litellm_kwargs(),
    }
    input_type = _input_type(mode)
    if input_type:
        kwargs["input_type"] = input_type

    response = litellm.embedding(**kwargs)
    emb = _extract_embedding(response)
    if _env_bool("MULTIMODAL_L2_NORMALIZE", True):
        emb = _l2_normalize(emb)
    _validate_embedding(emb)
    return emb


def _image_payload(raw_b64: str) -> dict[str, Any]:
    hint = os.getenv("MULTIMODAL_IMAGE_TEXT_HINT", "").strip()
    if hint:
        return {
            "content": [
                {"type": "text", "text": hint},
                {"type": "image_base64", "image_base64": raw_b64},
            ]
        }
    return {"content": [{"type": "image_base64", "image_base64": raw_b64}]}


def _video_payload(raw_b64: str) -> dict[str, Any]:
    return {"content": [{"type": "video_base64", "video_base64": raw_b64}]}


def _video_support_enabled() -> bool:
    raw = os.getenv("VIDEO_EXTENSIONS", ".mp4,.webm,.mpeg,.mpg")
    exts = [e.strip().lower() for e in raw.split(",") if e.strip()]
    return bool(exts)


def require_video_capable_model(force: bool = False) -> None:
    if not force and not _video_support_enabled():
        return
    model = _embedding_model().strip().lower()
    if model == "voyage/voyage-multimodal-3.5":
        return
    if model.endswith("voyage-multimodal-3.5"):
        return
    raise RuntimeError(
        "Video embeddings require MULTIMODAL_EMBEDDING_MODEL=voyage/voyage-multimodal-3.5"
    )


def multimodal_embed_text(text: str) -> list[float]:
    normalized = (text or "").strip()
    if not normalized:
        raise ValueError("multimodal_embed_text requires non-empty text")
    return _embed_with_litellm(normalized, mode="text")


def multimodal_embed_image(b64_data: str) -> list[float]:
    raw = (b64_data or "").strip()
    if not raw:
        raise ValueError("multimodal_embed_image requires non-empty base64 payload")
    if raw.lower().startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    return _embed_with_litellm(_image_payload(raw), mode="image")


def multimodal_embed_video(b64_data: str) -> list[float]:
    raw = (b64_data or "").strip()
    if not raw:
        raise ValueError("multimodal_embed_video requires non-empty base64 payload")
    require_video_capable_model(force=True)
    if raw.lower().startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    return _embed_with_litellm(_video_payload(raw), mode="video")


def multimodal_embedding_dim() -> int:
    explicit = os.getenv("MULTIMODAL_EMBEDDING_DIM", "").strip()
    if not explicit:
        raise RuntimeError("MULTIMODAL_EMBEDDING_DIM env-var missing")
    try:
        dim = int(explicit)
    except ValueError as exc:
        raise RuntimeError(
            f"MULTIMODAL_EMBEDDING_DIM must be an integer, got {explicit!r}"
        ) from exc
    if dim <= 0:
        raise RuntimeError(
            f"MULTIMODAL_EMBEDDING_DIM must be > 0, got {dim}"
        )
    return dim

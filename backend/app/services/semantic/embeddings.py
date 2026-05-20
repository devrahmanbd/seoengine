import functools
import hashlib
import math

__all__ = ["embed_text", "cosine_similarity"]

_model: object | None = None


def _hash_fallback(text: str) -> list[float]:
    raw = hashlib.sha256(text.encode()).digest()
    vals = [b / 255.0 for b in raw]
    norm = math.sqrt(sum(v * v for v in vals))
    return [v / norm for v in vals] if norm > 0 else vals


def _get_model() -> object | None:
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        _model = None
    return _model


def _embed_with_model(text: str) -> list[float]:
    model = _get_model()
    if model is None:
        return _hash_fallback(text)
    emb = model.encode(text)  # type: ignore
    return emb.tolist()


@functools.lru_cache(maxsize=1000)
def embed_text(text: str) -> list[float]:
    return _embed_with_model(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

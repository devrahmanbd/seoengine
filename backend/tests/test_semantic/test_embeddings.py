import math
from unittest.mock import patch, MagicMock

from app.services.semantic.embeddings import (
    embed_text,
    cosine_similarity,
    _hash_fallback,
    _get_model,
)


def test_hash_fallback_returns_normalized_vector():
    vec = _hash_fallback("hello world")
    assert len(vec) == 32
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-6


def test_hash_fallback_deterministic():
    v1 = _hash_fallback("same text")
    v2 = _hash_fallback("same text")
    assert v1 == v2


def test_hash_fallback_different_inputs_different():
    v1 = _hash_fallback("text A")
    v2 = _hash_fallback("text B")
    assert v1 != v2


class TestEmbedText:
    def test_returns_list_of_floats(self):
        result = embed_text("test")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_uses_hash_fallback_when_no_model(self):
        with patch("app.services.semantic.embeddings._get_model", return_value=None):
            result = embed_text("hash fallback test")
        assert len(result) == 32
        norm = math.sqrt(sum(v * v for v in result))
        assert abs(norm - 1.0) < 1e-6

    def test_deterministic_output(self):
        v1 = embed_text("deterministic test")
        v2 = embed_text("deterministic test")
        assert v1 == v2

    def test_lru_cache_hits(self):
        key = "cache_test_key"
        first = embed_text(key)
        second = embed_text(key)
        assert first is second

    def test_lru_cache_different_inputs(self):
        a = embed_text("alpha")
        b = embed_text("beta")
        assert a is not b

    def test_embed_text_with_model_returns_384_dim(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 384

        with patch("app.services.semantic.embeddings._get_model", return_value=mock_model):
            result = embed_text("model test")
            assert len(result) == 384
            mock_model.encode.assert_called_once_with("model test")

    def test_model_encode_called_with_correct_text(self):
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.5] * 384

        with patch("app.services.semantic.embeddings._get_model", return_value=mock_model):
            embed_text("specific text")
            mock_model.encode.assert_called_once_with("specific text")

    def test_get_model_returns_model_instance(self):
        result = _get_model()
        assert result is not None
        assert hasattr(result, "encode")


class TestCosineSimilarity:
    def test_identical_vectors(self):
        vec = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == 1.0

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_parallel_same_direction(self):
        a = [2.0, 4.0]
        b = [1.0, 2.0]
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_mismatched_lengths(self):
        assert cosine_similarity([1.0, 0.0], [1.0]) == 0.0

    def test_zero_vector_first(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_zero_vector_second(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 0.0]) == 0.0

    def test_both_zero_vectors(self):
        assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0

    def test_with_hash_fallback_vectors(self):
        a = _hash_fallback("hello")
        b = _hash_fallback("hello")
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_cosine_similarity_symmetric(self):
        a = [0.5, 0.5, 0.5, 0.5]
        b = [1.0, 0.0, 0.0, 0.0]
        assert abs(cosine_similarity(a, b) - cosine_similarity(b, a)) < 1e-6

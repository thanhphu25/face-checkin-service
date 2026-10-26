import numpy as np
import pytest

from app.domain.embeddings import normalize_embedding
from app.domain.errors import FaceEmbeddingFailed


def test_normalization_returns_float32_without_changing_input() -> None:
    original = np.array([3.0, 9.0, 4.0, 9.0], dtype=np.float64)

    result = normalize_embedding(original[::2])

    np.testing.assert_array_equal(result, np.array([0.6, 0.8], dtype=np.float32))
    np.testing.assert_array_equal(original, [3.0, 9.0, 4.0, 9.0])
    assert result.dtype == np.float32
    assert result.flags.c_contiguous


@pytest.mark.parametrize("source", ["Face embedder", "InsightFace"])
@pytest.mark.parametrize(
    ("embedding", "reason"),
    [
        (np.array([]), "an invalid"),
        (np.array(1.0), "an invalid"),
        (np.ones((1, 2)), "an invalid"),
        (np.array([np.nan, 1.0]), "an invalid"),
        (np.array([np.inf, 1.0]), "an invalid"),
        (np.zeros(2), "a zero-length"),
        (np.array([np.finfo(np.float32).eps, 0.0]), "a zero-length"),
        (np.full(2, np.finfo(np.float32).max), "a zero-length"),
    ],
)
def test_normalization_preserves_validation_errors(
    embedding: np.ndarray, reason: str, source: str
) -> None:
    with np.errstate(over="ignore"), pytest.raises(FaceEmbeddingFailed) as caught:
        normalize_embedding(embedding, source=source)

    assert str(caught.value) == f"{source} returned {reason} embedding"

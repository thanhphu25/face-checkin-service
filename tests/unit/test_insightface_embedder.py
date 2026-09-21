from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.domain import (
    FaceEmbeddingFailed,
    InvalidImage,
    MultipleFacesDetected,
    NoFaceDetected,
)
from app.ml import InsightFaceEmbedder


class FakeAnalysis:
    def __init__(self, faces: list[SimpleNamespace]) -> None:
        self.faces = faces
        self.calls: list[tuple[np.ndarray, int]] = []

    def get(self, image: np.ndarray, max_num: int = 0) -> list[SimpleNamespace]:
        self.calls.append((image, max_num))
        return self.faces


def _image_bytes() -> bytes:
    ok, encoded = cv2.imencode(".png", np.full((8, 8, 3), 127, dtype=np.uint8))
    assert ok
    return encoded.tobytes()


def test_embed_returns_contiguous_float32_l2_normalized_vector() -> None:
    analysis = FakeAnalysis([SimpleNamespace(embedding=np.array([3.0, 4.0]))])
    embedder = InsightFaceEmbedder(model_name="buffalo_s", analysis=analysis)

    embedding = embedder.embed(_image_bytes())

    assert embedder.model_name == "buffalo_s"
    assert embedding.dtype == np.float32
    assert embedding.flags.c_contiguous
    np.testing.assert_allclose(embedding, np.array([0.6, 0.8], dtype=np.float32))
    assert np.linalg.norm(embedding) == pytest.approx(1.0)
    assert analysis.calls[0][1] == 2


@pytest.mark.parametrize("payload", [b"", b"not-an-image"])
def test_embed_rejects_invalid_image_bytes(payload: bytes) -> None:
    with pytest.raises(InvalidImage):
        InsightFaceEmbedder(analysis=FakeAnalysis([])).embed(payload)


def test_embed_rejects_images_without_exactly_one_face() -> None:
    with pytest.raises(NoFaceDetected):
        InsightFaceEmbedder(analysis=FakeAnalysis([])).embed(_image_bytes())

    faces = [SimpleNamespace(embedding=np.ones(2)), SimpleNamespace(embedding=np.ones(2))]
    with pytest.raises(MultipleFacesDetected):
        InsightFaceEmbedder(analysis=FakeAnalysis(faces)).embed(_image_bytes())


@pytest.mark.parametrize(
    "embedding",
    [None, np.zeros(2), np.array([np.nan, 1.0]), np.ones((1, 2))],
)
def test_embed_rejects_unusable_model_output(embedding: np.ndarray | None) -> None:
    analysis = FakeAnalysis([SimpleNamespace(embedding=embedding)])

    with pytest.raises(FaceEmbeddingFailed):
        InsightFaceEmbedder(analysis=analysis).embed(_image_bytes())

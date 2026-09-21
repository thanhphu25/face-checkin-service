from collections.abc import Sequence
from typing import Any, Protocol

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.domain.errors import (
    FaceEmbeddingFailed,
    InvalidImage,
    MultipleFacesDetected,
    NoFaceDetected,
)
from app.domain.ports import FaceEmbedder


class _FaceAnalysis(Protocol):
    def get(self, image: np.ndarray, max_num: int = 0) -> Sequence[Any]: ...


class InsightFaceEmbedder(FaceEmbedder):
    """CPU InsightFace adapter for one-face registration and check-in images."""

    def __init__(
        self,
        model_name: str = "buffalo_s",
        *,
        providers: Sequence[str] = ("CPUExecutionProvider",),
        detection_size: tuple[int, int] = (640, 640),
        model_root: str = "~/.insightface",
        analysis: _FaceAnalysis | None = None,
    ) -> None:
        self._model_name = model_name
        if analysis is None:
            runtime = FaceAnalysis(name=model_name, root=model_root, providers=list(providers))
            runtime.prepare(ctx_id=0, det_size=detection_size)
            self._analysis: _FaceAnalysis = runtime
        else:
            self._analysis = analysis

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, image_bytes: bytes) -> np.ndarray:
        if not image_bytes:
            raise InvalidImage("Image is empty or cannot be decoded")

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            raise InvalidImage("Image is empty or cannot be decoded")

        faces = self._analysis.get(image, max_num=2)
        if not faces:
            raise NoFaceDetected("No face was detected in the image")
        if len(faces) > 1:
            raise MultipleFacesDetected("Exactly one face is required")

        raw_embedding = getattr(faces[0], "embedding", None)
        if raw_embedding is None:
            raise FaceEmbeddingFailed("InsightFace did not return an embedding")

        embedding = np.asarray(raw_embedding, dtype=np.float32)
        if embedding.ndim != 1 or embedding.size == 0 or not np.all(np.isfinite(embedding)):
            raise FaceEmbeddingFailed("InsightFace returned an invalid embedding")

        norm = float(np.linalg.norm(embedding))
        if not np.isfinite(norm) or norm <= np.finfo(np.float32).eps:
            raise FaceEmbeddingFailed("InsightFace returned a zero-length embedding")

        return np.ascontiguousarray(embedding / norm, dtype=np.float32)

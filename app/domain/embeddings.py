import numpy as np

from app.domain.errors import FaceEmbeddingFailed


def normalize_embedding(embedding: np.ndarray, *, source: str = "Face embedder") -> np.ndarray:
    """Kiểm tra vector và chuẩn hóa L2 về float32 liên tục trong bộ nhớ."""
    vector = np.asarray(embedding, dtype=np.float32)
    if vector.ndim != 1 or vector.size == 0 or not np.all(np.isfinite(vector)):
        raise FaceEmbeddingFailed(f"{source} returned an invalid embedding")

    norm = float(np.linalg.norm(vector))
    # Vector quá nhỏ hoặc tràn số không thể dùng để tính độ tương đồng cosine.
    if not np.isfinite(norm) or norm <= np.finfo(np.float32).eps:
        raise FaceEmbeddingFailed(f"{source} returned a zero-length embedding")
    return np.ascontiguousarray(vector / norm, dtype=np.float32)

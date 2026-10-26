"""Sample images derived from the public picture bundled with the InsightFace wheel.

Seeding and benchmarking need a face the embedder can actually
process. Deriving it from the installed wheel keeps real face photos out of Git
while every run still gets byte-identical input.
"""

from functools import lru_cache
from pathlib import Path

import cv2
import insightface

# Cắt đúng một khuôn mặt từ ảnh nhóm `t1.jpg` đi kèm package.
_FACE_CROP = (slice(290, 530), slice(690, 900))


def sample_image_path() -> Path:
    return Path(insightface.__file__).parent / "data" / "images" / "t1.jpg"


@lru_cache
def face_image_bytes() -> bytes:
    """Return a JPEG holding exactly one face."""
    source = sample_image_path()
    image = cv2.imread(str(source))
    if image is None:
        raise RuntimeError(f"Cannot read InsightFace sample image: {source}")
    encoded, payload = cv2.imencode(".jpg", image[_FACE_CROP])
    if not encoded:
        raise RuntimeError("Cannot encode the sample face crop")
    return payload.tobytes()

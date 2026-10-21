"""Sample images derived from the public picture bundled with the InsightFace wheel.

Seeding, verification and benchmarking all need a face the embedder can actually
process. Deriving it from the installed wheel keeps real face photos out of Git
while every run still gets byte-identical input.
"""

from functools import lru_cache
from pathlib import Path

import cv2
import insightface
import numpy as np

# Crop window of one face inside the bundled group photo `t1.jpg`.
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


@lru_cache
def no_face_image_bytes() -> bytes:
    """Return a PNG the detector must reject."""
    encoded, payload = cv2.imencode(".png", np.zeros((128, 128, 3), dtype=np.uint8))
    if not encoded:
        raise RuntimeError("Cannot encode the no-face sample image")
    return payload.tobytes()


def write_face_image(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(face_image_bytes())
    return destination

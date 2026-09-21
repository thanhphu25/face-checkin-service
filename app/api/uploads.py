from fastapi import UploadFile

from app.domain.errors import InvalidImage

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png"})


def read_image_upload(file: UploadFile, *, max_upload_mb: int) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidImage("Only JPEG and PNG images are accepted")

    max_bytes = max_upload_mb * 1024 * 1024
    payload = file.file.read(max_bytes + 1)
    if not payload:
        raise InvalidImage("Uploaded image is empty")
    if len(payload) > max_bytes:
        raise InvalidImage(f"Uploaded image exceeds the {max_upload_mb} MB limit")
    return payload

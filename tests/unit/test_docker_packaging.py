from pathlib import Path


def test_dockerfile_is_reproducible_multi_stage_and_non_root() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.count("FROM ") == 2
    assert "FROM python:3.12-slim AS builder" in dockerfile
    assert "FROM python:3.12-slim AS runtime" in dockerfile
    assert dockerfile.count("uv sync --frozen --no-dev") == 2
    assert "USER app" in dockerfile
    assert 'CMD ["uvicorn", "app.main:app"' in dockerfile
    assert 'CMD ["python", "-c", "import urllib.request;' in dockerfile
    assert "insightface/data/images" in dockerfile
    assert "onnx/backend/test" in dockerfile
    assert "curl" not in dockerfile


def test_docker_context_excludes_secrets_caches_models_and_face_data() -> None:
    ignored = set(Path(".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {
        ".git",
        ".venv",
        ".env",
        "*.db",
        ".pytest_cache",
        ".ruff_cache",
        "model_cache",
        ".insightface",
        "*.onnx",
        "faces",
        "uploads",
        "tmp",
        "output",
    } <= ignored

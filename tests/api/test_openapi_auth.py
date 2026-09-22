import ast
from pathlib import Path

from app.core.config import get_settings
from app.main import create_app


def test_openapi_declares_oauth2_and_locks_only_protected_operations(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "openapi-test-secret")
    get_settings.cache_clear()
    schema = create_app().openapi()

    scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert scheme["type"] == "oauth2"
    assert scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/login"

    protected = [
        ("/api/v1/auth/me", "get"),
        ("/api/v1/users", "post"),
        ("/api/v1/users/{user_id}", "get"),
        ("/api/v1/face-profiles", "post"),
        ("/api/v1/checkins", "get"),
        ("/api/v1/checkins/{record_id}", "delete"),
    ]
    for path, method in protected:
        assert schema["paths"][path][method]["security"] == [{"OAuth2PasswordBearer": []}]

    assert "security" not in schema["paths"]["/api/v1/auth/login"]["post"]
    assert "security" not in schema["paths"]["/api/v1/checkins"]["post"]


def test_routers_do_not_decode_or_lookup_tokens_in_handlers() -> None:
    violations: list[str] = []
    for source_path in Path("app/api/v1").glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "decode_access_token":
                violations.append(f"{source_path}:{node.lineno}")
            if isinstance(node, ast.Attribute) and node.attr == "decode_access_token":
                violations.append(f"{source_path}:{node.lineno}")

    assert violations == []

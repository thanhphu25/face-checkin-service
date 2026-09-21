import ast
from pathlib import Path

BANNED_IMPORTS = (
    "alembic",
    "fastapi",
    "sqlalchemy",
    "starlette",
    "app.api",
    "app.models",
    "app.repositories",
    "app.schemas",
)


def test_service_modules_do_not_import_web_framework_or_database() -> None:
    service_directory = Path("app/services")
    violations: list[str] = []

    for source_path in service_directory.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported = [node.module]
            else:
                continue
            for module in imported:
                if module.startswith(BANNED_IMPORTS):
                    violations.append(f"{source_path}:{node.lineno} imports {module}")

    assert violations == []

"""Write the OpenAPI document to a file so handover does not require a running app.

The committed copy is checked against the live schema in the test suite, so a
route or schema change that is not exported fails CI instead of silently leaving
stale documentation behind.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("docs/openapi.json")


def build_openapi() -> dict[str, Any]:
    # Settings validation must not force the exporter's caller to hold a real secret.
    os.environ.setdefault("JWT_SECRET", "openapi-export-only-not-a-real-secret")
    from app.main import app

    return dict(app.openapi())


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(build_openapi()), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

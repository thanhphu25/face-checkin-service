"""Run one complete baseline measurement: migrate, seed, serve, benchmark, stop.

Kaggle notebooks cannot run Docker, so this script reproduces what Compose does
in a single process tree: Alembic migration, sample data, a single-worker Uvicorn
server and the benchmark sweep. The same command runs locally, which is how the
Kaggle procedure is smoke-tested before it is trusted.
"""

import argparse
import asyncio
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

from scripts.benchmark import PASSWORD_ENV, parse_config, run_benchmark, write_results
from scripts.seed import USER_EMAIL, USER_PASSWORD_ENV

STARTUP_TIMEOUT_SECONDS = 180.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, choices=("sqlite", "postgresql"))
    parser.add_argument(
        "--database-url",
        default=None,
        help="Required for postgresql; defaults to a fresh file for sqlite.",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--requests", type=int, default=60, help="Check-in requests per concurrency level."
    )
    parser.add_argument(
        "--history-requests",
        type=int,
        default=1000,
        help="History requests per level; the read path is far faster than check-in.",
    )
    parser.add_argument("--concurrency", default="1,2,4,8")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/benchmark"))
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--keep-database",
        action="store_true",
        help="Keep the SQLite file instead of starting from an empty database.",
    )
    return parser


def resolve_database_url(args: argparse.Namespace) -> str:
    if args.backend == "postgresql":
        if not args.database_url:
            raise SystemExit("--database-url is required for the postgresql backend")
        return str(args.database_url)
    if args.database_url:
        return str(args.database_url)
    path = Path("benchmark-baseline.db").resolve()
    if path.exists() and not args.keep_database:
        path.unlink()
    return f"sqlite:///{path.as_posix()}"


def _child_env(database_url: str) -> dict[str, str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    if not env.get("JWT_SECRET"):
        raise SystemExit("JWT_SECRET must be set before running the baseline")
    return env


def migrate(database_url: str) -> None:
    print(f"==> alembic upgrade head ({database_url.split('@')[-1]})")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=_child_env(database_url),
        check=True,
    )


def seed_database(database_url: str) -> None:
    print("==> seeding sample data")
    subprocess.run(
        [sys.executable, "-m", "scripts.seed", "--database-url", database_url],
        env=_child_env(database_url),
        check=True,
    )


def start_server(database_url: str, port: int) -> subprocess.Popen[bytes]:
    print(f"==> starting uvicorn on port {port}")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--workers",
            "1",
            "--log-level",
            "warning",
        ],
        env=_child_env(database_url),
    )


def wait_until_healthy(base_url: str, server: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise SystemExit(f"Server exited early with code {server.returncode}")
        try:
            response = httpx.get(f"{base_url}/health", timeout=5.0)
        except httpx.HTTPError:
            time.sleep(0.5)
            continue
        if response.status_code == 200:
            print("==> server healthy")
            return
        time.sleep(0.5)
    raise SystemExit("Server did not become healthy in time")


def stop_server(server: subprocess.Popen[bytes]) -> None:
    if server.poll() is not None:
        return
    print("==> stopping uvicorn")
    server.send_signal(signal.SIGTERM)
    try:
        server.wait(timeout=20)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=10)


def measure(args: argparse.Namespace, base_url: str, server_pid: int) -> None:
    csv_path = args.output_dir / f"baseline-{args.backend}.csv"
    config = parse_config(
        [
            "--base-url",
            base_url,
            "--scenario",
            "both",
            "--requests",
            str(args.requests),
            "--history-requests",
            str(args.history_requests),
            "--concurrency",
            args.concurrency,
            "--warmup",
            str(args.warmup),
            "--login-email",
            USER_EMAIL,
            "--server-pid",
            str(server_pid),
            "--csv",
            str(csv_path),
            "--notes",
            args.notes or f"backend={args.backend}",
        ]
    )
    results = asyncio.run(run_benchmark(config))
    write_results(results, config)


def main() -> None:
    args = build_parser().parse_args()
    if not os.environ.get(USER_PASSWORD_ENV):
        raise SystemExit(f"{USER_PASSWORD_ENV} must be set so the benchmark can log in")
    # The history scenario authenticates as the seeded sample user.
    os.environ.setdefault(PASSWORD_ENV, os.environ[USER_PASSWORD_ENV])
    if shutil.which("git") is None:
        print("note: git is unavailable, metadata will omit the commit id")

    database_url = resolve_database_url(args)
    migrate(database_url)
    seed_database(database_url)

    base_url = f"http://127.0.0.1:{args.port}"
    server = start_server(database_url, args.port)
    try:
        wait_until_healthy(base_url, server)
        measure(args, base_url, server.pid)
    finally:
        stop_server(server)


if __name__ == "__main__":
    main()

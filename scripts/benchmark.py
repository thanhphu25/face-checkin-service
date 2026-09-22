"""Load harness for the phase 1 baseline.

Sweeps one or more concurrency levels against a running instance, reporting
latency percentiles, throughput and CPU usage per level. Results are written as
CSV plus a JSON metadata file so the phase 2 run can repeat the exact conditions.
"""

import argparse
import asyncio
import csv
import json
import math
import os
import platform
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx

CHECK_IN_SCENARIO = "checkin"
HISTORY_SCENARIO = "history"
SCENARIOS = (CHECK_IN_SCENARIO, HISTORY_SCENARIO)
PASSWORD_ENV = "BENCHMARK_PASSWORD"

CSV_COLUMNS = (
    "scenario",
    "concurrency",
    "requests",
    "elapsed_seconds",
    "throughput_rps",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "min_ms",
    "mean_ms",
    "max_ms",
    "ok_count",
    "error_count",
    "cpu_percent_system",
    "cpu_percent_server",
    "statuses",
)


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    base_url: str
    scenarios: tuple[str, ...]
    image_path: Path | None
    requests: int
    history_requests: int
    concurrency_levels: tuple[int, ...]
    warmup: int
    settle_seconds: float
    timeout_seconds: float
    login_email: str | None
    server_pid: int | None
    csv_path: Path | None
    notes: str

    def requests_for(self, scenario: str) -> int:
        return self.history_requests if scenario == HISTORY_SCENARIO else self.requests

    def url(self, path: str) -> str:
        return urljoin(f"{self.base_url.rstrip('/')}/", path.lstrip("/"))

    @property
    def check_in_url(self) -> str:
        return self.url("/api/v1/checkins")

    @property
    def history_url(self) -> str:
        return self.url("/api/v1/checkins?limit=50")

    @property
    def login_url(self) -> str:
        return self.url("/api/v1/auth/login")


@dataclass(frozen=True, slots=True)
class CpuUsage:
    """CPU utilisation measured across a run window, in percent of one core.

    A value above 100 means several cores were busy; divide by `cpu_count` in the
    metadata file to read it as a fraction of the whole machine.
    """

    system: float | None
    server: float | None


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    scenario: str
    concurrency: int
    requests: int
    elapsed_seconds: float
    latencies_ms: tuple[float, ...]
    statuses: dict[int | str, int]
    cpu: CpuUsage = field(default=CpuUsage(None, None))

    @property
    def requests_per_second(self) -> float:
        return self.requests / self.elapsed_seconds if self.elapsed_seconds else math.inf

    @property
    def ok_count(self) -> int:
        return sum(
            count
            for status, count in self.statuses.items()
            if isinstance(status, int) and 200 <= status < 400
        )

    @property
    def error_count(self) -> int:
        return self.requests - self.ok_count

    def as_row(self) -> dict[str, object]:
        return {
            "scenario": self.scenario,
            "concurrency": self.concurrency,
            "requests": self.requests,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "throughput_rps": round(self.requests_per_second, 3),
            "p50_ms": round(percentile(self.latencies_ms, 50), 2),
            "p95_ms": round(percentile(self.latencies_ms, 95), 2),
            "p99_ms": round(percentile(self.latencies_ms, 99), 2),
            "min_ms": round(min(self.latencies_ms), 2) if self.latencies_ms else math.nan,
            "mean_ms": (
                round(sum(self.latencies_ms) / len(self.latencies_ms), 2)
                if self.latencies_ms
                else math.nan
            ),
            "max_ms": round(max(self.latencies_ms), 2) if self.latencies_ms else math.nan,
            "ok_count": self.ok_count,
            "error_count": self.error_count,
            "cpu_percent_system": (None if self.cpu.system is None else round(self.cpu.system, 1)),
            "cpu_percent_server": (None if self.cpu.server is None else round(self.cpu.server, 1)),
            "statuses": ";".join(f"{key}={value}" for key, value in sorted_statuses(self.statuses)),
        }


def sorted_statuses(statuses: dict[int | str, int]) -> list[tuple[str, int]]:
    return sorted((str(key), value) for key, value in statuses.items())


def percentile(values: tuple[float, ...], percent: int) -> float:
    """Nearest-rank percentile, so a reported value is always an observed one."""
    if not values:
        return math.nan
    ordered = sorted(values)
    index = max(0, math.ceil(percent / 100 * len(ordered)) - 1)
    return ordered[index]


def parse_concurrency_levels(raw: str) -> tuple[int, ...]:
    levels = []
    for item in raw.split(","):
        text = item.strip()
        if not text:
            continue
        value = int(text)
        if value < 1:
            raise ValueError("--concurrency values must be at least 1")
        levels.append(value)
    if not levels:
        raise ValueError("--concurrency needs at least one value")
    return tuple(sorted(dict.fromkeys(levels)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--scenario",
        default="both",
        choices=(*SCENARIOS, "both"),
        help="checkin posts an image, history reads the authenticated check-in list.",
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        dest="image_path",
        help="Face image to upload; defaults to the InsightFace sample bundled with the wheel.",
    )
    parser.add_argument("--requests", type=int, default=100, help="Requests per concurrency level.")
    parser.add_argument(
        "--history-requests",
        type=int,
        default=None,
        help="Requests per level for the history scenario; it is far faster than check-in, "
        "so it needs more requests to fill a window CPU sampling can resolve.",
    )
    parser.add_argument("--concurrency", default="1,2,4,8", help="Comma separated levels.")
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Unmeasured requests per level; the first call also loads the embedding model.",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="Idle pause after warm-up so the previous level's CPU is not charged here.",
    )
    parser.add_argument("--timeout", type=float, default=60.0, dest="timeout_seconds")
    parser.add_argument(
        "--login-email",
        default=None,
        help=f"Account for the history scenario; password read from {PASSWORD_ENV}.",
    )
    parser.add_argument(
        "--server-pid",
        type=int,
        default=None,
        help="Process id of the API server, to report its CPU usage separately.",
    )
    parser.add_argument("--csv", type=Path, default=None, dest="csv_path")
    parser.add_argument("--notes", default="", help="Free text stored in the metadata file.")
    return parser


def parse_config(argv: list[str] | None = None) -> BenchmarkConfig:
    args = build_parser().parse_args(argv)
    if args.requests < 1:
        raise ValueError("--requests must be at least 1")
    history_requests = args.requests if args.history_requests is None else args.history_requests
    if history_requests < 1:
        raise ValueError("--history-requests must be at least 1")
    if args.warmup < 0:
        raise ValueError("--warmup cannot be negative")
    if args.settle_seconds < 0:
        raise ValueError("--settle-seconds cannot be negative")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout must be positive")
    levels = parse_concurrency_levels(args.concurrency)
    if max(levels) > min(args.requests, history_requests):
        raise ValueError("--concurrency cannot exceed the request count of any scenario")
    if args.image_path is not None and not args.image_path.is_file():
        raise ValueError(f"Image does not exist: {args.image_path}")
    scenarios = SCENARIOS if args.scenario == "both" else (args.scenario,)
    if HISTORY_SCENARIO in scenarios and not args.login_email:
        raise ValueError("--login-email is required for the history scenario")
    return BenchmarkConfig(
        base_url=args.base_url,
        scenarios=scenarios,
        image_path=args.image_path,
        requests=args.requests,
        history_requests=history_requests,
        concurrency_levels=levels,
        warmup=args.warmup,
        settle_seconds=args.settle_seconds,
        timeout_seconds=args.timeout_seconds,
        login_email=args.login_email,
        server_pid=args.server_pid,
        csv_path=args.csv_path,
        notes=args.notes,
    )


def load_face_image(config: BenchmarkConfig) -> tuple[str, bytes]:
    if config.image_path is not None:
        return config.image_path.name, config.image_path.read_bytes()
    from scripts.sample_images import face_image_bytes

    return "sample-face.jpg", face_image_bytes()


def _clock_ticks_per_second() -> float:
    return float(os.sysconf("SC_CLK_TCK")) if hasattr(os, "sysconf") else 100.0


def read_system_cpu_ticks() -> tuple[float, float] | None:
    """Return (busy, total) jiffies from /proc/stat, or None off Linux."""
    try:
        first_line = Path("/proc/stat").read_text(encoding="utf-8").split("\n", 1)[0]
    except OSError:
        return None
    fields = [float(value) for value in first_line.split()[1:]]
    if len(fields) < 5:
        return None
    idle = fields[3] + fields[4]
    total = sum(fields)
    return total - idle, total


def read_process_cpu_ticks(pid: int) -> float | None:
    """Return utime+stime jiffies for a process, or None when unavailable."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return None
    # The comm field is parenthesised and may contain spaces, so split after it.
    _, separator, rest = raw.partition(") ")
    if not separator:
        return None
    fields = rest.split()
    if len(fields) < 13:
        return None
    return float(fields[11]) + float(fields[12])


class CpuSampler:
    """Measure CPU utilisation between two points in time."""

    # Jiffies tick ~100 times per second, so a shorter window quantises into noise.
    MINIMUM_WINDOW_SECONDS = 0.5

    def __init__(self, server_pid: int | None) -> None:
        self._server_pid = server_pid
        self._system = read_system_cpu_ticks()
        self._server = read_process_cpu_ticks(server_pid) if server_pid else None
        self._started = time.monotonic()

    def finish(self) -> CpuUsage:
        elapsed = max(time.monotonic() - self._started, 1e-9)
        if elapsed < self.MINIMUM_WINDOW_SECONDS:
            return CpuUsage(system=None, server=None)
        system = None
        after_system = read_system_cpu_ticks()
        if self._system is not None and after_system is not None:
            busy = after_system[0] - self._system[0]
            total = after_system[1] - self._system[1]
            system = 100.0 * busy / total if total > 0 else None

        server = None
        if self._server_pid is not None and self._server is not None:
            after_server = read_process_cpu_ticks(self._server_pid)
            if after_server is not None:
                ticks = after_server - self._server
                server = 100.0 * (ticks / _clock_ticks_per_second()) / elapsed
        return CpuUsage(system=system, server=server)


async def login(client: httpx.AsyncClient, config: BenchmarkConfig) -> str:
    password = os.environ.get(PASSWORD_ENV, "")
    if not password:
        raise SystemExit(f"{PASSWORD_ENV} must be set for the history scenario")
    response = await client.post(
        config.login_url,
        data={"username": config.login_email, "password": password},
    )
    if response.status_code != 200:
        raise SystemExit(f"Login failed with HTTP {response.status_code}")
    return str(response.json()["access_token"])


def _request_factory(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    scenario: str,
    image: tuple[str, bytes],
    token: str | None,
):
    if scenario == CHECK_IN_SCENARIO:
        name, payload = image

        async def send_check_in() -> httpx.Response:
            return await client.post(
                config.check_in_url,
                files={"image": (name, payload, "image/jpeg")},
            )

        return send_check_in

    headers = {"Authorization": f"Bearer {token}"}

    async def send_history() -> httpx.Response:
        return await client.get(config.history_url, headers=headers)

    return send_history


async def _drive(send, count: int, concurrency: int) -> tuple[list[float], Counter[int | str]]:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    statuses: Counter[int | str] = Counter()

    async def one_request() -> None:
        async with semaphore:
            started = time.perf_counter()
            try:
                response = await send()
                statuses[response.status_code] += 1
            except httpx.HTTPError as exc:
                statuses[type(exc).__name__] += 1
            finally:
                latencies.append((time.perf_counter() - started) * 1000)

    await asyncio.gather(*(one_request() for _ in range(count)))
    return latencies, statuses


async def run_level(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    scenario: str,
    image: tuple[str, bytes],
    token: str | None,
    concurrency: int,
) -> BenchmarkResult:
    send = _request_factory(client, config, scenario, image, token)
    if config.warmup:
        await _drive(send, config.warmup, min(concurrency, config.warmup))

    # ONNX Runtime keeps its thread pool spinning after an inference, so CPU from
    # the previous level would otherwise be charged to this one.
    await asyncio.sleep(config.settle_seconds)

    count = config.requests_for(scenario)
    sampler = CpuSampler(config.server_pid)
    started = time.perf_counter()
    latencies, statuses = await _drive(send, count, concurrency)
    elapsed = time.perf_counter() - started
    return BenchmarkResult(
        scenario=scenario,
        concurrency=concurrency,
        requests=count,
        elapsed_seconds=elapsed,
        latencies_ms=tuple(latencies),
        statuses=dict(statuses),
        cpu=sampler.finish(),
    )


async def run_benchmark(config: BenchmarkConfig) -> list[BenchmarkResult]:
    image = (
        load_face_image(config) if CHECK_IN_SCENARIO in config.scenarios else ("unused.jpg", b"")
    )
    results: list[BenchmarkResult] = []
    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        token = await login(client, config) if HISTORY_SCENARIO in config.scenarios else None
        for scenario in config.scenarios:
            for concurrency in config.concurrency_levels:
                result = await run_level(client, config, scenario, image, token, concurrency)
                print_result(result)
                results.append(result)
    return results


def collect_metadata(config: BenchmarkConfig) -> dict[str, object]:
    return {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "base_url": config.base_url,
        "scenarios": list(config.scenarios),
        "requests_per_level": config.requests,
        "history_requests_per_level": config.history_requests,
        "concurrency_levels": list(config.concurrency_levels),
        "warmup_per_level": config.warmup,
        "settle_seconds": config.settle_seconds,
        "timeout_seconds": config.timeout_seconds,
        "image": str(config.image_path) if config.image_path else "insightface-sample-crop",
        "notes": config.notes,
    }


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def write_results(results: list[BenchmarkResult], config: BenchmarkConfig) -> None:
    if config.csv_path is None:
        return
    config.csv_path.parent.mkdir(parents=True, exist_ok=True)
    with config.csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(result.as_row())

    metadata_path = config.csv_path.with_suffix(".metadata.json")
    metadata_path.write_text(
        json.dumps(collect_metadata(config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {config.csv_path} and {metadata_path}")


def print_result(result: BenchmarkResult) -> None:
    row = result.as_row()
    cpu_system = row["cpu_percent_system"]
    cpu_server = row["cpu_percent_server"]
    print(
        f"{result.scenario:<8} c={result.concurrency:<3} "
        f"rps={row['throughput_rps']:<8} "
        f"p50={row['p50_ms']:<9} p95={row['p95_ms']:<9} p99={row['p99_ms']:<9} "
        f"cpu_sys={cpu_system if cpu_system is not None else 'n/a'}% "
        f"cpu_srv={cpu_server if cpu_server is not None else 'n/a'}% "
        f"errors={row['error_count']} statuses={row['statuses']}"
    )


def main() -> None:
    try:
        config = parse_config()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    results = asyncio.run(run_benchmark(config))
    write_results(results, config)


if __name__ == "__main__":
    main()

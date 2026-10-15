"""Configurable HTTP load harness for the final check-in endpoint.

This week-3 scaffold intentionally does not store a baseline. Week 6 will use the
same CLI and record hardware metadata together with measured results.
"""

import argparse
import asyncio
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    base_url: str
    endpoint: str
    image_path: Path
    requests: int
    concurrency: int
    timeout_seconds: float

    @property
    def url(self) -> str:
        return urljoin(f"{self.base_url.rstrip('/')}/", self.endpoint.lstrip("/"))


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    requests: int
    elapsed_seconds: float
    latencies_ms: tuple[float, ...]
    statuses: dict[int | str, int]

    @property
    def requests_per_second(self) -> float:
        return self.requests / self.elapsed_seconds if self.elapsed_seconds else math.inf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/api/v1/checkins")
    parser.add_argument("--image", required=True, type=Path, dest="image_path")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0, dest="timeout_seconds")
    return parser


def parse_config(argv: list[str] | None = None) -> BenchmarkConfig:
    args = build_parser().parse_args(argv)
    if args.requests < 1:
        raise ValueError("--requests must be at least 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")
    if args.concurrency > args.requests:
        raise ValueError("--concurrency cannot exceed --requests")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout must be positive")
    if not args.image_path.is_file():
        raise ValueError(f"Image does not exist: {args.image_path}")
    return BenchmarkConfig(**vars(args))


async def run_benchmark(config: BenchmarkConfig) -> BenchmarkResult:
    image_bytes = config.image_path.read_bytes()
    queue: asyncio.Queue[int] = asyncio.Queue()
    for request_number in range(config.requests):
        queue.put_nowait(request_number)

    latencies: list[float] = []
    statuses: Counter[int | str] = Counter()

    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:

        async def worker() -> None:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                started = time.perf_counter()
                try:
                    response = await client.post(
                        config.url,
                        files={"image": (config.image_path.name, image_bytes, "image/jpeg")},
                    )
                    statuses[response.status_code] += 1
                except httpx.HTTPError as exc:
                    statuses[type(exc).__name__] += 1
                finally:
                    latencies.append((time.perf_counter() - started) * 1000)
                    queue.task_done()

        started = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(config.concurrency)))
        elapsed = time.perf_counter() - started

    return BenchmarkResult(
        requests=config.requests,
        elapsed_seconds=elapsed,
        latencies_ms=tuple(latencies),
        statuses=dict(statuses),
    )


def percentile(values: tuple[float, ...], percent: int) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = max(0, math.ceil(percent / 100 * len(ordered)) - 1)
    return ordered[index]


def print_result(config: BenchmarkConfig, result: BenchmarkResult) -> None:
    print(f"URL: {config.url}")
    print(f"Requests/concurrency: {result.requests}/{config.concurrency}")
    print(f"Statuses: {result.statuses}")
    print(f"Throughput: {result.requests_per_second:.2f} req/s")
    print(
        "Latency: "
        f"p50={percentile(result.latencies_ms, 50):.2f} ms "
        f"p95={percentile(result.latencies_ms, 95):.2f} ms "
        f"p99={percentile(result.latencies_ms, 99):.2f} ms"
    )


def main() -> None:
    try:
        config = parse_config()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    result = asyncio.run(run_benchmark(config))
    print_result(config, result)


if __name__ == "__main__":
    main()

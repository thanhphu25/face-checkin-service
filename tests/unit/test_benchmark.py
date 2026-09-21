from pathlib import Path

import pytest

from scripts.benchmark import BenchmarkResult, parse_config, percentile


def test_benchmark_config_uses_final_check_in_url_and_explicit_load(tmp_path: Path) -> None:
    image = tmp_path / "input.jpg"
    image.write_bytes(b"test-only-bytes")

    config = parse_config(
        [
            "--base-url",
            "http://localhost:9000/",
            "--image",
            str(image),
            "--requests",
            "20",
            "--concurrency",
            "5",
            "--timeout",
            "10",
        ]
    )

    assert config.url == "http://localhost:9000/api/v1/checkins"
    assert config.requests == 20
    assert config.concurrency == 5
    assert config.timeout_seconds == 10


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--requests", "0"], "--requests"),
        (["--requests", "2", "--concurrency", "3"], "--concurrency"),
        (["--timeout", "0"], "--timeout"),
    ],
)
def test_benchmark_config_rejects_invalid_load_values(
    tmp_path: Path, arguments: list[str], message: str
) -> None:
    image = tmp_path / "input.jpg"
    image.write_bytes(b"test-only-bytes")

    with pytest.raises(ValueError, match=message):
        parse_config(["--image", str(image), *arguments])


def test_benchmark_result_calculates_throughput_and_nearest_rank_percentiles() -> None:
    result = BenchmarkResult(
        requests=4,
        elapsed_seconds=2.0,
        latencies_ms=(10.0, 20.0, 30.0, 40.0),
        statuses={201: 4},
    )

    assert result.requests_per_second == 2.0
    assert percentile(result.latencies_ms, 50) == 20.0
    assert percentile(result.latencies_ms, 95) == 40.0

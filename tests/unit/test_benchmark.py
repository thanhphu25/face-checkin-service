import os
from pathlib import Path

import pytest

from scripts.benchmark import (
    CSV_COLUMNS,
    BenchmarkResult,
    CpuSampler,
    CpuUsage,
    collect_metadata,
    parse_concurrency_levels,
    parse_config,
    percentile,
    write_results,
)


def _result(**overrides) -> BenchmarkResult:
    defaults = {
        "scenario": "checkin",
        "concurrency": 4,
        "requests": 4,
        "elapsed_seconds": 2.0,
        "latencies_ms": (10.0, 20.0, 30.0, 40.0),
        "statuses": {201: 4},
        "cpu": CpuUsage(system=63.5, server=88.25),
    }
    return BenchmarkResult(**{**defaults, **overrides})


def test_benchmark_config_uses_final_urls_and_sweeps_concurrency() -> None:
    config = parse_config(
        [
            "--base-url",
            "http://localhost:9000/",
            "--requests",
            "20",
            "--concurrency",
            "8,1,4,4",
            "--warmup",
            "3",
            "--timeout",
            "10",
            "--login-email",
            "user.sample@example.test",
        ]
    )

    assert config.check_in_url == "http://localhost:9000/api/v1/checkins"
    assert config.history_url == "http://localhost:9000/api/v1/checkins?limit=50"
    assert config.login_url == "http://localhost:9000/api/v1/auth/login"
    assert config.scenarios == ("checkin", "history")
    assert config.concurrency_levels == (1, 4, 8)
    assert config.requests == 20
    assert config.warmup == 3
    assert config.timeout_seconds == 10
    assert config.image_path is None


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--requests", "0"], "--requests"),
        (["--requests", "2", "--concurrency", "3"], "--concurrency"),
        (["--concurrency", "0"], "--concurrency"),
        (["--timeout", "0"], "--timeout"),
        (["--warmup", "-1"], "--warmup"),
    ],
)
def test_benchmark_config_rejects_invalid_load_values(arguments: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_config(["--login-email", "user.sample@example.test", *arguments])


def test_benchmark_config_requires_an_account_for_the_history_scenario() -> None:
    with pytest.raises(ValueError, match="--login-email"):
        parse_config(["--scenario", "history"])


def test_benchmark_config_rejects_a_missing_image(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image does not exist"):
        parse_config(["--scenario", "checkin", "--image", str(tmp_path / "absent.jpg")])


def test_parse_concurrency_levels_deduplicates_and_orders() -> None:
    assert parse_concurrency_levels(" 4, 1 ,4,16 ") == (1, 4, 16)


def test_benchmark_result_reports_throughput_percentiles_and_outcomes() -> None:
    result = _result(elapsed_seconds=2.0, statuses={201: 3, "ReadTimeout": 1}, requests=4)

    assert result.requests_per_second == 2.0
    assert percentile(result.latencies_ms, 50) == 20.0
    assert percentile(result.latencies_ms, 95) == 40.0
    assert result.ok_count == 3
    assert result.error_count == 1

    row = result.as_row()
    assert row["p99_ms"] == 40.0
    assert row["mean_ms"] == 25.0
    assert row["cpu_percent_system"] == 63.5
    assert row["cpu_percent_server"] == 88.2
    assert row["statuses"] == "201=3;ReadTimeout=1"


def test_write_results_emits_csv_and_metadata(tmp_path: Path) -> None:
    csv_path = tmp_path / "nested" / "baseline-sqlite.csv"
    config = parse_config(
        [
            "--scenario",
            "checkin",
            "--requests",
            "4",
            "--concurrency",
            "4",
            "--csv",
            str(csv_path),
            "--notes",
            "backend=sqlite",
        ]
    )

    write_results([_result()], config)

    header, row = csv_path.read_text(encoding="utf-8").splitlines()[:2]
    assert header.split(",") == list(CSV_COLUMNS)
    assert row.startswith("checkin,4,4,")

    metadata = collect_metadata(config)
    assert metadata["concurrency_levels"] == [4]
    assert metadata["requests_per_level"] == 4
    assert metadata["image"] == "insightface-sample-crop"
    assert metadata["notes"] == "backend=sqlite"
    assert csv_path.with_suffix(".metadata.json").is_file()


def test_cpu_sampler_reports_nothing_for_a_window_too_short_to_resolve() -> None:
    sampler = CpuSampler(server_pid=os.getpid())

    usage = sampler.finish()

    assert usage.system is None
    assert usage.server is None


def test_benchmark_config_scopes_request_counts_per_scenario() -> None:
    config = parse_config(
        [
            "--requests",
            "40",
            "--history-requests",
            "800",
            "--login-email",
            "user.sample@example.test",
        ]
    )

    assert config.requests_for("checkin") == 40
    assert config.requests_for("history") == 800

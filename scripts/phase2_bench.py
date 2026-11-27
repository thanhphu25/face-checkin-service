"""Prepare immutable fixtures on A, run isolated cells, and compare repeated measurements."""

import argparse
import asyncio
import csv
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from contextlib import closing, suppress
from pathlib import Path
from statistics import median

import httpx
import numpy as np

from scripts import benchmark as bench

BASE = "247db09d98f4cedcc9ad22fdbd112ba328324aa9"
ROOT = Path(__file__).resolve().parents[1]
EMAIL = "user.sample@example.test"
SEED = 23020023
FIXTURES = {"E1": "single", "E2": "history", "M1": "single"}
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_WAIT_POLICY")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha(repo):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def save(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)


def environment(db):
    return {**os.environ, "DATABASE_URL": f"sqlite:///{db.resolve().as_posix()}"}


def extend(db, fixture):
    """Extend the one real profile without changing its owner, embedding or id."""
    with closing(sqlite3.connect(db)) as conn, conn:
        [(profile, user, raw, dim, model)] = conn.execute(
            "SELECT p.id,p.user_id,p.embedding,p.embedding_dim,p.model_name FROM face_profiles p "
            "JOIN users u ON u.id=p.user_id WHERE u.email=?",
            (EMAIL,),
        )
        if fixture == "history":
            for i in range(60):
                conn.execute(
                    "INSERT INTO check_in_records(user_id,matched_face_profile_id,checkin_time,"
                    "similarity_score,threshold,status) VALUES(?,?,?,1,.4,'success')",
                    (user, profile, f"2020-01-01 00:00:{i:02}"),
                )
        if fixture in ("pure", "mixed"):
            query = np.frombuffer(raw, np.float32)
            rng = np.random.default_rng(SEED)
            for i in range(1, 1000):
                noise = rng.standard_normal(dim, dtype=np.float32)
                noise /= np.linalg.norm(noise)
                if noise @ query >= query @ query:
                    raise ValueError("oracle has no unique top-1")
                noise_model = model if fixture == "pure" or i < 500 else "other"
                conn.execute(
                    "INSERT INTO face_profiles(user_id,embedding,embedding_dim,model_name,"
                    "created_at) VALUES(?,?,?,?,'2020-01-01')",
                    (user, noise.tobytes(), dim, noise_model),
                )
        counts = dict(conn.execute("SELECT model_name,count(*) FROM face_profiles GROUP BY 1"))
        total = 1000 if fixture in ("pure", "mixed") else 1
        if sum(counts.values()) != total or counts[model] != (500 if fixture == "mixed" else total):
            raise ValueError(f"unexpected gallery: {counts}")
        history = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM check_in_records WHERE user_id=? "
                "ORDER BY checkin_time DESC,id DESC LIMIT 50",
                (user,),
            )
        ]
        if fixture == "history" and len(history) != 50:
            raise ValueError("history must fill a page")
    return dict(profile=profile, user=user, models=counts, history=history, sha256=digest(db))


def target(args, db, *command):
    subprocess.run([args.python, *command], cwd=args.app, env=environment(db), check=True)


def prepare(args):
    if sha(args.app) != BASE:
        raise ValueError("prepare requires the baseline checkout")
    args.fixtures.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "seed.db"
        target(args, db, "-m", "alembic", "upgrade", "0002")
        target(args, db, "-m", "scripts.seed")
        image = args.fixtures / "sample.jpg"
        target(
            args,
            db,
            "-c",
            "import sys;from pathlib import Path;"
            "from scripts.sample_images import face_image_bytes;"
            "Path(sys.argv[1]).write_bytes(face_image_bytes())",
            str(image.resolve()),
        )
        manifest = dict(app=BASE, seed=SEED, image=digest(image), fixtures={})
        for name in ("single", "history", "pure", "mixed"):
            path = args.fixtures / f"{name}.db"
            with closing(sqlite3.connect(db)) as source, closing(sqlite3.connect(path)) as dest:
                source.backup(dest)
            manifest["fixtures"][name] = extend(path, name)
        save(args.fixtures / "manifest.json", manifest)


def inspect_body(response, history, oracle):
    expected = 200 if history else 201
    if response.status_code != expected:
        return False, None
    try:
        body = response.json()
        if history:
            ids = [r["id"] for r in body if r["user_id"] == oracle["user"]]
            return len(ids) == len(body) and ids == oracle["history"], None
        valid = (
            body["status"] == "success"
            and body["user_id"] == oracle["user"]
            and body["matched_face_profile_id"] == oracle["profile"]
            and type(body["id"]) is int
        )
        return valid, body["id"] if valid else None
    except (KeyError, TypeError, ValueError):
        return False, None


async def drive(send, count, concurrency, history, oracle):
    slots = asyncio.Semaphore(concurrency)

    async def one():
        async with slots:
            started = time.perf_counter()
            try:
                response = await send()
            except httpx.HTTPError as exc:
                return (time.perf_counter() - started) * 1000, type(exc).__name__, False, None
            ms = (time.perf_counter() - started) * 1000
            valid, record = inspect_body(response, history, oracle)
            return ms, response.status_code, valid, record

    return await asyncio.gather(*(one() for _ in range(count)))


async def sample_rss(pid, samples):
    while True:
        path = Path(f"/proc/{pid}/status")
        if not path.exists():
            return
        for line in path.read_text().splitlines():
            if line.startswith("VmRSS:"):
                samples.append(int(line.split()[1]))
                break
        await asyncio.sleep(0.05)


def audit(db, before, rows, history, oracle):
    with closing(sqlite3.connect(db)) as conn:
        new = list(
            conn.execute(
                "SELECT id,user_id,matched_face_profile_id,status FROM check_in_records WHERE id>?",
                (before,),
            )
        )
    ids = [r[3] for r in rows if r[3] is not None]
    expected = [] if history else [(i, oracle["user"], oracle["profile"], "success") for i in ids]
    return len(new), sorted(expected) == sorted(new) and len(ids) == len(set(ids))


async def http_cell(args, oracle, image, db, pid):
    history = args.scenario == "E2"
    scenario = "history" if history else "checkin"
    config = bench.parse_config(
        [
            "--scenario",
            scenario,
            "--login-email",
            EMAIL,
            "--base-url",
            f"http://127.0.0.1:{args.port}",
        ]
    )
    count = args.count or (1000 if history else 60)
    with closing(sqlite3.connect(db)) as conn:
        before = conn.execute("SELECT coalesce(max(id),0) FROM check_in_records").fetchone()[0]
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        os.environ[bench.PASSWORD_ENV] = os.environ["SEED_USER_PASSWORD"]
        token = await bench.login(client, config) if history else None
        send = bench._request_factory(client, config, scenario, ("sample.jpg", image), token)
        warm = await drive(send, 5, args.c, history, oracle)
        await asyncio.sleep(2)
        rss = []
        monitor = asyncio.create_task(sample_rss(pid, rss))
        sampler = bench.CpuSampler(pid)
        start = time.perf_counter()
        try:
            rows = await drive(send, count, args.c, history, oracle)
            elapsed = time.perf_counter() - start
            cpu = sampler.finish()
        finally:
            monitor.cancel()
            with suppress(asyncio.CancelledError):
                await monitor
    actual, audit_ok = audit(db, before, warm + rows, history, oracle)
    expected = 0 if history else count + len(warm)
    ok = sum(r[2] for r in rows)
    status = 200 if history else 201
    completed = sum(isinstance(r[1], int) for r in rows)
    return rows, {
        "expected": count,
        "actual": len(rows),
        "audit_actual": actual,
        "audit_expected": expected,
        "warmup_ok": sum(r[2] for r in warm),
        "warmup_expected": 5,
        "statuses": dict(Counter(str(r[1]) for r in rows)),
        "passed": ok == count and all(r[2] for r in warm) and audit_ok and actual == expected,
        "errors": count - ok,
        "timeouts": sum("Timeout" in str(r[1]) for r in rows),
        "http_errors": completed - sum(r[1] == status for r in rows),
        "body_errors": sum(r[1] == status and not r[2] for r in rows),
        "cpu_system": cpu.system,
        "cpu_process": cpu.server,
        "rss_kib": max(rss, default=None),
        "rps": completed / elapsed,
        "success_rps": ok / elapsed,
    }


def run(args):
    from scripts.run_baseline import stop_server, wait_until_healthy

    fixture = FIXTURES.get(args.scenario, args.gallery)
    manifest = json.loads((args.fixtures / "manifest.json").read_text())
    oracle = manifest["fixtures"][fixture]
    source = args.fixtures / f"{fixture}.db"
    img = args.fixtures / "sample.jpg"
    if (
        manifest["app"] != BASE
        or digest(source) != oracle["sha256"]
        or digest(img) != manifest["image"]
    ):
        raise ValueError("fixture checksum or baseline mismatch")
    app_sha = sha(args.app)
    folder = args.output / app_sha / f"{args.scenario}-{fixture}" / f"c{args.c}" / f"r{args.round}"
    folder.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        machine = Path(tmp) / "machine.json"
        db = Path(tmp) / "run.db"
        target(
            args,
            db,
            "-c",
            "import sys,runpy;runpy.run_path(sys.argv.pop(1),run_name='__main__')",
            str(Path(__file__).resolve()),
            "_machine",
            str(machine),
        )
        machine_data = json.loads(machine.read_text())
        shutil.copyfile(source, db)
        if args.scenario in ("probe", "M1"):
            out = Path(tmp) / "probe.json"
            target(
                args,
                db,
                "-c",
                "import sys,runpy;runpy.run_path(sys.argv.pop(1),run_name='__main__')",
                str(Path(__file__).resolve()),
                "_probe",
                args.scenario,
                str(db),
                str(img.resolve()),
                str(out),
                str(oracle["profile"]),
            )
            data = json.loads(out.read_text())
            rows = data.pop("rows")
        else:
            server = subprocess.Popen(
                [
                    args.python,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.port),
                    "--workers",
                    "1",
                    "--log-level",
                    "warning",
                ],
                cwd=args.app,
                env=environment(db),
            )
            try:
                wait_until_healthy(f"http://127.0.0.1:{args.port}", server)
                rows, data = asyncio.run(http_cell(args, oracle, img.read_bytes(), db, server.pid))
            finally:
                stop_server(server)
    with (folder / "requests.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("latency_ms", "status", "body_ok", "record_id"))
        writer.writerows(rows)
    latencies = tuple(row[0] for row in rows)
    data.update({f"p{p}_ms": bench.percentile(latencies, p) for p in (50, 95, 99)})
    data.update(
        measured_at=time.time(),
        app=app_sha,
        runner=sha(ROOT),
        lock=digest(args.app / "uv.lock"),
        snapshot=oracle["sha256"],
        image=manifest["image"],
        scenario=args.scenario,
        fixture=fixture,
        concurrency=args.c,
        round=args.round,
        session=args.session,
        workers=1,
        client_python=platform.python_version(),
        os=platform.platform(),
        cpu_count=os.cpu_count(),
        threads={key: os.environ.get(key) for key in THREADS},
    )
    data["machine"] = machine_data
    save(folder / "metadata.json", data)
    if not data["passed"]:
        raise SystemExit("cell failed oracle; raw results retained")


def machine_info(args):
    from importlib.metadata import version

    import onnxruntime

    model = os.environ.get("EMBEDDING_MODEL", "buffalo_s")
    model_dir = Path.home() / ".insightface" / "models" / model
    files = {p.name: digest(p) for p in sorted(model_dir.glob("*.onnx"))}
    if not files:
        raise ValueError(f"cache {model} before measurement")

    def linux_file(name):
        path = Path(name)
        return path.read_text().strip() if path.exists() else None

    cpuinfo = linux_file("/proc/cpuinfo") or ""
    meminfo = linux_file("/proc/meminfo") or ""
    save(
        args.result,
        dict(
            python=platform.python_version(),
            sqlite=sqlite3.sqlite_version,
            packages={k: version(k) for k in ("numpy", "insightface", "onnxruntime", "uvicorn")},
            model_sha256=files,
            cpu=next((x for x in cpuinfo.splitlines() if "model name" in x), platform.processor()),
            affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
            quota=linux_file("/sys/fs/cgroup/cpu.max"),
            ram=next((x for x in meminfo.splitlines() if x.startswith("MemTotal")), None),
            available_providers=onnxruntime.get_available_providers(),
            token_minutes=os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"),
        ),
    )


def probe(args):
    from sqlalchemy.orm import Session

    from app.api.deps import get_check_in_service, get_embedder, get_engine

    with closing(sqlite3.connect(args.db)) as db:
        raw, model = db.execute(
            "SELECT embedding,model_name FROM face_profiles WHERE id=?", (args.profile,)
        ).fetchone()
    query = np.frombuffer(raw, np.float32)
    payload = args.image.read_bytes()
    adapter = None
    cold = None
    sessions = None
    if args.kind == "M1":
        start = time.perf_counter()
        adapter = get_embedder()
        cold = (time.perf_counter() - start) * 1000
        sessions = {}
        for name, component in getattr(getattr(adapter, "_analysis", None), "models", {}).items():
            inference = component.session
            options = inference.get_session_options()
            sessions[name] = dict(
                providers=inference.get_providers(),
                intra=options.intra_op_num_threads,
                inter=options.inter_op_num_threads,
            )

    class CachedEmbedding:
        model_name = model

        def embed(self, _):
            return query

    class Capture:
        def add(self, record):
            return record

    sampler = None
    rows = []
    scores = []
    with Session(get_engine()) as session:
        service = get_check_in_service(session, CachedEmbedding())
        service._check_ins = Capture()
        for i in range(65):
            start = time.perf_counter()
            if args.kind == "M1":
                vector = adapter.embed(payload)
                ms = (time.perf_counter() - start) * 1000
                score = float(vector @ query)
                ok = bool(np.allclose(vector, query, atol=1e-5, rtol=1e-4) and score >= 0.4)
                if i >= 5:
                    scores.append(score)
            else:
                record = service.check_in(payload)
                ms = (time.perf_counter() - start) * 1000
                ok = record.matched_face_profile_id == args.profile
            if i < 5 and not ok:
                raise ValueError("probe warm-up parity failed")
            if i == 4:
                time.sleep(2)
                sampler = bench.CpuSampler(os.getpid())
                window = time.perf_counter()
            if i >= 5:
                rows.append((ms, "ok" if ok else "mismatch", ok, None))
    elapsed = time.perf_counter() - window
    cpu = sampler.finish()
    rss = Path("/proc/self/status")
    peak = (
        next(
            (int(s.split()[1]) for s in rss.read_text().splitlines() if s.startswith("VmHWM:")),
            None,
        )
        if rss.exists()
        else None
    )
    save(
        args.result,
        dict(
            rows=rows,
            cold_init_ms=cold,
            rss_kib=peak,
            ort_sessions=sessions,
            cpu_system=cpu.system,
            cpu_process=cpu.server,
            rps=len(rows) / elapsed,
            success_rps=sum(r[2] for r in rows) / elapsed,
            faces_per_accepted_image=1 if args.kind == "M1" else None,
            min_cosine=min(scores, default=None),
            errors=sum(not r[2] for r in rows),
            statuses=dict(Counter(r[1] for r in rows)),
            expected=60,
            actual=len(rows),
            passed=all(r[2] for r in rows),
        ),
    )


def compare(args):
    groups = defaultdict(dict)
    for path in args.output.glob("*/*/c*/r*/metadata.json"):
        d = json.loads(path.read_text())
        if d["app"] not in (args.a, args.b) or d["session"] != args.session:
            continue
        key = d["scenario"], d["fixture"], d["concurrency"]
        groups[key].setdefault(d["app"], {})[d["round"]] = d
    if not groups or args.a == args.b:
        raise ValueError("need distinct measured arms")
    result = []
    matrix = {
        (scenario, fixture, c)
        for scenario, fixtures, levels in (
            ("E1", ("single",), (1, 2, 4, 8)),
            ("E2", ("history",), (1, 2, 4, 8)),
            ("E3", ("pure", "mixed"), (1, 4)),
            ("probe", ("pure", "mixed"), (1,)),
            ("M1", ("single",), (1,)),
        )
        for fixture in fixtures
        for c in levels
    }
    if set(groups) != matrix:
        raise ValueError(f"incomplete or unexpected workload: {set(groups) ^ matrix}")
    for key, arms in sorted(groups.items()):
        a, b = (arms.get(s, {}) for s in (args.a, args.b))
        if a.keys() != b.keys() or len(a) < 3:
            raise ValueError(f"missing paired rounds for {key}")
        for n in a:
            if (a[n]["measured_at"] < b[n]["measured_at"]) != (n % 2 == 1):
                raise ValueError(f"wrong A/B order for {key}, round {n}")
        cells = [*a.values(), *b.values()]
        expected = 1000 if key[0] == "E2" else 60
        if any(d["expected"] != expected or d["actual"] != expected for d in cells):
            raise ValueError(f"wrong workload size for {key}")
        for field in ("runner", "snapshot", "image", "expected", "threads", "cpu_count", "machine"):
            if any(d[field] != cells[0][field] for d in cells):
                raise ValueError(f"incompatible {field} for {key}")
        for metric in (
            "p50_ms",
            "p95_ms",
            "p99_ms",
            "rps",
            "success_rps",
            "cpu_system",
            "cpu_process",
            "rss_kib",
            "cold_init_ms",
        ):
            if any(d.get(metric) is None for d in cells):
                continue
            x, y = ([d[metric] for d in arm.values()] for arm in (a, b))
            delta = median(y) - median(x)
            sign = -1 if metric.endswith("_ms") else 1
            result.append(
                [
                    *key,
                    metric,
                    len(x),
                    min(x),
                    median(x),
                    max(x),
                    min(y),
                    median(y),
                    max(y),
                    delta,
                    sign * 100 * delta / median(x) if median(x) else None,
                    all(d["passed"] for d in cells),
                ]
            )
    with args.table.open("x", newline="") as stream:
        w = csv.writer(stream)
        w.writerow(
            [
                "scenario",
                "fixture",
                "c",
                "metric",
                "pairs",
                "a_min",
                "a_median",
                "a_max",
                "b_min",
                "b_median",
                "b_max",
                "delta_b_a",
                "change_percent",
                "all_oracles_pass",
            ]
        )
        w.writerows(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    run_parser = sub.add_parser("run")
    for p in (prep, run_parser):
        p.add_argument("--app", type=Path, required=True)
        p.add_argument("--python", type=Path, required=True)
        p.add_argument("--fixtures", type=Path, required=True)
    run_parser.add_argument("--scenario", choices=("E1", "E2", "E3", "probe", "M1"), required=True)
    run_parser.add_argument("--gallery", choices=("pure", "mixed"), default="pure")
    run_parser.add_argument("--c", type=int, choices=(1, 2, 4, 8), default=1)
    run_parser.add_argument("--round", type=int, required=True)
    run_parser.add_argument("--count", type=int)
    run_parser.add_argument("--port", type=int, default=8765)
    comp = sub.add_parser("compare")
    for p in (comp, run_parser):
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--session", required=True)
    for key in ("a", "b"):
        comp.add_argument("--" + key, required=True)
    comp.add_argument("--table", type=Path, required=True)
    sub.add_parser("_machine").add_argument("result", type=Path)
    inner = sub.add_parser("_probe")
    inner.add_argument("kind")
    for field in ("db", "image", "result"):
        inner.add_argument(field, type=Path)
    inner.add_argument("profile", type=int)
    args = parser.parse_args()
    if args.action in ("prepare", "run"):
        args.app = args.app.resolve()
        args.python = args.python.absolute()
        for repo in (args.app, ROOT):
            if subprocess.check_output(["git", "status", "--porcelain", "-uno"], cwd=repo).strip():
                parser.error(f"commit tracked changes before measurement: {repo}")
    if args.action == "run":
        if args.count is not None and args.count < 1:
            parser.error("count must be positive")
        if args.scenario in ("probe", "M1") and (args.c != 1 or args.count is not None):
            parser.error("probes require C=1 and 60 measured requests")
    {"prepare": prepare, "run": run, "compare": compare, "_probe": probe, "_machine": machine_info}[
        args.action
    ](args)


if __name__ == "__main__":
    main()

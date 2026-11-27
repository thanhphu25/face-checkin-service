import asyncio
import csv
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from argparse import Namespace
from contextlib import closing
from pathlib import Path

import httpx
import numpy as np

from scripts import phase2_bench as runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / "seed.db"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("""
                CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT);
                CREATE TABLE face_profiles(id INTEGER PRIMARY KEY,user_id,embedding,
                    embedding_dim,model_name,created_at);
                CREATE TABLE check_in_records(id INTEGER PRIMARY KEY,user_id,
                    matched_face_profile_id,checkin_time,similarity_score,threshold,status);
            """)
            conn.execute("INSERT INTO users VALUES(7,?)", (runner.EMAIL,))
            vec = np.zeros(512, np.float32)
            vec[0] = 1
            conn.execute(
                "INSERT INTO face_profiles VALUES(9,7,?,512,'buffalo_s','2020')", (vec.tobytes(),)
            )

    def test_gallery_reproducible_and_scoped(self):
        for name, count in [("pure", 1000), ("mixed", 500)]:
            copies = []
            for n in (1, 2):
                path = self.root / f"{name}{n}.db"
                shutil.copyfile(self.db, path)
                copies.append(runner.extend(path, name))
            self.assertEqual(copies[0], copies[1])
            self.assertEqual(copies[0]["models"]["buffalo_s"], count)
            self.assertEqual((copies[0]["user"], copies[0]["profile"]), (7, 9))

    def test_history_limit_and_identity(self):
        oracle = runner.extend(self.db, "history")
        self.assertEqual(oracle["history"], list(range(60, 10, -1)))
        page = [{"user_id": 7, "id": i} for i in oracle["history"]]
        for data, ok in [
            (page, True),
            (page[::-1], False),
            (page[:-1], False),
            (page + [{"user_id": 8, "id": 100}], False),
        ]:
            self.assertEqual(
                runner.inspect_body(httpx.Response(200, json=data), True, oracle)[0], ok
            )

    def test_two_smokes_copy_snapshot_and_check_audit_ids(self):
        oracle = runner.extend(self.db, "single")
        for n in (1, 2):
            db = self.root / f"run{n}.db"
            shutil.copyfile(self.db, db)
            self.assertEqual(runner.digest(db), oracle["sha256"])
            with closing(sqlite3.connect(db)) as conn:

                async def send(conn=conn):
                    cur = conn.execute(
                        "INSERT INTO check_in_records(user_id,"
                        "matched_face_profile_id,status) VALUES(7,9,'success')"
                    )
                    conn.commit()
                    return httpx.Response(
                        201,
                        json={
                            "id": cur.lastrowid,
                            "user_id": 7,
                            "matched_face_profile_id": 9,
                            "status": "success",
                        },
                    )

                rows = asyncio.run(runner.drive(send, 6, 2, False, oracle))
            self.assertEqual(runner.audit(db, 0, rows, False, oracle), (6, True))
            self.assertEqual(runner.audit(db, 0, rows[:-1] + rows[:1], False, oracle), (6, False))
            self.assertEqual(runner.digest(self.db), oracle["sha256"])

    def test_http_cell_counts_warmup_separately(self):
        from unittest.mock import patch

        oracle = runner.extend(self.db, "single")
        for n in (1, 2):
            db = self.root / f"cell-{n}.db"
            shutil.copyfile(self.db, db)
            self.assertEqual(runner.digest(db), oracle["sha256"])
            with closing(sqlite3.connect(db)) as conn:

                def respond(request, conn=conn):
                    self.assertEqual(request.method, "POST")
                    self.assertEqual(request.url.path, "/api/v1/checkins")
                    row = conn.execute(
                        "INSERT INTO check_in_records(user_id,matched_face_profile_id,status) "
                        "VALUES(7,9,'success')"
                    )
                    conn.commit()
                    return httpx.Response(
                        201,
                        json=dict(
                            status="success", user_id=7, matched_face_profile_id=9, id=row.lastrowid
                        ),
                    )

                client = httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False)
                args = Namespace(scenario="E1", port=8765, count=6, c=2)
                with (
                    patch.object(httpx, "AsyncClient", return_value=client),
                    patch.dict(os.environ, {"SEED_USER_PASSWORD": "test-only"}),
                ):
                    pending = runner.http_cell(args, oracle, b"test", db, os.getpid())
                    rows, meta = asyncio.run(pending)
            self.assertTrue(meta["passed"])
            self.assertEqual((meta["actual"], meta["warmup_ok"], meta["audit_actual"]), (6, 5, 11))
            self.assertEqual(runner.digest(self.db), oracle["sha256"])
            if dest := os.environ.get("PHASE2_LOCAL_SMOKE"):
                folder = Path(dest) / f"r{n}"
                folder.mkdir(parents=True, exist_ok=False)
                runner.save(
                    folder / "metadata.json",
                    dict(
                        meta,
                        transport="httpx.MockTransport",
                        app=None,
                        runner=runner.sha(runner.ROOT),
                        snapshot=oracle["sha256"],
                        user=7,
                        profile=9,
                        concurrency=2,
                    ),
                )
                with (folder / "requests.csv").open("x", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(("latency_ms", "status", "body_ok", "record_id"))
                    writer.writerows(rows)

    def test_failed_requests_count_toward_latency(self):
        async def send():
            raise httpx.ReadTimeout("timeout")

        rows = asyncio.run(runner.drive(send, 3, 2, False, {}))
        self.assertEqual([r[1:] for r in rows], [("ReadTimeout", False, None)] * 3)
        ok, _ = runner.inspect_body(httpx.Response(201, json=[]), False, {"user": 7})
        self.assertFalse(ok)

    def test_compare_uses_per_round_median_without_overwrite(self):
        args = Namespace(
            output=self.root, a="aaa", b="bbb", session="test", table=self.root / "table.csv"
        )
        for arm, values in [(args.a, (1, 10, 40)), (args.b, (2, 8, 14))]:
            for n, value in enumerate(values, 1):
                matrix = [
                    ("E1", "single", (1, 2, 4, 8)),
                    ("E2", "history", (1, 2, 4, 8)),
                    ("E3", "pure", (1, 4)),
                    ("E3", "mixed", (1, 4)),
                    ("probe", "pure", (1,)),
                    ("probe", "mixed", (1,)),
                    ("M1", "single", (1,)),
                ]
                for scenario, fixture, levels in matrix:
                    for c in levels:
                        folder = self.root / arm / f"{scenario}-{fixture}" / f"c{c}" / f"r{n}"
                        folder.mkdir(parents=True)
                        count = 1000 if scenario == "E2" else 60
                        sample = dict(
                            app=arm,
                            session="test",
                            scenario=scenario,
                            fixture=fixture,
                            concurrency=c,
                            round=n,
                            runner="r",
                            snapshot="s",
                            image="i",
                            expected=count,
                            actual=count,
                            threads={},
                            cpu_count=4,
                            measured_at=n * 2 + int((arm == args.b) == (n % 2 == 1)),
                            machine={},
                            p95_ms=value,
                            passed=True,
                        )
                        (folder / "metadata.json").write_text(json.dumps(sample))
        runner.compare(args)
        with args.table.open() as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(
            (row["a_median"], row["b_median"], row["change_percent"]), ("10", "8", "20.0")
        )
        with self.assertRaises(FileExistsError):
            runner.compare(args)

    def test_probe_skips_embedder_load_for_gallery_benchmark(self):
        from datetime import UTC, datetime
        from unittest.mock import patch

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.api import deps
        from app.core.config import get_settings
        from app.domain import FaceProfile
        from app.models import UserORM
        from app.models.base import Base
        from app.repositories import SQLAlchemyFaceProfileRepository

        db = self.root / "probe.db"
        img = self.root / "sample.jpg"
        img.write_bytes(b"unused")
        out = self.root / "probe.json"
        engine = create_engine(f"sqlite:///{db.as_posix()}")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        now = datetime.now(UTC)
        vec = np.zeros(512, np.float32)
        vec[0] = 1
        with Session(engine) as session, session.begin():
            session.add(
                UserORM(
                    id=7,
                    email="u7@example.test",
                    hashed_password="x",
                    role="user",
                    full_name="User 7",
                    created_at=now,
                )
            )
            session.flush()
            SQLAlchemyFaceProfileRepository(session).add(
                FaceProfile(None, 7, vec, "buffalo_s", now)
            )

        get_settings.cache_clear()
        self.addCleanup(get_settings.cache_clear)
        args = Namespace(kind="probe", db=db, image=img, result=out, profile=1)
        with (
            patch.dict(
                os.environ,
                {"JWT_SECRET": "test-only", "DATABASE_URL": f"sqlite:///{db.as_posix()}"},
            ),
            patch.object(
                deps, "get_embedder", side_effect=AssertionError("must not load embedder")
            ),
            patch.object(deps, "get_engine", return_value=engine),
            patch.object(runner.time, "sleep"),
        ):
            runner.probe(args)

        data = json.loads(out.read_text())
        self.assertTrue(data["passed"])
        self.assertEqual(data["actual"], 60)
        self.assertIsNone(data["cold_init_ms"])
        self.assertIsNone(data["ort_sessions"])


class TransactionTests(unittest.TestCase):
    def test_matching_skips_different_dimension(self):
        from datetime import UTC, datetime
        from unittest.mock import Mock

        from app.domain import FaceProfile
        from app.services import CheckInService

        query = np.array([1.0, 0.0], dtype=np.float32)
        now = datetime.now(UTC)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.models import UserORM
        from app.models.base import Base
        from app.repositories import SQLAlchemyFaceProfileRepository

        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        session = Session(engine)
        self.addCleanup(session.close)
        session.add(
            UserORM(
                id=7,
                email="u7@example.test",
                hashed_password="x",
                role="user",
                full_name="User 7",
                created_at=now,
            )
        )
        session.flush()
        profiles = SQLAlchemyFaceProfileRepository(session)
        candidates = [(np.ones(3, np.float32), "model"), (query, "other"), (query, "model")]
        for vector, model in candidates:
            profiles.add(FaceProfile(None, 7, vector, model, now))
        audit = Mock()
        audit.add.side_effect = lambda record: record
        embedder = Mock(model_name="model")
        embedder.embed.return_value = query
        service = CheckInService(audit, profiles, embedder, threshold=0.4)
        self.assertEqual(service.check_in(b"sample").matched_face_profile_id, 3)

    @unittest.skipUnless(os.environ.get("PHASE2_R1") == "1", "run R1 against each app checkout")
    def test_r1_ten_independent_requests_per_case(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.api import deps
        from app.core.config import get_settings
        from app.domain import InvalidImage, MultipleFacesDetected, NoFaceDetected
        from app.models.base import Base
        from app.repositories import SQLAlchemyCheckInRepository

        class Embedder:
            model_name = "buffalo_s"

            def embed(self, data):
                if data == b"empty":
                    raise NoFaceDetected("no face")
                if data == b"invalid":
                    raise InvalidImage("bad image")
                return np.array([1.0, 0.0], dtype=np.float32)

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {"JWT_SECRET": "test-only"}),
        ):
            db = Path(tmp) / "r1.db"
            engine = create_engine(f"sqlite:///{db.as_posix()}")
            self.addCleanup(engine.dispose)
            Base.metadata.create_all(engine)
            get_settings.cache_clear()
            from app.main import create_app

            app = create_app()
            app.dependency_overrides[deps.get_embedder] = Embedder
            factory = sessionmaker(engine)
            original = SQLAlchemyCheckInRepository.add

            report = os.environ.get("PHASE2_R1_CSV")
            if report:
                stream = self.enterContext(open(report, "x", newline="", encoding="utf-8"))
                writer = csv.writer(stream)
                writer.writerow(
                    (
                        "case",
                        "trial",
                        "expected_http",
                        "actual_http",
                        "record_id",
                        "audit_count",
                        "audit_rows",
                    )
                )
            case = ""

            def fail_after_flush(repo, record):
                original(repo, record)
                if case == "business":
                    raise MultipleFacesDetected("injected business error")
                raise RuntimeError("injected after flush")

            with (
                patch.object(deps, "get_session_factory", return_value=factory),
                TestClient(app, raise_server_exceptions=False) as client,
                closing(sqlite3.connect(db)) as conn,
            ):
                for case, status, error, audit in (
                    ("empty", 422, "NoFaceDetected", "no_face"),
                    ("unmatched", 404, "UnmatchedFace", "unmatched"),
                    ("invalid", 400, "InvalidImage", None),
                    ("business", 422, "MultipleFacesDetected", None),
                    ("system", 500, None, None),
                ):
                    for trial in range(10):
                        with self.subTest(case=case, trial=trial):
                            before = conn.execute(
                                "SELECT coalesce(max(id),0) FROM check_in_records"
                            ).fetchone()[0]
                            inject = case in ("system", "business")
                            method = fail_after_flush if inject else original
                            with patch.object(SQLAlchemyCheckInRepository, "add", method):
                                resp = client.post(
                                    "/api/v1/checkins",
                                    files={"image": ("fixture.jpg", case.encode(), "image/jpeg")},
                                )
                            delta = conn.execute(
                                "SELECT id,status FROM check_in_records WHERE id>?", (before,)
                            ).fetchall()
                            body = resp.json() if error and resp.status_code < 500 else {}
                            if report:
                                writer.writerow(
                                    (
                                        case,
                                        trial + 1,
                                        status,
                                        resp.status_code,
                                        body.get("record_id"),
                                        len(delta),
                                        json.dumps(delta),
                                    )
                                )
                            self.assertEqual(resp.status_code, status)
                            self.assertEqual(body.get("error"), error)
                            self.assertEqual(delta, [(body["record_id"], audit)] if audit else [])
                            if not audit:
                                self.assertNotIn("record_id", body)
            get_settings.cache_clear()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()

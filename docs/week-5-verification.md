# Xác minh hoàn tất kỹ thuật Tuần 5

Ngày chạy cuối: 2026-09-22.

## Môi trường và phạm vi

- Docker Engine/CLI 29.8.1, Docker Compose v5.5.1.
- Image ứng dụng dùng Python 3.12.14; môi trường host dùng Python 3.12.3 và uv 0.12.5.
- PostgreSQL 16.15 (`postgres:16-alpine`) và Redis 7.4.11 (`redis:7.4-alpine`).
- InsightFace 2.0, ONNX Runtime 1.23.2, model chính thức `buffalo_s` chạy CPU.
- Secret, user, password, database, port và Compose project trong tài liệu này đều là giá trị giả,
  chỉ dùng cho verification.

`uv sync --frozen --extra dev` đã tạo lại môi trường từ `uv.lock`. Không có `.env`, database,
model cache, ONNX, ảnh khuôn mặt, token hoặc output kiểm thử được thêm vào Git.

## Repository integration thật

Cùng một bộ test trong `tests/integration/test_repositories.py` chạy qua implementation
SQLAlchemy, mapper domain và schema Alembic thật trên hai backend. SQLite dùng file tạm của pytest;
PostgreSQL dùng database có tên chứa `test`, được migrate trước khi test và rollback từng case.

```text
POSTGRES_TEST_DATABASE_URL=postgresql+psycopg://.../facecheckin_w5_final_test
REQUIRE_POSTGRES_TESTS=1
uv run alembic upgrade head
uv run pytest -q tests/integration -p no:cacheprovider

17 passed
alembic_version=0002
users|face_profiles|check_in_records=0|0|0 sau test
```

Các assertion đã kiểm chứng trên cả SQLite và PostgreSQL:

- CRUD và mapper ORM/domain của `User`, `FaceProfile`, `CheckInRecord`; `Role.ADMIN` và ba giá trị
  `CheckInStatus` được round-trip đúng.
- Embedding đầu vào được lưu/đọc lại dưới dạng little-endian `float32`; dimension, bytes và
  `model_name=buffalo_s` khớp chính xác.
- Unique email phát sinh `IntegrityError` thật.
- Xóa profile đặt `matched_face_profile_id` trong lịch sử về `NULL`; xóa user cascade profile và
  đặt cả hai khóa ngoại lịch sử về `NULL`; bản ghi lịch sử vẫn còn.
- Filter `user_id`, `start`, `end`, thứ tự mới nhất trước và `limit` đều đúng.
- SQLite trả `PRAGMA foreign_keys=1`; metadata PostgreSQL ghi `ON DELETE SET NULL`.

Migration `0002` là head hiện tại, thay vì `0001` dự kiến ban đầu. Migration này được thêm sau khi
test PostgreSQL thật phát hiện CHECK constraint của `success` xung đột với `ON DELETE SET NULL` khi
ẩn danh lịch sử. Không có database dev nào bị migrate, reset hoặc drop trong verification.

## Docker image

Các lệnh chính đã chạy:

```text
docker build --tag face-checkin-service:week5-c02-verify .
docker run ... face-checkin-service:week5-c02-verify
docker build --tag face-checkin-service:ci .
```

Kết quả đã xác minh:

- Build multi-stage thành công từ `uv.lock` bằng `uv sync --frozen --no-dev`.
- Process Uvicorn chạy bằng user không phải root, UID/GID `10001:10001`.
- `/health` trả 200; `/openapi.json` đọc được.
- Chạy image mà không cấp `JWT_SECRET` kết thúc mã 1 với lỗi validation cấu hình rõ ràng.
- Runtime không cài pytest/compiler/dev dependency; sample face, model cache và ONNX test assets bị
  loại khỏi image. `.dockerignore` loại Git, `.venv`, `.env`, database, cache, model và ảnh/output.
- Docker healthcheck dùng Python standard library, không phụ thuộc `curl`.

## Compose, migration và persistence

Project cách ly `facecheckin_w5_c03_20260922` đã được build/up thật. `docker compose ps -a` cho thấy
app, PostgreSQL và Redis healthy; service `migrate` chạy `alembic upgrade head` và exited 0.

```text
PostgreSQL: 16.15, healthy, alembic_version=0002
Redis: 7.4.11, healthy, PONG
App: healthy, /health=200, OpenAPI truy cập được
App SQLAlchemy dialect: postgresql
```

Một admin và user giả tạm thời đã được tạo qua Repository để kiểm tra OAuth2/JWT. Login thành công;
user vẫn tồn tại sau khi restart riêng app, chứng minh dữ liệu nằm trong PostgreSQL volume chứ không
nằm trong container app. Redis chỉ được dựng sẵn cho Pha 2 và chưa được application sử dụng.

## CI và mô phỏng job cục bộ

Workflow `.github/workflows/ci.yml` có bốn job độc lập:

1. `quality-and-sqlite`: sync lockfile, Ruff lint/format, import-linter, app smoke và unit/API/SQLite
   integration; marker `real_model` bị loại chủ ý.
2. `postgres-integration`: PostgreSQL service thật có healthcheck, migration Alembic và integration
   test với `REQUIRE_POSTGRES_TESTS=1`, nên thiếu URL hoặc không chạy PostgreSQL sẽ làm job fail.
3. `docker-image`: build production image từ `Dockerfile`.
4. `compose-clean-setup`: checkout trên GitHub-hosted Ubuntu runner, build Compose không dùng cache,
   chạy migration/app/PostgreSQL/Redis, kiểm tra health/OpenAPI/kết nối DB rồi `down -v` và xác nhận
   không còn container/volume mang label project test.

Các lệnh tương đương job đã chạy cục bộ trước commit:

```text
uv sync --frozen --extra dev
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
uv run pytest -q -m "not real_model" tests/unit tests/api tests/integration
# 91 passed, 8 skipped (PostgreSQL không cấp cho job nhẹ), 1 deselected

POSTGRES_TEST_DATABASE_URL=postgresql+psycopg://.../facecheckin_ci_test
REQUIRE_POSTGRES_TESTS=1 uv run pytest -q tests/integration -p no:cacheprovider
# 17 passed

docker build --tag face-checkin-service:ci .
# thành công
```

Real-model E2E không chạy trong CI thường để tránh tải model nặng ngoài chủ ý. Tài liệu này không dùng
kết quả mô phỏng cục bộ để tuyên bố GitHub Actions xanh. Sau push, GitHub Actions run
[`35700197582`](https://github.com/thanhphu25/face-checkin-service/actions/runs/35700197582) của commit
`909a1b6` đã hoàn tất thành công ở lần chạy đầu: `quality-and-sqlite`, `postgres-integration` và
`docker-image` đều xanh.

Follow-up commit `0b1ac68` kích hoạt GitHub Actions run
[`35703077030`](https://github.com/thanhphu25/face-checkin-service/actions/runs/35703077030), hoàn tất
thành công ngay lần chạy đầu với cả bốn job. Riêng job
[`compose-clean-setup`](https://github.com/thanhphu25/face-checkin-service/actions/runs/35703077030/job/106665430253)
chạy trên GitHub-hosted Ubuntu runner độc lập và xác nhận từng bước sau đều `success`:

- validate Compose config;
- build image từ đầu bằng `docker compose build --no-cache`;
- `docker compose up -d --wait` cho app, migration, PostgreSQL và Redis;
- revision `0002`, PostgreSQL dialect, Redis `PONG`, `/health` và `/openapi.json`;
- `docker compose down -v --remove-orphans`;
- không còn container hoặc volume mang label project `facecheckin_ci_clean`.

Ba job còn lại (`quality-and-sqlite`, `postgres-integration`, `docker-image`) cũng đều `success`.

## Clean-directory / clean-setup

Một clone tạm được tạo tại `/tmp/facecheckin-w5-clean-OQWy5C/repo` từ commit `23afa53`. Trước khi
chạy, clone không có `.venv`, `.env`, database, `.insightface`, model hoặc ONNX. uv dùng cache tạm
riêng; Compose dùng project `facecheckin_w5_clean_20260922`, database
`facecheckin_w5_clean_test`, image `face-checkin-service:week5-clean-verify` và port riêng.

Các bước và kết quả:

```text
uv sync --frozen --extra dev                         # cài 83 package từ lockfile
docker compose ... config --quiet                    # pass
docker compose ... build --no-cache                  # pass, build từ đầu
docker compose ... up -d --wait                      # pass
docker compose ... ps -a                             # app/PG/Redis healthy; migrate exited 0
GET /health                                          # 200 {"status":"ok"}
GET /openapi.json                                    # title đúng, 9 paths
app dialect/current database                         # postgresql/facecheckin_w5_clean_test
redis-cli ping                                       # PONG
pytest -q tests/integration -p no:cacheprovider      # 17 passed
ruff check / format --check / lint-imports           # pass; 3/3 contracts kept
```

Database ở revision `0002` và có `0|0|0` row sau test. Trước cleanup, bốn container và hai named
volume đều được kiểm tra có label `com.docker.compose.project=facecheckin_w5_clean_20260922`. Sau
`docker compose -p facecheckin_w5_clean_20260922 down -v --remove-orphans`, truy vấn theo label trả
rỗng cho cả container và volume.

Lượt `/tmp` ở trên chỉ là clean-directory/clean-setup trên cùng máy và tự nó không đủ để thay cho
máy khác. Sau đó, GitHub Actions run `35703077030` đã chạy toàn bộ Compose trên GitHub-hosted runner
sạch, tách biệt với máy phát triển. Chủ project chấp thuận dùng bằng chứng kỹ thuật này thay cho test
chéo trên máy cá nhân của A/C; checklist nói rõ phương án thay thế và không tuyên bố thành viên A/C
đã trực tiếp thực hiện.

## E2E thật và quality gates cuối

```text
RUN_REAL_MODEL_TESTS=1 uv run pytest -q tests/api/test_real_embedding_e2e.py
# 1 passed: buffalo_s, 512 chiều, float32, norm 1.0, persist/check-in/auth/RBAC thật

POSTGRES_TEST_DATABASE_URL=postgresql+psycopg://.../facecheckin_w5_final_test
REQUIRE_POSTGRES_TESTS=1 RUN_REAL_MODEL_TESTS=1 uv run pytest -q -p no:cacheprovider
# 100 passed, 1 warning in 5.18s
```

Warning duy nhất là `FutureWarning` từ `insightface/utils/face_align.py`, không phải test failure.
Ruff lint, Ruff format, import-linter, `git diff --check` và lockfile sync đều pass. Service layer vẫn
giữ 3/3 import contract, không import FastAPI/Starlette/SQLAlchemy/Pydantic schema/Repository impl.

## Cleanup và phần còn chờ xác nhận

Các tài nguyên test đã dọn:

- Compose project `facecheckin_w5_c03_20260922` và `facecheckin_w5_clean_20260922`, gồm database,
  container, network và named volume test.
- PostgreSQL container/database riêng của Repository, CI simulation và final suite.
- PostgreSQL container/database follow-up dùng để chạy lại suite sau khi thêm hosted Compose job.
- Clone/cache tạm `/tmp/facecheckin-w5-clean-OQWy5C` dùng cho clean-directory verification.
- Dữ liệu bootstrap giả; không có row test còn lại trước khi database bị xóa.

Không xóa hoặc reset database/container/volume dev. Image verification được giữ lại cục bộ để có thể
đối chiếu; image không chứa dữ liệu hay secret.

Hai hoạt động con người từ Tuần 4 đã được chủ project chấp thuận thay bằng
[technical review auth có cấu trúc](week-4-auth-technical-review.md). Đây là tiêu chí thay thế, không
phải tuyên bố pair session hoặc review chéo A/C của con người đã diễn ra.

Theo tiêu chí kỹ thuật thay thế đã được chủ project chấp thuận, không còn checkbox Tuần 4–5 nào
thiếu bằng chứng. Các hoạt động sau vẫn không được tài liệu này tuyên bố là đã diễn ra:

- Review README của A/B nếu nhóm yêu cầu biên bản xác nhận.
- Seed toàn diện, benchmark/baseline, OpenAPI export và release/tag thuộc Tuần 6.

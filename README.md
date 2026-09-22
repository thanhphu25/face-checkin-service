# Face Check-in Service

Backend điểm danh bằng khuôn mặt dùng FastAPI, SQLAlchemy/Alembic, PostgreSQL và InsightFace. Tài
liệu này dành cho người nhận project mà không cần hỏi lại tác giả.

Trạng thái hiện tại: Pha 1 đã có Repository, API, JWT/RBAC, image Docker, Compose, integration test
và seed dữ liệu mẫu tái lập. Benchmark baseline đang là công việc Tuần 6, chưa được tuyên bố hoàn
thành.

## 1. Nghiệp vụ và phạm vi

Một user có thể đăng ký nhiều hồ sơ khuôn mặt. Khi một ảnh được gửi tới máy chấm công, hệ thống sinh
embedding, so khớp với các profile cùng model/dimension và luôn ghi lại kết quả `success`,
`unmatched` hoặc `no_face`.

| Pha | Trong phạm vi | Ngoài phạm vi hiện tại |
|---|---|---|
| Pha 1 | CRUD `User`/`FaceProfile`/`CheckInRecord`, InsightFace CPU, JWT/RBAC, migration, Docker/Compose và baseline ở Tuần 6 | refresh token, liveness, cache, async DB, ANN index |
| Pha 2 | Chỉ chọn 2–3 cải tiến sau khi đo lại baseline | Không mặc định Redis cache, pgvector/FAISS hay multi-worker trước khi có số liệu |

Redis có trong Compose để chuẩn bị hạ tầng Pha 2 nhưng **application Pha 1 chưa sử dụng Redis**.

## 2. Kiến trúc

```text
Client / Swagger
       │ HTTP + JSON/multipart, OAuth2 bearer
       ▼
API layer             app/api, app/schemas
       │ gọi use case, ánh xạ lỗi/DTO
       ▼
Service layer         app/services — Python thuần
       │ chỉ phụ thuộc domain port
       ▼
Repository ports      app/domain
       ▲
       │ implements + ORM↔domain mapping
SQLAlchemy adapters   app/repositories, app/models
       │
       ▼
PostgreSQL (Compose/prod) / SQLite (test nhanh)

FaceEmbedder port ◀── app/ml/insightface_embedder.py (buffalo_s, CPU)
```

Trách nhiệm chính:

- API xác thực request, đọc upload, gọi Service và chuyển domain error sang HTTP.
- Service chứa matching, role/ownership và use case; không import FastAPI, SQLAlchemy, ORM hay
  Pydantic schema. `import-linter` cưỡng chế ranh giới này.
- Repository là nơi duy nhất chuyển ORM ↔ domain. Session/transaction theo request; Repository
  `flush()`, dependency session commit/rollback.
- Alembic là nguồn schema duy nhất. Compose chạy một service `migrate` trước app, không dùng
  `Base.metadata.create_all()`.

Đọc sâu hơn tại [kiến trúc](docs/architecture.md), [ERD](docs/erd.md) và [ADR](docs/adr/).

## 3. API và quyền truy cập

Sau khi chạy stack:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

Nếu đổi `APP_PORT`, thay `8000` trong các URL bằng giá trị đó.

| Method | Path | Quyền |
|---|---|---|
| GET | `/health` | Công khai |
| POST | `/api/v1/auth/login` | Công khai; OAuth2 form, `username` chứa email |
| GET | `/api/v1/auth/me` | User đã đăng nhập |
| POST | `/api/v1/users` | Admin |
| GET | `/api/v1/users` | Admin |
| GET | `/api/v1/users/{id}` | Admin hoặc chính user |
| DELETE | `/api/v1/users/{id}` | Admin |
| POST | `/api/v1/face-profiles` | User đã đăng nhập; profile luôn thuộc current user |
| GET | `/api/v1/face-profiles` | Admin xem/lọc tất cả; user chỉ thấy của mình |
| DELETE | `/api/v1/face-profiles/{id}` | Admin hoặc chủ profile |
| POST | `/api/v1/checkins` | Công khai; nhận JPEG/PNG multipart field `image` |
| GET | `/api/v1/checkins` | Admin xem/lọc tất cả; user chỉ thấy lịch sử của mình |
| GET | `/api/v1/checkins/{id}` | Admin hoặc user của record |
| DELETE | `/api/v1/checkins/{id}` | Admin |

Trong Swagger, chọn **Authorize**, nhập email vào `username` và mật khẩu vào `password`. Lệnh tương
đương (chỉ chạy thành công sau khi đã có user hợp lệ):

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=admin.sample@example.test' \
  --data-urlencode 'password=<MAT_KHAU_DO_BAN_CUNG_CAP>'
```

## 4. Chạy từ máy sạch bằng Docker Compose

### Yêu cầu

- Git.
- Docker Engine/Desktop có Docker Compose v2 (`docker compose version`).
- Tối thiểu vài GB dung lượng trống; dependency ML làm image lớn hơn web service thông thường.
- Không cần cài Python, PostgreSQL hay Redis trên host.

### Clone và cấu hình

```bash
git clone https://github.com/thanhphu25/face-checkin-service.git
cd face-checkin-service
git switch week5
cp .env.example .env
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Điền kết quả lệnh cuối vào `JWT_SECRET` trong `.env`, rồi đổi `POSTGRES_PASSWORD`. Không commit
`.env`. Nếu host đang dùng các cổng mặc định, đổi `APP_PORT`, `POSTGRES_PORT` hoặc `REDIS_PORT`.

### Build, migration và khởi động

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose ps -a
```

`up` chờ PostgreSQL healthy, chạy đúng một container `migrate` với `alembic upgrade head`, rồi mới
khởi động app. `migrate` kết thúc với exit code 0 là trạng thái đúng. Redis khởi động độc lập và app
không phụ thuộc Redis trong Pha 1.

Kiểm tra và xem log:

```bash
curl http://localhost:8000/health
curl -fsS -o /dev/null http://localhost:8000/docs
docker compose logs migrate
docker compose logs --tail=100 app postgres redis
```

Sau khi sửa migration, có thể chạy idempotent rồi restart app:

```bash
docker compose run --rm migrate
docker compose restart app
```

### Seed dữ liệu mẫu

Stack vừa dựng có schema nhưng chưa có tài khoản nào. `scripts/seed.py` tạo admin mẫu, user mẫu, một
face profile thật và ba bản ghi lịch sử (`success`, `unmatched`, `no_face`). Script idempotent: chạy
lại không nhân đôi dữ liệu.

Seed chạy từ môi trường dev trên host, không chạy trong container: ảnh khuôn mặt mẫu lấy từ package
InsightFace đã cài, còn runtime image cố ý loại bỏ `scripts/` và thư mục ảnh đó. Compose đã publish
cổng PostgreSQL nên host kết nối thẳng vào database của stack:

```bash
uv sync --python 3.12 --frozen --extra dev
export SEED_ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export SEED_USER_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
DATABASE_URL="postgresql+psycopg://app:<POSTGRES_PASSWORD>@localhost:5432/facecheckin" \
JWT_SECRET=<JWT_SECRET trong .env> \
  uv run python -m scripts.seed
```

Ghi lại hai mật khẩu vừa sinh ở nơi an toàn — chúng chỉ tồn tại trong shell của bạn, repo không lưu.
Thêm `--skip-face-profile` nếu chỉ cần tài khoản và không muốn tải model embedding; khi đó check-in
sẽ trả `unmatched` vì chưa có profile nào.

### Dừng và dọn đúng phạm vi

Giữ dữ liệu PostgreSQL/model cache cho lần chạy sau:

```bash
docker compose down
```

Xóa cả dữ liệu **chỉ của project hiện tại**:

```bash
docker compose ls
docker compose -p face-checkin-service down -v
```

Trước `down -v`, luôn đối chiếu project name trong `docker compose ls`; không dùng lệnh xóa volume
toàn cục. Khi kiểm chứng/CI, đặt project riêng, ví dụ
`docker compose -p facecheckin_w5_verify ...`, và chỉ `down -v` đúng tên đó.

## 5. Test, quality gate và benchmark

Chạy ngoài Docker bằng Python 3.12 và [uv](https://docs.astral.sh/uv/):

```bash
uv sync --python 3.12 --frozen --extra dev
JWT_SECRET=local-test-only uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
git diff --check
```

Repository test luôn chạy SQLite. PostgreSQL cases ghi rõ `skipped` nếu không cấp database; để bắt
buộc chạy thật như CI:

```bash
POSTGRES_TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/facecheckin_test' \
REQUIRE_POSTGRES_TESTS=1 \
JWT_SECRET=local-test-only \
uv run pytest -q tests/integration
```

Tên database PostgreSQL test bắt buộc chứa `test`. Hãy tạo database/container riêng, chạy migration
và drop riêng nó; không trỏ lệnh này vào database dev.

Benchmark Pha 1 sẽ được chạy và lưu số liệu trong **Tuần 6**. `scripts/benchmark.py` hiện mới là
harness; README không công bố p50/p95/p99, throughput hay kết luận tối ưu khi chưa có phép đo thật.

## 6. Quyết định thiết kế

- [ADR 0001](docs/adr/0001-database-repository-and-migrations.md): PostgreSQL/SQLite,
  SQLAlchemy Repository, Alembic và transaction.
- [ADR 0002](docs/adr/0002-authentication-and-authorization.md): JWT/OAuth2 dependency,
  Argon2id/PBKDF2 và ownership trong Service.
- [ADR 0003](docs/adr/0003-face-embedding-and-storage.md): `buffalo_s` CPU, embedding
  float32/L2/bytes cùng dimension/model name.
- [ADR 0004](docs/adr/0004-phase-1-infrastructure-boundary.md): chưa dùng Redis cache,
  pgvector/FAISS hay async DB trong Pha 1.

## 7. Biến môi trường và tài khoản mẫu

| Biến | Bắt buộc / mặc định | Mục đích |
|---|---|---|
| `DATABASE_URL` | SQLite local mặc định; Compose tự tạo URL PostgreSQL | SQLAlchemy connection URL |
| `POSTGRES_DB` | `facecheckin` | Database Compose |
| `POSTGRES_USER` | `app` | User PostgreSQL Compose |
| `POSTGRES_PASSWORD` | Bắt buộc với Compose | Password PostgreSQL; dùng giá trị riêng |
| `POSTGRES_PORT` | `5432` | Cổng PostgreSQL trên host |
| `JWT_SECRET` | Bắt buộc | Secret ký JWT; phải sinh ngẫu nhiên |
| `JWT_ALGORITHM` | `HS256` | Thuật toán JWT được cho phép |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Tuổi access token |
| `SIMILARITY_THRESHOLD` | `0.40` | Ngưỡng cosine tại thời điểm check-in |
| `EMBEDDING_MODEL` | `buffalo_s` | Model ghi cùng face profile |
| `MAX_UPLOAD_MB` | `5` | Giới hạn JPEG/PNG trước inference |
| `LOG_LEVEL` | `INFO` | Mức log app |
| `APP_PORT` | `8000` | Cổng HTTP trên host |
| `REDIS_PORT` | `6379` | Cổng Redis dự phòng trên host |
| `APP_IMAGE` | `face-checkin-service:local` | Tên/tag image do Compose build |

`scripts/seed.py` tạo đúng hai tài khoản dưới đây. Email là cố định và nằm trong repo; mật khẩu do
người chạy cung cấp qua biến môi trường, tối thiểu 12 ký tự, và không bao giờ được commit.

| Tên | Email | Role | Mật khẩu |
|---|---|---|---|
| Admin mẫu | `admin.sample@example.test` | `admin` | `SEED_ADMIN_PASSWORD`, người chạy tự sinh |
| User mẫu | `user.sample@example.test` | `user` | `SEED_USER_PASSWORD`, người chạy tự sinh |

Không commit password, JWT, token, ảnh mặt, `.env`, database, model cache hay file ONNX tải về.

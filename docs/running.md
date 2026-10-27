# Hướng dẫn vận hành Face Check-in Service

Backend điểm danh bằng khuôn mặt dùng FastAPI, SQLAlchemy/Alembic, PostgreSQL và InsightFace. Tài
liệu này dành cho người nhận project mà không cần hỏi lại tác giả.

Trạng thái hiện tại: Pha 1 đã có Repository, API, JWT/RBAC, image Docker, Compose, integration test,
seed dữ liệu mẫu tái lập và benchmark baseline trên Kaggle CPU. Số liệu và giới hạn được ghi
trong [báo cáo baseline](benchmark-phase1.md).

Yêu cầu gốc tại [docs/2026.md](2026.md). Tài liệu hiện tại mô tả bản Pha 1 và các hướng cải
tiến Pha 2; chưa có kết quả đo trước/sau cho một cải tiến đã triển khai.

## 1. Nghiệp vụ và phạm vi

Một user có thể đăng ký nhiều hồ sơ khuôn mặt. Khi một ảnh được gửi tới máy chấm công, hệ thống sinh
embedding, so khớp với các profile cùng model/dimension và ghi lại kết quả `success`, `unmatched`
hoặc `no_face`. Ảnh hỏng, nhiều mặt hoặc lỗi sinh embedding bị từ chối và chưa tạo record.

Admin tạo/xóa tài khoản và quản lý dữ liệu toàn hệ thống. User đăng nhập, đăng ký hồ sơ mặt và
xem dữ liệu của mình. Thiết bị điểm danh gửi ảnh tới API công khai để xác định người tương ứng.
Mỗi request là một sự kiện; chưa có quản lý ca làm, tính công, check-out hay chống điểm danh trùng.

| Pha | Trong phạm vi | Ngoài phạm vi hiện tại |
|---|---|---|
| Pha 1 | CRUD `User`/`FaceProfile`/`CheckInRecord`, InsightFace CPU, JWT/RBAC, migration, Docker/Compose và baseline trên Kaggle CPU | refresh token, liveness, cache, async DB, ANN index |
| Pha 2 | Chỉ chọn 2–3 cải tiến sau khi đo lại baseline | Không mặc định Redis cache, pgvector/FAISS hay multi-worker trước khi có số liệu |

Compose Pha 1 chỉ chạy `app`, `migrate` và `postgres`; không dựng hạ tầng dự phòng.
Các vấn đề chính, bằng chứng và cách đánh giá cải tiến được tổng hợp tại
[đề xuất Pha 2](phase-2-improvements.md).

## 2. Kiến trúc

```text
Client / Swagger
       | HTTP + JSON/multipart, OAuth2 bearer
       v
API layer             app/api, app/schemas
       | gọi use case, ánh xạ lỗi/DTO
       v
Service layer         app/services — Python thuần
       | chỉ phụ thuộc domain port
       v
Repository ports      app/domain
       ^
       | implements + ORM<->domain mapping
SQLAlchemy adapters   app/repositories, app/models
       |
       v
PostgreSQL (Compose/prod) / SQLite (test nhanh)

FaceEmbedder port <-- app/ml/insightface_embedder.py (buffalo_s, CPU)
```

Trách nhiệm chính:

- `AuthenticationMiddleware` xác minh Bearer JWT và tải user hiện hành một lần/request.
  Dependency lấy user từ `request.user`, kiểm tra quyền và khai báo OAuth2 cho Swagger.
- API đọc upload, gọi Service và chuyển domain error sang HTTP.
- Service chứa matching, role/ownership và use case; không import FastAPI, SQLAlchemy, ORM hay
  Pydantic schema. `import-linter` cưỡng chế ranh giới này.
- Repository là nơi duy nhất chuyển ORM <-> domain. Middleware đóng session đọc user trước khi
  gọi endpoint; session nghiệp vụ theo request, Repository `flush()`, dependency commit/rollback.
- Alembic là nguồn schema duy nhất. Compose chạy một service `migrate` trước app, không dùng
  `Base.metadata.create_all()`.

Đọc sâu hơn tại [kiến trúc và các quyết định thiết kế](architecture.md) và [ERD](erd.md).

## 3. API và quyền truy cập

Sau khi chạy stack:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>
- [Đặc tả và kịch bản test Swagger](api-spec.md#8-kiểm-thử-thủ-công-trên-swagger)

Bản OpenAPI tĩnh đã commit tại [docs/openapi.json](openapi.json) để đọc contract mà không cần
dựng stack. Sau khi đổi route hoặc schema, xuất lại bằng `uv run python -m scripts.export_openapi`;
test sẽ fail nếu file commit bị lệch so với app.

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
- Kết nối Internet để tải base image, dependency và model khi chưa có cache.
- Build và chạy stack bằng Docker không cần Python hay PostgreSQL trên host. Bước seed và kiểm
  thử ngoài container cần thêm Python 3.12 và uv; cách chuẩn bị nằm ở phần seed bên dưới.

Các khối `bash` dùng với Bash trên Linux/macOS hoặc Git Bash trên Windows. Phần seed có thêm
khối PowerShell tương đương cho Windows.

### Clone và cấu hình

```bash
git clone --branch main https://github.com/thanhphu25/face-checkin-service.git
cd face-checkin-service
cp .env.example .env
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Mã nguồn bàn giao nằm trên nhánh `main` của GitHub. Khi bắt đầu Phase 2, ghi lại commit bằng
`git rev-parse HEAD` để xác định bản gốc dùng cho thay đổi và so sánh benchmark.

Điền kết quả lệnh cuối vào `JWT_SECRET` trong `.env`, rồi đổi `POSTGRES_PASSWORD`. Không commit
`.env`. Nếu host đang dùng các cổng mặc định, đổi `APP_PORT` hoặc `POSTGRES_PORT`.

### Cách đóng gói ứng dụng

`Dockerfile` xây image qua hai giai đoạn, đều dùng Python 3.12 slim:

| Giai đoạn | Công việc và lý do |
|---|---|
| `builder` | Dùng uv cài dependency theo `uv.lock` bằng `uv sync --frozen`, rồi cài ứng dụng vào `.venv`. Dependency được cài trước khi copy code để tận dụng layer cache khi chỉ sửa mã nguồn; cache của uv giúp giảm tải lại package. |
| `runtime` | Copy `.venv`, code ứng dụng và migration; cài `libgl1`/`libglib2.0-0` cho xử lý ảnh. Loại ảnh mẫu và dữ liệu phụ không cần khi chạy để giảm kích thước; chạy bằng user `app` UID 10001, khởi động Uvicorn ở cổng 8000 với một worker. |

`.dockerignore` loại `.env`, database local, model cache và các thư mục không cần khỏi build
context. Runtime image chứa thành phần phục vụ API và migration; seed/test chạy từ checkout trên
host. Compose đọc `.env` trên host, truyền các biến đã khai báo vào container và tạo `DATABASE_URL`
PostgreSQL riêng; giá trị SQLite trong `.env.example` phục vụ chạy ngoài Compose.

### Build, migration và khởi động

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose ps -a
```

`config --quiet` kiểm tra cấu hình sau khi thay biến môi trường. `build` tạo image dùng chung cho
`app` và `migrate`. `up` chờ PostgreSQL healthy, chạy một container `migrate` với
`alembic upgrade head`, rồi mới khởi động app. `migrate` kết thúc với exit code 0 là trạng thái đúng.

Các container kết nối database qua hostname `postgres:5432` trong mạng Compose. Client trên host
gọi API qua `localhost:APP_PORT`; công cụ seed trên host kết nối DB qua `localhost:POSTGRES_PORT`.

| Volume | Điểm mount trong container | Dữ liệu được giữ |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Tài khoản, hồ sơ embedding, lịch sử và phiên bản migration |
| `insightface_models` | `/home/app/.insightface` | Model ONNX đã tải; mặc định ở `models/buffalo_s/` |

Rebuild hoặc tạo lại container vẫn dùng các volume này. `docker compose down` giữ volume;
`down -v` xóa cả dữ liệu DB và model cache của project được chọn.

Kiểm tra và xem log:

```bash
curl http://localhost:8000/health
curl -fsS -o /dev/null http://localhost:8000/docs
docker compose logs migrate
docker compose logs --tail=100 app postgres
```

Khi cập nhật code hoặc thêm migration, build lại image để container nhận được file mới:

```bash
docker compose build
docker compose run --rm migrate
docker compose up -d --wait app
```

### Chuẩn bị model trước khi thử API

Model chưa được tải sẵn trong image. Lần đầu dependency `get_embedder` được gọi, InsightFace tải
model từ GitHub nếu chưa có cache, rồi ONNX Runtime nạp model vào RAM. Dependency này hiện dùng
chung cho các route face-profile/check-in, kể cả GET/DELETE. Vì vậy request đầu có thể chậm hoặc
lỗi nếu mạng tải model hay quyền ghi cache có vấn đề.

Có thể tải và kiểm tra model ngay sau khi stack chạy:

```bash
docker compose exec app python -c "from app.api.deps import get_embedder; get_embedder(); print('Model ready')"
```

Lệnh này chạy trong tiến trình riêng, chuẩn bị file trong volume; request đầu của Uvicorn vẫn
cần nạp model vào RAM. Sau đó model được tái sử dụng trong từng tiến trình. `/health` chỉ kiểm
tra handler HTTP, nên `up --wait` thành công chưa xác nhận model đã sẵn sàng; tiếp tục thử đăng
ký mặt/điểm danh theo [kịch bản Swagger](api-spec.md#8-kiểm-thử-thủ-công-trên-swagger).

### Seed dữ liệu mẫu

Stack vừa dựng có schema nhưng chưa có tài khoản nào. `scripts/seed.py` tạo admin mẫu, user mẫu, một
face profile thật và ba bản ghi lịch sử (`success`, `unmatched`, `no_face`). Script idempotent: chạy
lại không nhân đôi dữ liệu.

Seed chạy từ môi trường dev trên host, không chạy trong container: ảnh khuôn mặt mẫu lấy từ package
InsightFace đã cài, còn runtime image cố ý loại bỏ `scripts/` và thư mục ảnh đó. Compose đã publish
cổng PostgreSQL nên host kết nối thẳng vào database của stack.

Trên host, cài Python 3.12 và đưa lệnh `python` vào PATH. Nếu chưa có uv, cài bằng pip của Python
đó, rồi chuẩn bị dependency từ thư mục gốc repo:

```bash
python --version  # cần Python 3.12.x
python -m pip install uv
uv --version
uv sync --python 3.12 --frozen --extra dev
```

Script đọc `JWT_SECRET` từ `.env`. Thay `<POSTGRES_PASSWORD>` trong URL bên dưới bằng mật khẩu đã
đặt; nếu đổi user, tên DB hoặc cổng trong Compose thì sửa URL tương ứng. `--database-url` trỏ
seed vào PostgreSQL của stack, thay cho SQLite mặc định trong `.env`. Mật khẩu có ký tự đặc biệt
trong URL cần percent-encode.

Chạy **một** trong hai khối sau. Với Bash:

```bash
export SEED_ADMIN_PASSWORD="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export SEED_USER_PASSWORD="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(24))')"
seed_database_url="postgresql+psycopg://app:<POSTGRES_PASSWORD>@localhost:5432/facecheckin"
uv run python -m scripts.seed --database-url "$seed_database_url"
```

Với PowerShell:

```powershell
$env:SEED_ADMIN_PASSWORD = uv run python -c "import secrets; print(secrets.token_urlsafe(24))"
$env:SEED_USER_PASSWORD = uv run python -c "import secrets; print(secrets.token_urlsafe(24))"
$seedDatabaseUrl = "postgresql+psycopg://app:<POSTGRES_PASSWORD>@localhost:5432/facecheckin"
uv run python -m scripts.seed --database-url $seedDatabaseUrl
```

Ghi lại hai mật khẩu vừa sinh ở nơi an toàn — chúng chỉ tồn tại trong shell của bạn, repo không lưu.
Chạy lại seed giữ nguyên tài khoản và mật khẩu đã có. Model của seed nằm trong `~/.insightface`
của user trên host, tách khỏi volume model của app; chuẩn bị model trong container chưa tạo cache
cho host và ngược lại.

Thêm `--skip-face-profile` vào lệnh seed nếu chỉ cần tài khoản và lịch sử mẫu, rồi đăng ký mặt qua
Swagger. Nếu DB chưa có profile, điểm danh bằng ảnh hợp lệ có một mặt sẽ trả `unmatched` sau khi
model phía API đã nạp thành công.

### Xử lý lỗi khi dựng lần đầu

| Biểu hiện | Cách kiểm tra |
|---|---|
| Compose báo thiếu `JWT_SECRET`/`POSTGRES_PASSWORD` | Điền `.env` ở thư mục gốc và chạy lại `docker compose config --quiet`. |
| App chưa khởi động, `migrate` có exit code khác 0 | Xem `docker compose logs migrate postgres`; xử lý kết nối/schema trước khi chạy lại migration. |
| Cổng đã được sử dụng | Đổi `APP_PORT`/`POSTGRES_PORT`, tạo lại container và dùng cổng mới trong URL API/seed. |
| Health trả 200 nhưng route khuôn mặt chậm hoặc lỗi | Xem `docker compose logs --tail=100 app`, chạy lệnh kiểm tra model ở trên; kiểm tra Internet và quyền ghi volume model. |
| Seed không kết nối DB | Kiểm tra PostgreSQL đang chạy, mật khẩu và cổng host trong `--database-url`; hostname `postgres` chỉ dùng giữa các container. |

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
`docker compose -p facecheckin_verify ...`, và chỉ `down -v` đúng tên đó.

## 5. Test, quality gate và benchmark

Chạy ngoài Docker bằng Python 3.12 và [uv](https://docs.astral.sh/uv/), dùng môi trường host đã
chuẩn bị ở phần seed:

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

### Baseline Pha 1

Đo ngày 2026-10-27 trên Kaggle CPU 4 core, commit `3503b24`, Uvicorn một worker, ngoài Compose.
Notebook: [Face Check-in Benchmark trên Kaggle](https://www.kaggle.com/code/tphu25/face-checkin-benchmark).
Bộ hiện hành có thời điểm metadata 10:53:08 (SQLite) và 10:55:26 (PostgreSQL), giờ Việt Nam.
Cả 8.480 request ở 16 mức đo trên SQLite/PostgreSQL đều không lỗi HTTP. PostgreSQL check-in đạt
6,424–10,140 req/s khi concurrency tăng từ 1 lên 8; p95 tăng từ 167,79 lên 874,75 ms.
Baseline chỉ có một face profile, một lượt mỗi cấu hình; chưa đại diện cho dữ liệu lớn hoặc
độ chính xác nhận diện.

[Báo cáo benchmark](benchmark-phase1.md) chứa bảng số liệu, giới hạn, các cell Kaggle và điều
kiện so sánh trước/sau. Số liệu gốc nằm tại [docs/benchmark/](benchmark/).

## 6. Thiết kế và tài liệu theo đề bài

[Kiến trúc và quyết định thiết kế](architecture.md) có sơ đồ tổng quát, các luồng nghiệp vụ
và lý do lựa chọn database, JWT, embedding, hạ tầng và phương pháp benchmark.

| Nội dung theo yêu cầu | Tài liệu / bằng chứng |
|---|---|
| Đề bài hai pha | [docs/2026.md](2026.md) |
| Phân tầng API, nghiệp vụ, dữ liệu; Repository/ORM | [Kiến trúc](architecture.md), [ERD](erd.md), import-linter và integration test |
| REST JSON, POST/GET/DELETE; đăng nhập và GET/POST có xác thực | Danh mục API ở trên, [API spec và test Swagger](api-spec.md), [OpenAPI](openapi.json) |
| Xác thực tập trung qua middleware | [Quyết định auth](architecture.md#auth), test middleware/RBAC |
| Đóng gói và dựng Docker | Mục 4, Dockerfile/Compose và CI |
| Kiểm thử tải trên Kaggle CPU | [Notebook Kaggle](https://www.kaggle.com/code/tphu25/face-checkin-benchmark), [kết quả và cách tái lập](benchmark-phase1.md), [CSV/metadata](benchmark/) |
| Cải tiến có lý do và đánh giá trước/sau trên cùng phần cứng | [Đánh giá và hướng Pha 2](phase-2-improvements.md); phần kết quả sau cải tiến chưa có |

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
| `APP_PORT` | `8000` | Cổng HTTP trên host |
| `APP_IMAGE` | `face-checkin-service:local` | Tên/tag image do Compose build |
| `SEED_ADMIN_PASSWORD` | Bắt buộc khi tạo admin mẫu lần đầu | Biến môi trường của tiến trình seed trên host, tối thiểu 12 ký tự |
| `SEED_USER_PASSWORD` | Bắt buộc khi tạo user mẫu lần đầu | Biến môi trường của tiến trình seed trên host, tối thiểu 12 ký tự |

`scripts/seed.py` tạo đúng hai tài khoản dưới đây. Email là cố định và nằm trong repo; mật khẩu do
người chạy cung cấp qua biến môi trường, tối thiểu 12 ký tự, và không bao giờ được commit.

| Tên | Email | Role | Mật khẩu |
|---|---|---|---|
| Admin mẫu | `admin.sample@example.test` | `admin` | `SEED_ADMIN_PASSWORD`, người chạy tự sinh |
| User mẫu | `user.sample@example.test` | `user` | `SEED_USER_PASSWORD`, người chạy tự sinh |

Không commit password, JWT, token, ảnh mặt, `.env`, database, model cache hay file ONNX tải về.

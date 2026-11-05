# Hướng dẫn vận hành Face Check-in Service

Runbook dựng, kiểm tra, cập nhật và dọn dẹp stack từ một máy sạch mà không cần hỏi lại tác giả.
Mọi lệnh chạy từ thư mục gốc repo. Khối `bash` dùng cho Linux/macOS hoặc Git Bash trên Windows;
bước seed có thêm khối PowerShell.

Tài liệu này chỉ chứa thao tác. Kiến trúc và lý do thiết kế ở [architecture.md](architecture.md);
endpoint, quyền và mã lỗi ở [api-spec.md](api-spec.md); số liệu baseline ở
[benchmark-phase1.md](benchmark-phase1.md).

## Thứ tự thực hiện

| Bước | Việc cần làm | Dấu hiệu hoàn thành |
|---:|---|---|
| 1 | [Chuẩn bị máy](#yêu-cầu) | `docker compose version` chạy được |
| 2 | [Clone và cấu hình](#clone-và-cấu-hình) | `.env` đã có `JWT_SECRET` và `POSTGRES_PASSWORD` riêng |
| 3 | [Build và khởi động](#build-và-khởi-động) | `migrate` thoát với mã 0, `app` ở trạng thái healthy |
| 4 | [Chuẩn bị model](#chuẩn-bị-model) | Lệnh kiểm tra in ra `Model ready` |
| 5 | [Seed dữ liệu mẫu](#seed-dữ-liệu-mẫu) | Có tài khoản admin/user mẫu và đã lưu mật khẩu |
| 6 | [Kiểm tra sau khi dựng](#kiểm-tra-sau-khi-dựng) | Login trả JWT, kịch bản Swagger cho kết quả đúng |

Dùng khi cần: [cập nhật code hoặc migration](#cập-nhật-code-hoặc-migration),
[xử lý sự cố](#xử-lý-sự-cố), [dừng và dọn dữ liệu](#dừng-và-dọn-dữ-liệu),
[test và quality gate](#test-và-quality-gate), [benchmark](#benchmark),
[tham chiếu cấu hình](#tham-chiếu-cấu-hình).

## Yêu cầu

- Git.
- Docker Engine hoặc Docker Desktop có Docker Compose v2.
- Vài GB dung lượng trống: dependency ML làm image lớn hơn web service thông thường.
- Internet ở lần chạy đầu để tải base image, dependency và model.
- Bước 1–4 không cần Python hay PostgreSQL trên host. Seed, test và benchmark thử cần thêm
  Python 3.12 và uv, cài ở [bước seed](#seed-dữ-liệu-mẫu).

```bash
git --version
docker compose version
```

## Clone và cấu hình

```bash
git clone --branch main https://github.com/thanhphu25/face-checkin-service.git
cd face-checkin-service
git rev-parse HEAD
cp .env.example .env
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Mở `.env` và sửa:

1. `JWT_SECRET`: dán chuỗi do lệnh cuối sinh ra.
2. `POSTGRES_PASSWORD`: đặt mật khẩu riêng. Nên chỉ dùng chữ, số, `-` và `_` để không phải
   percent-encode khi đưa vào URL ở bước seed.
3. Nếu cổng `8000` hoặc `5432` trên host đã bận, đổi `APP_PORT` hoặc `POSTGRES_PORT`. Khi đó thay
   cổng tương ứng trong mọi URL và lệnh bên dưới.

Không commit `.env`. Ghi lại kết quả `git rev-parse HEAD`: đây là commit gốc dùng để đối chiếu khi
so sánh benchmark Phase 2.

`DATABASE_URL` (SQLite) trong `.env` chỉ dùng khi chạy ngoài Compose; Compose tự tạo URL PostgreSQL
cho container. Danh sách biến đầy đủ ở [tham chiếu cấu hình](#biến-môi-trường).

## Build và khởi động

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose ps -a
docker compose logs migrate
```

| Lệnh | Tác dụng |
|---|---|
| `config --quiet` | Kiểm tra cấu hình sau khi thay biến; báo lỗi nếu thiếu `JWT_SECRET` hoặc `POSTGRES_PASSWORD` |
| `build` | Build một image dùng chung cho `app` và `migrate` |
| `up -d --wait` | Chờ `postgres` healthy, chạy `migrate` (`alembic upgrade head`), rồi khởi động `app` và chờ healthcheck |
| `ps -a`, `logs migrate` | Xác nhận trạng thái container và kết quả migration |

**Kết quả đúng:** `postgres` và `app` ở trạng thái `running (healthy)`; `migrate` ở trạng thái
`exited (0)`. Container `migrate` chạy một lần rồi kết thúc là bình thường.

`up --wait` thành công chỉ xác nhận `/health` trả lời, chưa xác nhận model nhận diện đã sẵn sàng.
Làm tiếp bước chuẩn bị model.

## Chuẩn bị model

Image không chứa sẵn model. Lần đầu dependency `get_embedder` được gọi, InsightFace tải model
`buffalo_s` từ GitHub vào volume `insightface_models`, rồi ONNX Runtime nạp model vào RAM. Mọi
route face-profile/check-in, kể cả GET/DELETE, đều kích hoạt bước này, nên request đầu có thể chậm
hoặc lỗi nếu chưa tải trước.

```bash
docker compose exec app python -c "from app.api.deps import get_embedder; get_embedder(); print('Model ready')"
```

**Kết quả đúng:** in ra `Model ready`. Lệnh chạy trong tiến trình riêng nên chỉ tạo cache trong
volume; request đầu tới Uvicorn vẫn mất thêm thời gian nạp model vào RAM, các request sau dùng lại.

## Seed dữ liệu mẫu

Stack vừa dựng có schema nhưng chưa có tài khoản. `scripts/seed.py` tạo:

- admin mẫu và user mẫu (xem [tài khoản mẫu](#tài-khoản-mẫu));
- một face profile từ ảnh mẫu;
- ba bản ghi lịch sử `success`, `unmatched` và `no_face`.

Script idempotent: chạy lại không nhân đôi dữ liệu và giữ nguyên mật khẩu đã có.

Seed chạy trên host, không chạy trong container: ảnh mẫu lấy từ package InsightFace cài trên host,
còn runtime image không chứa `scripts/`. Host kết nối PostgreSQL của stack qua cổng `POSTGRES_PORT`
mà Compose publish.

### 1. Chuẩn bị Python và uv (một lần)

```bash
python --version  # cần Python 3.12.x
python -m pip install uv
uv --version
uv sync --python 3.12 --frozen --extra dev
```

### 2. Chạy seed

Điền bốn giá trị đầu cho khớp với `.env`. Seed tự đọc `JWT_SECRET` từ `.env`; `--database-url` trỏ
seed vào PostgreSQL của stack thay cho SQLite mặc định. Mật khẩu có ký tự đặc biệt cần
percent-encode trong URL. Chạy **một** trong hai khối sau.

Bash:

```bash
pg_user=app                        # POSTGRES_USER
pg_password='<POSTGRES_PASSWORD>'  # POSTGRES_PASSWORD
pg_port=5432                       # POSTGRES_PORT
pg_db=facecheckin                  # POSTGRES_DB
export SEED_ADMIN_PASSWORD="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export SEED_USER_PASSWORD="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(24))')"
uv run python -m scripts.seed \
  --database-url "postgresql+psycopg://${pg_user}:${pg_password}@localhost:${pg_port}/${pg_db}"
echo "admin: $SEED_ADMIN_PASSWORD"
echo "user:  $SEED_USER_PASSWORD"
```

PowerShell:

```powershell
$pgUser = "app"                        # POSTGRES_USER
$pgPassword = "<POSTGRES_PASSWORD>"    # POSTGRES_PASSWORD
$pgPort = 5432                         # POSTGRES_PORT
$pgDb = "facecheckin"                  # POSTGRES_DB
$env:SEED_ADMIN_PASSWORD = uv run python -c "import secrets; print(secrets.token_urlsafe(24))"
$env:SEED_USER_PASSWORD = uv run python -c "import secrets; print(secrets.token_urlsafe(24))"
uv run python -m scripts.seed --database-url "postgresql+psycopg://${pgUser}:${pgPassword}@localhost:${pgPort}/${pgDb}"
"admin: $env:SEED_ADMIN_PASSWORD"
"user:  $env:SEED_USER_PASSWORD"
```

**Lưu hai mật khẩu vừa in ở nơi an toàn.** Chúng chỉ tồn tại trong shell hiện tại, repo không lưu.
Seed yêu cầu mật khẩu tối thiểu 12 ký tự, chặt hơn mức 8 ký tự của API tạo user.

Tùy chọn:

- Thêm `--skip-face-profile` nếu chỉ cần tài khoản và lịch sử mẫu, rồi tự đăng ký mặt qua Swagger.
  Khi DB chưa có profile, check-in bằng ảnh hợp lệ có một mặt sẽ trả `unmatched`.
- Model của seed nằm trong `~/.insightface` trên host, tách khỏi volume model của app. Chuẩn bị model
  ở một bên không tạo cache cho bên kia.

## Kiểm tra sau khi dựng

Chạy trong cùng shell vừa seed để dùng lại biến `SEED_ADMIN_PASSWORD`:

```bash
curl http://localhost:8000/health
curl -fsS -o /dev/null http://localhost:8000/docs && echo "Swagger OK"
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=admin.sample@example.test' \
  --data-urlencode "password=$SEED_ADMIN_PASSWORD"
```

**Kết quả đúng:** health trả `{"status":"ok"}`, dòng thứ hai in `Swagger OK`, login trả JSON có
`access_token` và `"token_type":"bearer"`.

Sau đó mở Swagger UI tại <http://localhost:8000/docs>, bấm **Authorize** (email vào `username`,
mật khẩu vào `password`) và chạy
[kịch bản kiểm thử thủ công](api-spec.md#8-kiểm-thử-thủ-công-trên-swagger).

| Địa chỉ | Nội dung |
|---|---|
| <http://localhost:8000/docs> | Swagger UI |
| <http://localhost:8000/openapi.json> | OpenAPI runtime; bản tĩnh đã commit ở [openapi.json](openapi.json) |
| <http://localhost:8000/health> | Health check, chỉ kiểm tra handler HTTP |

Danh sách endpoint, quyền và mã lỗi nằm trong [api-spec.md](api-spec.md).

## Cập nhật code hoặc migration

Container chỉ nhận code mới sau khi build lại image. Chạy `migrate` trước để áp dụng migration mới
(nếu có), rồi khởi động lại app:

```bash
git pull
docker compose build
docker compose run --rm migrate
docker compose up -d --wait app
```

Khi đổi route hoặc schema API, xuất lại OpenAPI tĩnh và commit cùng thay đổi. Test
`tests/api/test_openapi_export.py` sẽ fail nếu `docs/openapi.json` lệch so với app.

```bash
uv run python -m scripts.export_openapi
```

## Xử lý sự cố

| Biểu hiện | Cách kiểm tra và xử lý |
|---|---|
| Compose báo thiếu `JWT_SECRET`/`POSTGRES_PASSWORD` | Điền `.env` ở thư mục gốc, chạy lại `docker compose config --quiet`. |
| App không khởi động, `migrate` thoát với mã khác 0 | Xem `docker compose logs migrate postgres`; xử lý lỗi kết nối/schema rồi chạy lại `docker compose run --rm migrate`. |
| Cổng đã được sử dụng | Đổi `APP_PORT`/`POSTGRES_PORT` trong `.env`, chạy `docker compose up -d --wait`, dùng cổng mới trong URL API và URL seed. |
| Health trả 200 nhưng route khuôn mặt chậm hoặc lỗi | Chạy lệnh [chuẩn bị model](#chuẩn-bị-model), xem `docker compose logs --tail=100 app`; kiểm tra Internet và quyền ghi volume model. |
| Seed không kết nối được DB | Kiểm tra PostgreSQL đang chạy (`docker compose ps`), mật khẩu và cổng host trong `--database-url`. Hostname `postgres` chỉ dùng giữa các container, từ host phải dùng `localhost`. |
| Seed báo mật khẩu quá ngắn | `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD` chưa được đặt hoặc ngắn hơn 12 ký tự trong shell hiện tại. |
| Login trả `401` | Sai email/mật khẩu, hoặc đang dùng shell khác nên biến mật khẩu seed rỗng. |

Xem log:

```bash
docker compose logs migrate
docker compose logs --tail=100 app postgres
```

## Dừng và dọn dữ liệu

Dừng stack, giữ dữ liệu PostgreSQL và model cache cho lần chạy sau:

```bash
docker compose down
```

Xóa cả dữ liệu, **chỉ của project hiện tại**:

```bash
docker compose ls
docker compose -p face-checkin-service down -v
```

Trước khi chạy `down -v`, luôn đối chiếu tên project trong `docker compose ls`; không dùng lệnh xóa
volume toàn cục. Khi kiểm chứng hoặc chạy CI, đặt project riêng, ví dụ
`docker compose -p facecheckin_verify ...`, và chỉ `down -v` đúng tên đó.

## Test và quality gate

Chạy ngoài Docker bằng môi trường Python/uv đã chuẩn bị ở [bước seed](#1-chuẩn-bị-python-và-uv-một-lần):

```bash
uv sync --python 3.12 --frozen --extra dev
JWT_SECRET=local-test-only uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
git diff --check
```

Repository test luôn chạy trên SQLite. Các case PostgreSQL được báo `skipped` nếu không cấp
database; để bắt buộc chạy thật như CI:

```bash
POSTGRES_TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/facecheckin_test' \
REQUIRE_POSTGRES_TESTS=1 \
JWT_SECRET=local-test-only \
uv run pytest -q tests/integration
```

Tên database test bắt buộc chứa `test`. Tạo database hoặc container riêng, chạy migration và drop
riêng nó; không trỏ lệnh này vào database dev.

## Benchmark

| Mục đích | Hướng dẫn |
|---|---|
| Thử harness trên máy thường (~1 phút, không dùng làm baseline) | [Kiểm tra harness không cần Kaggle](benchmark-phase1.md#kiểm-tra-harness-không-cần-kaggle) |
| Chạy lại baseline trên Kaggle CPU | [Chạy lại trên Kaggle CPU](benchmark-phase1.md#7-chạy-lại-trên-kaggle-cpu) |
| So sánh trước/sau cho Phase 2 | [Đọc kết quả và so sánh trước/sau](benchmark-phase1.md#8-đọc-kết-quả-và-so-sánh-trướcsau) |

## Tham chiếu cấu hình

### Biến môi trường

| Biến | Bắt buộc / mặc định | Mục đích |
|---|---|---|
| `DATABASE_URL` | SQLite local; Compose tự tạo URL PostgreSQL | SQLAlchemy connection URL khi chạy ngoài Compose |
| `POSTGRES_DB` | `facecheckin` | Tên database Compose |
| `POSTGRES_USER` | `app` | User PostgreSQL Compose |
| `POSTGRES_PASSWORD` | Bắt buộc với Compose | Mật khẩu PostgreSQL; dùng giá trị riêng |
| `POSTGRES_PORT` | `5432` | Cổng PostgreSQL publish ra host |
| `JWT_SECRET` | Bắt buộc | Secret ký JWT; phải sinh ngẫu nhiên |
| `JWT_ALGORITHM` | `HS256` | Thuật toán JWT được chấp nhận |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Thời hạn access token |
| `SIMILARITY_THRESHOLD` | `0.40` | Ngưỡng cosine lúc check-in, được lưu cùng mỗi record |
| `EMBEDDING_MODEL` | `buffalo_s` | Model ghi cùng face profile |
| `MAX_UPLOAD_MB` | `5` | Dung lượng tối đa ảnh JPEG/PNG trước inference |
| `APP_PORT` | `8000` | Cổng HTTP publish ra host |
| `APP_IMAGE` | `face-checkin-service:local` | Tên/tag image do Compose build |
| `SEED_ADMIN_PASSWORD` | Bắt buộc khi tạo admin mẫu lần đầu | Biến của tiến trình seed trên host, tối thiểu 12 ký tự |
| `SEED_USER_PASSWORD` | Bắt buộc khi tạo user mẫu lần đầu | Biến của tiến trình seed trên host, tối thiểu 12 ký tự |

### Service, cổng và volume

| Service | Vai trò | Truy cập |
|---|---|---|
| `postgres` | PostgreSQL 16 | Container: `postgres:5432`; host: `localhost:POSTGRES_PORT` |
| `migrate` | Chạy `alembic upgrade head` một lần rồi thoát | Không publish cổng |
| `app` | FastAPI/Uvicorn một worker, user `app` UID 10001 | Host: `localhost:APP_PORT` |

| Volume | Điểm mount trong container | Dữ liệu được giữ |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Tài khoản, hồ sơ embedding, lịch sử và phiên bản migration |
| `insightface_models` | `/home/app/.insightface` | Model ONNX đã tải, mặc định ở `models/buffalo_s/` |

Rebuild hoặc tạo lại container vẫn dùng các volume này. `docker compose down` giữ volume;
`down -v` xóa cả dữ liệu DB và model cache của project được chọn. Cách đóng gói image được giải
thích ở [quyết định Infrastructure](architecture.md#infrastructure).

### Tài khoản mẫu

`scripts/seed.py` tạo đúng hai tài khoản. Email cố định trong repo; mật khẩu do người chạy cung cấp
qua biến môi trường và không bao giờ được commit.

| Tên | Email | Role | Mật khẩu |
|---|---|---|---|
| Admin mẫu | `admin.sample@example.test` | `admin` | `SEED_ADMIN_PASSWORD` |
| User mẫu | `user.sample@example.test` | `user` | `SEED_USER_PASSWORD` |

Không commit password, JWT, token, ảnh mặt, `.env`, database, model cache hay file ONNX tải về.

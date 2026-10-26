# Face Check-in Service — Báo cáo Phase 1

Backend điểm danh bằng khuôn mặt, xây dựng theo [đề bài hai pha](docs/2026.md).
README này trình bày bài toán, nghiệp vụ, kiến trúc, công nghệ, API và các vấn đề làm cơ sở cho
Phase 2. [Hướng dẫn vận hành](docs/running.md) chứa chi tiết cài đặt, cấu hình, seed và kiểm thử.

## 1. Đặc tả bài toán, mục tiêu và phạm vi

**Bối cảnh:** một đơn vị cần ghi nhận sự có mặt của người đã đăng ký thông qua ảnh từ thiết bị
điểm danh. Thiết bị gửi ảnh, backend xác định danh tính và lưu thời điểm, kết quả để tra cứu.
Đây là dịch vụ nhận diện và ghi nhận sự kiện; chưa xử lý ca làm, check-out hoặc tính công/lương.

**Đầu vào:** tài khoản, thông tin người dùng và ảnh JPEG/PNG chứa một khuôn mặt.
**Đầu ra:** hồ sơ đã đăng ký; kết quả điểm danh gồm danh tính nếu khớp, thời điểm UTC, điểm tương
đồng, ngưỡng và trạng thái; lịch sử được giới hạn theo quyền truy cập.

| Tác nhân | Chức năng và giới hạn quyền |
|---|---|
| Quản trị viên (`admin`) | Tạo/xóa tài khoản; xem toàn bộ user, hồ sơ mặt, lịch sử; xóa hồ sơ và bản ghi điểm danh |
| Người dùng (`user`) | Đăng nhập; đăng ký/xóa hồ sơ mặt của mình; xem thông tin và lịch sử cá nhân |
| Thiết bị điểm danh | Gửi ảnh đến API công khai; không gửi trước ID người cần nhận diện |

**Mục tiêu Phase 1:** có luồng nghiệp vụ hoàn chỉnh, kiến trúc phân tầng, đăng nhập/phân quyền,
API có đặc tả, triển khai bằng Docker và baseline tải trên Kaggle CPU. Các yêu cầu này được
hiện thực bằng REST POST/GET/DELETE, middleware JWT, Service độc lập web/DB và Repository dùng ORM.

**Cách tạo cơ sở cho Phase 2:** chọn thiết kế ban đầu đơn giản: một dịch vụ, inference CPU trong
cùng ứng dụng, tải toàn bộ hồ sơ để so khớp, chưa cache/chưa vector index, chưa chống gửi lặp.
Khi tăng tải, dữ liệu hoặc yêu cầu triển khai, những lựa chọn này tạo bài toán cải tiến có thể
kiểm chứng. Phase 2 chọn 2–3 vấn đề, thay đổi có lý do và đo trước/sau; không bắt buộc bổ sung
mọi công nghệ. Các chức năng ca làm, giao diện camera và tính lương nằm ngoài phạm vi hiện tại.

## 2. Đặc tả nghiệp vụ và dữ liệu

**Luồng 1 — Cấp tài khoản và đăng nhập.** Admin tạo user với email, mật khẩu, họ tên và vai trò.
Email được chuẩn hóa và phải duy nhất; mật khẩu được băm. User đăng nhập bằng email/mật khẩu
để nhận JWT. Các request được bảo vệ gửi `Authorization: Bearer <token>`; middleware kiểm tra
token và tải user hiện hành, sau đó Service kiểm tra vai trò/quyền sở hữu tài nguyên.

**Luồng 2 — Đăng ký khuôn mặt.** User đã đăng nhập gửi ảnh có đúng một mặt. Backend kiểm tra
định dạng/dung lượng, phát hiện mặt và sinh embedding — vector số mô tả đặc trưng khuôn mặt.
Vector được chuẩn hóa L2 và lưu với model/số chiều, luôn thuộc tài khoản đang đăng nhập.
Một user có thể đăng ký nhiều hồ sơ; hiện chưa giới hạn số hồ sơ hay phát hiện đăng ký trùng.

**Luồng 3 — Điểm danh và tra cứu.** Thiết bị gửi ảnh đến `POST /api/v1/checkins`. Backend sinh
vector ảnh mới, tải hồ sơ, lọc cùng model/số chiều, tính cosine similarity và chọn điểm cao nhất.
Nếu điểm ≥ ngưỡng cấu hình (mặc định `0.40`), ghi nhận người khớp. Ví dụ, điểm `0.62` đạt ngưỡng
`0.40`, còn `0.32` bị từ chối. Đây là điểm tương đồng, không phải xác suất nhận diện đúng.

| Tình huống | HTTP / trạng thái | Quy tắc lưu |
|---|---|---|
| Nhận diện đạt ngưỡng | `201` / `success` | Lưu user/profile khớp, thời điểm, điểm và ngưỡng |
| Không có hồ sơ phù hợp hoặc dưới ngưỡng | `404` / `unmatched` | Vẫn lưu lịch sử; lỗi trả `record_id` và `best_score` nếu có |
| Ảnh giải mã được nhưng không có mặt | `422` / `no_face` | Vẫn lưu lịch sử; lỗi trả `record_id` |
| Ảnh rỗng/hỏng, sai MIME hoặc quá dung lượng | `400` | Không tạo lịch sử |
| Nhiều mặt hoặc lỗi sinh embedding | `422` | Không tạo lịch sử |

Không có mặt khi **đăng ký** bị từ chối và không tạo hồ sơ/lịch sử điểm danh. Mỗi request
điểm danh thành công là một sự kiện mới, kể cả gửi lại cùng ảnh. User chỉ xem dữ liệu của mình;
admin xem được cả các lần `unmatched`/`no_face`.

| Thực thể | Dữ liệu chính và quan hệ |
|---|---|
| `User` | ID, email duy nhất, password hash, họ tên, vai trò, ngày tạo; một user có nhiều hồ sơ/lượt điểm danh |
| `FaceProfile` | ID, user sở hữu, embedding nhị phân `float32`, số chiều, tên model, ngày tạo |
| `CheckInRecord` | ID, thời gian UTC, trạng thái, điểm, ngưỡng tại lúc xử lý, user/profile khớp có thể null |

Không lưu ảnh gốc; API không trả embedding hoặc password hash. Xóa user sẽ xóa hồ sơ mặt;
lịch sử vẫn còn, liên kết user/profile đã xóa chuyển thành `null`. Xem [ERD và ràng buộc](docs/erd.md).

## 3. Framework, tech stack và các yếu tố kỹ thuật

| Thành phần | Công nghệ | Vai trò/lý do sử dụng |
|---|---|---|
| Ngôn ngữ/runtime | Python 3.12, uv và `uv.lock` | Dùng chung hệ sinh thái web/ML; khóa dependency để tái lập môi trường |
| Web/API | FastAPI, Uvicorn, Pydantic | Routing, kiểm tra dữ liệu, dependency injection; sinh OpenAPI và Swagger UI |
| Dữ liệu | PostgreSQL 16 trong Compose, SQLAlchemy 2, psycopg | DB quan hệ có constraint/index; ORM hiện thực Repository; SQLite cho local/test nhanh |
| Migration | Alembic | Quản lý phiên bản schema; chạy migration trước ứng dụng |
| Nhận diện | InsightFace `buffalo_s`, ONNX Runtime CPU | Phát hiện mặt, sinh embedding bằng model có sẵn; không huấn luyện model riêng |
| Xử lý ảnh/vector | OpenCV, NumPy | Giải mã ảnh; chuẩn hóa vector và tính cosine bằng phép nhân ma trận |
| Bảo mật | PyJWT, OAuth2 Bearer, Argon2id | JWT cho request đã đăng nhập; băm mật khẩu; phân quyền admin/user và ownership |
| Đóng gói/chất lượng | Docker/Compose, pytest, Ruff, import-linter, GitHub Actions | Dựng môi trường; kiểm thử; kiểm tra style, ranh giới tầng và quy trình CI |

JWT mặc định dùng `HS256`, hạn 30 phút; secret lấy từ môi trường. Ảnh upload mặc định tối đa
5 MB, chỉ nhận JPEG/PNG. Embedding thường 512 chiều, lưu `BYTEA` trên PostgreSQL (`BLOB` trên
SQLite); DB chưa thực hiện tìm kiếm vector. Model được giữ trong bộ nhớ mỗi tiến trình sau
khởi tạo, nhưng kết quả inference và ma trận hồ sơ chưa có cache.

SQLAlchemy và nghiệp vụ xử lý đồng bộ. Repository chỉ `flush`, dependency tại API quản lý
commit/rollback. Hiện dependency commit cả lỗi Domain để lưu audit thất bại; lỗi hệ thống
rollback. Đây là chính sách đơn giản cần đánh giá lại nếu một use case có nhiều bước ghi.
Compose có `postgres`, `migrate`, `app`; PostgreSQL healthy → migration thành công → mở app.

## 4. Kiến trúc và tổ chức mã nguồn

```text
Client / thiết bị / Swagger UI
             ↓ HTTP + JSON / multipart
Middleware xác thực JWT → API → Service
                                  ├→ Repository port → SQLAlchemy adapter → PostgreSQL
                                  └→ FaceEmbedder port → InsightFace / ONNX CPU
Domain: entity, lỗi nghiệp vụ và các port dùng chung.
```

Đây là **một dịch vụ phân tầng**. API tiếp nhận HTTP và ánh xạ lỗi; Service điều phối use case,
phân quyền và matching; Repository truy cập dữ liệu, chuyển ORM ↔ domain. Service chỉ biết
hợp đồng Domain, không import FastAPI, SQLAlchemy, ORM hay schema API. Dependency ở API lắp
adapter vào Service; `import-linter` kiểm tra các ranh giới này. Vì vậy Phase 2 có thể thay
adapter hoặc cách tìm kiếm mà ít ảnh hưởng đến hợp đồng nghiệp vụ.

```text
app/
├── main.py         # Khởi tạo FastAPI, middleware, router, handler lỗi
├── api/            # Route v1, JWT middleware, dependency, đọc upload
├── schemas/        # DTO: kiểm tra request và định dạng response
├── services/       # Use case user, face profile, check-in; phân quyền
├── domain/         # Entity, lỗi, hợp đồng Repository/FaceEmbedder
├── repositories/   # SQLAlchemy adapter và mapper ORM ↔ domain
├── models/         # ORM: User, FaceProfile, CheckInRecord
├── ml/             # InsightFace adapter sinh embedding
└── core/           # Cấu hình môi trường, password hash và JWT
alembic/            # Migration schema
scripts/            # Seed, benchmark, xuất OpenAPI
tests/              # Unit, API và integration test
docs/               # API JSON, ERD, kiến trúc, baseline, vận hành
.github/workflows/  # CI: quality gate, test và Docker/Compose
```

Ví dụ luồng gọi: `app/api/v1/check_ins.py` nhận ảnh → `CheckInService` gọi `FaceEmbedder` và
`FaceProfileRepository` → NumPy chọn hồ sơ → `CheckInRepository` lưu kết quả → API trả DTO.
[Kiến trúc chi tiết](docs/architecture.md) trình bày thêm các quyết định và đánh đổi.

## 5. Đặc tả API, xác thực và preview

**Tệp đặc tả:** [docs/openapi.json](docs/openapi.json), chuẩn OpenAPI 3.1, chứa 14 thao tác,
schema request/response và OAuth2. [API spec](docs/api-spec.md) bổ sung quy tắc, mã lỗi và
kịch bản kiểm thử. Prefix nghiệp vụ là `/api/v1`; bảng dưới dùng đường dẫn đầy đủ.

| Method / path | Mục đích và dữ liệu vào | Quyền |
|---|---|---|
| `GET /health` | Kiểm tra handler hoạt động | Công khai |
| `POST /api/v1/auth/login` | OAuth2 form: `username` là email, `password`; trả access token | Công khai |
| `GET /api/v1/auth/me` | Thông tin user đang đăng nhập | Đăng nhập |
| `POST /api/v1/users` | JSON: `email`, `password`, `full_name`, `role` tùy chọn | Admin |
| `GET /api/v1/users` | Danh sách tài khoản | Admin |
| `GET /api/v1/users/{user_id}` | Thông tin tài khoản theo ID | Chính user hoặc admin |
| `DELETE /api/v1/users/{user_id}` | Xóa tài khoản | Admin |
| `POST /api/v1/face-profiles` | Multipart field `image`; đăng ký cho user hiện hành | Đăng nhập |
| `GET /api/v1/face-profiles` | Danh sách hồ sơ, query `user_id` tùy chọn | User chỉ thấy của mình; admin được lọc toàn bộ |
| `DELETE /api/v1/face-profiles/{profile_id}` | Xóa hồ sơ mặt | Chủ hồ sơ hoặc admin |
| `POST /api/v1/checkins` | Multipart field `image`; nhận diện và ghi sự kiện | Công khai |
| `GET /api/v1/checkins` | Lọc `user_id`, `start`, `end`, `limit` | User chỉ thấy của mình; admin được lọc toàn bộ |
| `GET /api/v1/checkins/{record_id}` | Chi tiết sự kiện | User gắn với record hoặc admin |
| `DELETE /api/v1/checkins/{record_id}` | Xóa sự kiện | Admin |

Tạo thành công trả `201`, đọc `200`, xóa `204`; riêng đăng nhập trả `200`. Thiếu/sai/hết hạn JWT
trả `401`, thiếu quyền `403`. Lịch sử lọc khoảng `[start, end)`, mới nhất trước, `limit` mặc định
50 và tối đa 200; chưa có cursor. Lỗi Domain có `detail`, `error`, có thể thêm `record_id`;
lỗi validation dùng cấu trúc FastAPI. OpenAPI hiện chưa khai báo đầy đủ schema lỗi Domain cho
từng route, nên cần đối chiếu bảng lỗi trong API spec.

**Preview và thử API:** sau khi chạy hệ thống, mở [Swagger UI](http://localhost:8000/docs),
chọn **Authorize**, nhập email vào `username` và mật khẩu đã tạo, rồi dùng **Try it out**.
Schema trực tiếp ở <http://localhost:8000/openapi.json>. Có thể import tệp `docs/openapi.json`
vào công cụ preview OpenAPI để đọc khi backend chưa chạy; thực thi request cần backend.
Xuất lại JSON bằng `uv run python -m scripts.export_openapi`; test kiểm tra tệp khớp ứng dụng.

## 6. Vấn đề Phase 1 và hướng cải tiến Phase 2

Baseline lịch sử ngày **22/09/2026**, commit `4affbd0`, Kaggle CPU 4 core, Uvicorn một worker,
ngoài Compose; kết quả `POST /api/v1/checkins` với PostgreSQL:

| Request đồng thời | Throughput (request/giây) | p95 (ms) | CPU toàn máy |
|---:|---:|---:|---:|
| 1 | 4,83 | 227,7 | 78,8% |
| 8 | 8,46 | 1.116,0 | 99,7% |

p95 là mốc thời gian bao phủ khoảng 95% request. Khi tải tăng, CPU gần bão hòa và p95 tăng
khoảng 4,9 lần. Bộ đo chỉ có **một profile**, một lượt mỗi cấu hình và chưa tách thời gian
inference/DB/matching. Middleware đã đổi sau commit đo; phải đo lại bản bàn giao trước so sánh.

| Lựa chọn/giới hạn Phase 1 | Vấn đề dễ quan sát và thuộc tính chất lượng | Hướng Phase 2 / cách đánh giá |
|---|---|---|
| Inference CPU trong cùng dịch vụ | Tăng request đồng thời làm CPU gần bão hòa, độ trễ tăng như baseline; ảnh hưởng hiệu năng | Đo riêng các công đoạn; thử thread ONNX/worker hoặc tách inference khi cần; so throughput, p95/p99, RAM, lỗi |
| Mỗi request tải toàn bộ hồ sơ và tạo ma trận | Chi phí đọc/so khớp tăng theo số profile; ảnh hưởng khả năng mở rộng, chưa đo tập lớn | Thử 100/1.000/10.000 hồ sơ; lọc tại DB, cache ma trận hoặc vector index; đo latency/RAM, kiểm tra cập nhật cache và độ đúng tìm kiếm |
| Chưa có idempotency key | Retry cùng request sau mất kết nối có thể tạo nhiều record; ảnh hưởng độ tin cậy | Key theo thiết bị và ràng buộc DB; gửi đồng thời cùng key, kiểm tra chỉ một sự kiện; phân biệt retry với hai lần điểm danh hợp lệ |
| Check-in công khai, chưa liveness/rate limit | Chưa xác minh thiết bị hay người thật; có rủi ro gửi ảnh giả/lạm dụng tải | Xác thực/thu hồi credential thiết bị, giới hạn tải, thử liveness; đo phát hiện giả mạo, chặn nhầm và độ trễ |
| Ngưỡng `0.40` chưa hiệu chỉnh trên tập đại diện | Chưa biết tỷ lệ nhận nhầm/từ chối nhầm; ảnh hưởng độ chính xác | Tách ảnh đăng ký/kiểm thử, có ảnh khác người/góc/ánh sáng; đo FAR (nhận nhầm), FRR (từ chối nhầm), chọn ngưỡng |
| Commit với mọi lỗi Domain | Khi mở rộng nhiều bước ghi có nguy cơ lưu một phần dữ liệu; ảnh hưởng tính nguyên tử | Tách kết quả audit khỏi lỗi cần rollback, cân nhắc Unit of Work; inject lỗi giữa các bước và kiểm tra DB |
| API/vận hành còn tối giản | User/profile chưa phân trang, schema lỗi chưa đầy đủ; health không kiểm tra DB/model | Thêm phân trang, chuẩn hóa lỗi, readiness và metric; thử tập lớn, ngắt DB/model, kiểm tra khả năng phục hồi |

Các hạn chế là đánh đổi của bản cơ bản. Ngoài baseline đã nêu, tác động về dữ liệu lớn,
giả mạo và độ chính xác chưa được đo. Xem [số liệu gốc](docs/benchmark-phase1.md) và
[phân tích cải tiến](docs/phase-2-improvements.md). Phase 2 phải đặt mục tiêu trước khi sửa,
đo cả hai bản trên cùng cấu hình Kaggle CPU, cùng dữ liệu/model/workload; warm-up, lặp ít nhất
ba lần, báo trung vị và độ dao động. Chỉ chấp nhận cải tiến khi đạt mục tiêu và vẫn đúng auth,
ownership, matching, audit và lịch sử sau xóa. Hiện chưa có kết quả sau cải tiến.

## 7. Chạy thử, kiểm chứng và tài liệu bàn giao

Mã nguồn bàn giao nằm trên nhánh **`main`** của [GitHub](https://github.com/thanhphu25/face-checkin-service/tree/main).
Lấy code và vào thư mục dự án:

```bash
git clone --branch main https://github.com/thanhphu25/face-checkin-service.git
cd face-checkin-service
git rev-parse HEAD
```

Ghi lại commit khi nhận dự án để Phase 2 xác định được bản gốc và bản sau cải tiến. Build/chạy
stack cần Git, Docker/Compose v2 và Internet để tải image/dependency/model khi chưa có cache.
Sao chép `.env.example` thành `.env`, sinh `JWT_SECRET`, đặt `POSTGRES_PASSWORD` theo
[hướng dẫn cấu hình](docs/running.md#clone-và-cấu-hình), rồi chạy từ thư mục gốc:

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose logs migrate
```

Dockerfile dùng hai giai đoạn `builder` và `runtime`: uv cài dependency đã khóa trong `uv.lock`,
rồi môi trường Python và code được đưa sang image chạy bằng user `app` UID 10001. Compose dùng
chung image cho migration và API, khởi động theo thứ tự PostgreSQL healthy → migration thành
công → Uvicorn một worker. Volume `postgres_data` giữ DB, `insightface_models` giữ model đã tải.

Model được tải khi cần và nạp vào RAM từng tiến trình. Request đầu tới các route
face-profile/check-in, kể cả GET/DELETE do dùng chung dependency, có thể chậm vì khởi tạo model.
`/health` chỉ kiểm tra HTTP; xem [cách chuẩn bị model](docs/running.md#chuẩn-bị-model-trước-khi-thử-api)
trước khi thử nhận diện.

Stack mới chưa có tài khoản. Làm theo [hướng dẫn seed](docs/running.md#seed-dữ-liệu-mẫu):
`scripts/seed.py` nhận `SEED_ADMIN_PASSWORD` và `SEED_USER_PASSWORD` do người chạy cung cấp,
tạo admin/user mẫu, một hồ sơ mặt và lịch sử. Bước này cần Python 3.12 và uv trên host; URL seed
phải trỏ vào PostgreSQL được Compose publish. Tài liệu có lệnh cho Bash và PowerShell. Sau đó
thử đăng nhập → đăng ký mặt → điểm danh → tra cứu trên Swagger. `docker compose down` dừng stack
và giữ dữ liệu.

Kiểm tra trong môi trường Python 3.12:

```bash
uv sync --python 3.12 --frozen --extra dev
JWT_SECRET=local-test-only uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
```

Integration test PostgreSQL cần database test riêng, `POSTGRES_TEST_DATABASE_URL` và
`REQUIRE_POSTGRES_TESTS=1`; xem [hướng dẫn kiểm thử](docs/running.md#5-test-quality-gate-và-benchmark).
CI được cấu hình kiểm tra quality gate, unit/API/integration SQLite/PostgreSQL, build Docker
và khởi động Compose sạch. Bộ bàn giao gồm mã nguồn, migration, seed, Docker/Compose,
[OpenAPI JSON](docs/openapi.json), [API spec](docs/api-spec.md), [ERD](docs/erd.md),
[kiến trúc](docs/architecture.md), [baseline](docs/benchmark-phase1.md) và
[hướng dẫn vận hành](docs/running.md).

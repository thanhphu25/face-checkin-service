# Face Check-in Service

Dịch vụ backend check-in/điểm danh bằng khuôn mặt. Đồ án kiến trúc phần mềm — đề bài gốc ở [docs/2026.md](docs/2026.md).

> ⚠️ **Trạng thái: Tuần 1/8 — mới có khung dự án.**
> Hiện chỉ chạy được endpoint `/health` và Swagger UI. Chưa có nghiệp vụ, chưa có DB thật, chưa có auth.
> Tiến độ chi tiết: [docs/checklist-tien-do-8-tuan.md](docs/checklist-tien-do-8-tuan.md)

## Nghiệp vụ & phạm vi

Người dùng đăng ký khuôn mặt của mình một lần, sau đó check-in bằng cách đưa ảnh khuôn mặt — hệ thống sinh embedding, so khớp với các hồ sơ đã có, và ghi lại lượt check-in.

| Pha | Nội dung | Hạn |
|---|---|---|
| **Pha 1** | Xây hệ thống với chức năng cơ bản: CRUD 3 entity, phân tầng, auth, Docker, benchmark baseline | Cuối Tuần 6 |
| **Pha 2** | Nhận hệ thống từ nhóm khác, chọn 2–3 cải tiến chất lượng, đo trước/sau | Cuối Tuần 8 |

Ba entity chính: `User`, `FaceProfile` (hồ sơ khuôn mặt), `CheckInRecord` (lượt check-in).

## Kiến trúc

Ba tầng, tầng nghiệp vụ là Python thuần — không import framework web hay thư viện DB:

```
API Layer          FastAPI routers, Pydantic schemas, auth dependency
    │              (app/api, app/schemas)
    ▼
Service Layer      Business logic thuần Python — KHÔNG import FastAPI/SQLAlchemy
    │              (app/services, phụ thuộc ABC ở app/domain)
    ▼
Repository Layer   SQLAlchemy implementation, chuyển đổi ORM ↔ domain entity
    │              (app/repositories, app/models)
    ▼
PostgreSQL / SQLite
```

Quy tắc phụ thuộc này được **CI kiểm tra tự động** bằng `import-linter` — xem [.importlinter](.importlinter).

Tài liệu đầy đủ:
- [docs/architecture.md](docs/architecture.md) — phân tầng, luồng xử lý, auth, thuật toán so khớp
- [docs/erd.md](docs/erd.md) — mô hình dữ liệu, DDL, quyết định lưu embedding
- [docs/ke-hoach-8-tuan.md](docs/ke-hoach-8-tuan.md) — kế hoạch, API spec, RACI, rủi ro

## Yêu cầu môi trường

- **Python 3.12** (không dùng 3.13+ — wheel của onnxruntime/insightface thường ra chậm hơn)
- Git

## Chạy thử

```bash
# 1. Tạo môi trường ảo + cài dependencies
uv sync --python 3.12 --frozen --extra dev
source .venv/bin/activate

# Không dùng uv: python3.12 -m venv .venv, activate, rồi pip install -e ".[dev]"

# 2. Tạo file cấu hình
cp .env.example .env
# Sinh JWT_SECRET rồi điền vào .env:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Chạy
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000/docs để xem Swagger UI.

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

> App sẽ **không khởi động** nếu thiếu `JWT_SECRET` trong `.env` — đây là chủ ý, để không bao giờ chạy với secret mặc định.

## Kiểm tra chất lượng code

```bash
ruff check .              # lint
ruff format .             # format (thay cho black)
lint-imports              # kiểm tra phân tầng — phải luôn 3/3 contract KEPT
pytest -q                 # chạy test
```

Cài git hook để tự chạy khi commit (mỗi máy làm một lần):

```bash
pre-commit install
```

## Biến môi trường

Xem [.env.example](.env.example) để biết danh sách đầy đủ. Các biến quan trọng:

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./facecheckin.db` | Postgres khi chạy docker-compose |
| `JWT_SECRET` | *(không có)* | **Bắt buộc** — thiếu thì app không khởi động |
| `SIMILARITY_THRESHOLD` | `0.40` | Ngưỡng cosine, phải hiệu chỉnh ở Tuần 3 |
| `EMBEDDING_MODEL` | `buffalo_s` | Chưa chốt chính thức |

## Cấu trúc thư mục

```
app/
├── main.py           # FastAPI app
├── core/config.py    # cấu hình từ .env (pydantic-settings)
├── domain/           # entity + ABC (port) — Python thuần, chưa có nội dung
├── services/         # nghiệp vụ — Python thuần, chưa có nội dung
├── models/           # SQLAlchemy ORM models (draft theo ERD)
├── repositories/     # adapter SQLAlchemy — chưa có nội dung
├── ml/               # adapter sinh embedding — chưa có nội dung
├── schemas/          # Pydantic DTO — chưa có nội dung
└── api/              # routers, DI, exception handlers — chưa có nội dung
alembic/              # migration (đã init, chưa có migration nào)
docs/                 # tài liệu thiết kế & kế hoạch
tests/                # unit / integration / api
```

## Đã làm được gì đến hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Tài liệu kiến trúc + ERD | ✅ xong |
| Khung package 3 tầng | ✅ xong |
| Cấu hình qua `.env` (pydantic-settings) | ✅ xong |
| SQLAlchemy models | ✅ draft theo ERD (chưa có migration) |
| Alembic | ✅ đã init và nối vào config/models |
| FastAPI app + `/health` + Swagger | ✅ chạy được |
| Lint + format + kiểm tra phân tầng trong CI | ✅ xong, đang xanh |
| Repository / Service / API nghiệp vụ | ❌ Tuần 2–3 |
| Auth JWT + RBAC | ❌ Tuần 4 |
| Docker / docker-compose | ❌ Tuần 5 |
| Benchmark trên Kaggle CPU | ❌ Tuần 6 |

## Ghi chú cho người đọc sau

Các mục sau sẽ được bổ sung đúng tuần theo kế hoạch, hiện **cố ý chưa có**: bảng đặc tả endpoint đầy đủ, hướng dẫn `docker compose up`, kết quả benchmark baseline, ADR, tài khoản mẫu để đăng nhập thử.

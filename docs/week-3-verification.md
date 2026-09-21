# Xác minh hoàn tất Tuần 3

Ngày chạy: 2026-09-21.

## Môi trường và dữ liệu kiểm thử

- Python 3.12.5.
- InsightFace 2.0, ONNX Runtime 1.23.2, model `buffalo_s` chạy CPU.
- SQLite qua driver chuẩn của Python.
- PostgreSQL 16 qua service `postgres` trong `compose.yaml`.
- PostgreSQL dùng database cách ly `facecheckin_w3_verification`; sau kiểm chứng, script đã
  xóa dữ liệu do nó tạo, database test đã được drop và container đã dừng. Database/volume dev
  không bị reset hoặc xóa.
- Ảnh có mặt là crop trong bộ nhớ từ `t1.jpg` công khai đi kèm wheel InsightFace. Ảnh không được
  chép vào repo. Nhánh `no_face` dùng ảnh PNG đen tổng hợp trong bộ nhớ.
- Model cache nằm ngoài repo trong cache người dùng; không có model, ảnh mặt, secret hay database
  test nào được commit.

## Luồng API và embedding thật

Script dùng cho cả hai DB:

```powershell
python scripts/verify_week3.py --database-url <isolated-database-url>
```

Script chạy migration rồi gọi đúng API `/api/v1`: tạo user, gửi ảnh trắng để kiểm tra `no_face`,
upload ảnh thật để đăng ký profile, gửi lại ảnh qua check-in, đọc lịch sử, và cuối cùng xác nhận
embedding/bản ghi qua Repository. Không override bằng embedder giả; dependency API nhận một
`InsightFaceEmbedder` thật đã nạp `buffalo_s`.

Kết quả trên SQLite và PostgreSQL giống nhau:

```json
{
  "check_in_status": "success",
  "embedding_dim": 512,
  "embedding_dtype": "float32",
  "embedding_norm": 1.0,
  "history_statuses": ["no_face", "success"],
  "model": "buffalo_s",
  "no_face_http_status": 422,
  "persisted_statuses": ["no_face", "success"],
  "profile_persisted": true,
  "similarity_score": 1.0
}
```

Điều này chứng minh luồng ảnh → detection/embedding thật → API → Service → Repository → DB và
cosine matching đã chạy end-to-end. Response API không chứa `embedding` hoặc `hashed_password`.

PostgreSQL sau khi script tự xóa dữ liệu trả:

```text
alembic_version: 0001
users | face_profiles | check_in_records: 0 | 0 | 0
```

## API, transaction và boundary

- `/docs` trả Swagger UI và OpenAPI chứa toàn bộ endpoint users, face profiles, check-ins dưới
  `/api/v1`; upload được khai báo `multipart/form-data`.
- API test bao phủ POST/GET/DELETE, status 201/200/204, validation 400/422 và response schema.
- Session theo request commit nhánh thành công; lỗi hệ thống rollback; lỗi nghiệp vụ dự kiến được
  commit để giữ audit `unmatched`/`no_face` trước khi handler trả 404/422.
- Test AST và `lint-imports` xác nhận `app/services` không import FastAPI, Starlette, SQLAlchemy,
  Alembic, model, repository implementation hay schema API.

## Lệnh kiểm chứng cuối

```powershell
$env:RUN_REAL_MODEL_TESTS='1'
pytest -q -p no:cacheprovider
ruff check .
ruff format --check .
lint-imports
git diff --check
```

Kết quả cuối được ghi khi đóng commit W3-C08: 53 test pass (bao gồm E2E model thật), Ruff lint và
format pass, 3/3 import contract được giữ, `git diff --check` pass.

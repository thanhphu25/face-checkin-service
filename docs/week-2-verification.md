# Xác minh hoàn tất Tuần 2

Ngày chạy: 2026-09-21.

## Môi trường

- Python 3.12.5.
- SQLite qua driver chuẩn của Python.
- PostgreSQL 16 chạy bằng service `postgres` trong `compose.yaml`.
- Kiểm thử PostgreSQL dùng database cách ly `facecheckin_w2_smoke`, không reset database dev.

## Migration và CRUD

Các bước sau đã chạy thành công trên cả SQLite và PostgreSQL:

1. `alembic upgrade head` từ database rỗng.
2. `python scripts/manual_test_repo.py --database-url <url>`.
3. `alembic downgrade base`.
4. `alembic upgrade head`.
5. Chạy lại CRUD smoke script.

Mỗi lượt smoke test đều xác nhận:

- `User`: create, get, get-by-email, list và delete qua `UserRepository`.
- `FaceProfile`: create, get, list, list-by-user và delete qua `FaceProfileRepository`;
  embedding đọc lại đúng kiểu `float32` và đúng giá trị.
- `CheckInRecord`: create, get, list theo user và delete qua `CheckInRepository`.
- Script xóa toàn bộ dữ liệu do chính nó tạo sau khi xác minh.

`alembic check` trên PostgreSQL trả về `No new upgrade operations detected`, xác nhận ORM và
migration không bị lệch schema.

## Quality gates

- `pytest -q -p no:cacheprovider`: 16 passed.
- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `lint-imports`: 3 contracts kept, 0 broken.
- `git diff --check`: passed.

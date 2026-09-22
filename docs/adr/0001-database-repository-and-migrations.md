# ADR 0001 — Database, Repository và migration

- Status: Accepted
- Date: 2026-09-22

## Context

Hệ thống cần một database triển khai nhất quán, đồng thời cần test Repository nhanh trên máy cá
nhân. Domain và Service không được phụ thuộc ORM. Schema phải dựng lại được từ một database rỗng và
phải giữ đúng `CASCADE`/`SET NULL` trên cả hai backend.

## Decision

- PostgreSQL là database cho Docker Compose và môi trường production/baseline; SQLite chỉ dùng cho
  test nhanh và chạy local đơn giản.
- Các port Repository ở `app/domain/ports.py` được hiện thực bằng SQLAlchemy trong
  `app/repositories/sqlalchemy.py`. Adapter là nơi duy nhất ánh xạ ORM sang domain và ngược lại.
- Alembic là nguồn tạo/nâng schema. App và Compose không gọi `Base.metadata.create_all()`.
- Mỗi HTTP request có một SQLAlchemy `Session`. Repository `flush()` để trả ID; dependency session
  ở composition root commit khi use case kết thúc, commit audit cho lỗi domain dự kiến và rollback
  lỗi hệ thống.
- Integration test chạy cùng contract qua migration thật trên SQLite và PostgreSQL test cách ly.

## Alternatives considered

- Chỉ dùng PostgreSQL: sát production hơn nhưng làm unit/integration loop chậm và bắt buộc Docker.
- Dùng SQLite ở production: vận hành đơn giản nhưng concurrency, kiểu thời gian và ràng buộc không
  phù hợp mục tiêu triển khai.
- Raw SQL hoặc trả ORM khỏi Repository: ít lớp hơn nhưng làm Service phụ thuộc data access.
- `create_all()` lúc startup: tiện ban đầu nhưng không nâng cấp schema đã tồn tại và làm lệch lịch
  sử migration.
- Unit of Work riêng: hỗ trợ nhiều thao tác ghi nguyên tử nhưng chưa cần khi mỗi use case Pha 1 chỉ
  ghi một bảng.

## Consequences

- Mapping và hành vi constraint phải được test trên cả hai dialect; SQLite phải bật foreign keys
  cho từng connection.
- PostgreSQL test cần service/database riêng; khi không cấp URL thì local test ghi rõ skip, còn CI
  đặt `REQUIRE_POSTGRES_TESTS=1` để thiếu database là lỗi.
- Cần thêm Unit of Work và chuyển ranh giới transaction vào Service khi một use case phải ghi nhiều
  bảng theo kiểu cùng thành công hoặc cùng rollback.
- Quyết định database cần xem lại nếu production buộc dùng một hệ quản trị khác hoặc Pha 2 chọn một
  tính năng chỉ có ở PostgreSQL sau khi benchmark chứng minh lợi ích.

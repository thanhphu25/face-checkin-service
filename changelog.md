# Changelog

Mỗi commit mới phải thêm một mục ở đầu lịch sử theo định dạng:

```text
## YYYY-MM-DD — type(scope): mô tả ngắn

- Thay đổi chính thứ nhất.
- Thay đổi chính thứ hai.
```

Chỉ ghi thay đổi có ý nghĩa với dự án, viết ngắn gọn và sắp xếp commit mới nhất lên trước.

## 2026-09-21 — perf(benchmark): scaffold API load harness

- Thêm harness async cho endpoint cuối `/api/v1/checkins` với URL, ảnh, request và concurrency cấu hình được.
- Tính throughput cùng p50/p95/p99 tại console; chưa chạy hoặc lưu baseline trước Tuần 6.

## 2026-09-21 — feat(api): implement resource routers

- Hoàn thiện endpoint CRUD users, face profiles và check-ins dưới `/api/v1` chưa có auth.
- Thêm upload JPEG/PNG có giới hạn dung lượng, response không lộ password hash hoặc embedding.

## 2026-09-21 — feat(api): add v1 composition root and error handlers

- Lắp session theo request, Repository, Service, embedder singleton và password hasher qua dependency factory.
- Commit audit cho lỗi nghiệp vụ dự kiến, rollback lỗi hệ thống và map lỗi domain sang HTTP 400/404/422.

## 2026-09-21 — feat(service): implement check-in service

- Thêm cosine matching vector hóa, lọc profile theo model và ngưỡng cấu hình.
- Ghi lịch sử cho cả `success`, `unmatched`, `no_face` và hỗ trợ truy vấn/xóa bản ghi.

## 2026-09-21 — feat(service): implement face profile service

- Thêm đăng ký, liệt kê và xóa hồ sơ khuôn mặt qua các domain port.
- Kiểm tra user tồn tại và củng cố bất biến embedding `float32` đã L2-normalized.

## 2026-09-21 — feat(service): implement user service

- Thêm CRUD người dùng qua Repository port, chuẩn hóa email bằng trim + casefold.
- Băm mật khẩu qua `PasswordHasher` port và trả lỗi domain cho email trùng/không hợp lệ.

## 2026-09-21 — feat(ml): implement InsightFace embedder

- Thêm adapter InsightFace CPU xử lý rõ ảnh lỗi, không có mặt và nhiều mặt.
- Bảo đảm embedding đầu ra luôn liên tục, `float32` và L2-normalized; khóa dependency ML.

## 2026-09-21 — test(repo): add CRUD smoke script and close week 2

- Thêm script tạo/đọc/liệt kê/xóa cả ba entity hoàn toàn qua Repository port.
- Xác nhận migration và CRUD trên SQLite/PostgreSQL, hoàn tất checklist và DoD Tuần 2.

## 2026-09-21 — feat(api): scaffold v1 resource routers

- Thêm router rỗng có prefix ổn định cho users, face profiles và check-ins dưới `/api/v1`.
- Lắp router phiên bản vào FastAPI app, chưa nối service hay nghiệp vụ.

## 2026-09-21 — feat(schema): add API request and response schemas

- Thêm schema request/response cho user, hồ sơ khuôn mặt và lượt check-in.
- Xác thực input, khoảng thời gian truy vấn và bảo đảm response không lộ hash mật khẩu/embedding.

## 2026-09-21 — feat(repo): implement SQLAlchemy repositories

- Thêm mapper ORM ↔ domain và adapter SQLAlchemy cho User, FaceProfile, CheckInRecord.
- Bao phủ CRUD, filter lịch sử, giới hạn kết quả và mã hóa embedding float32 bằng integration test.

## 2026-09-21 — feat(db): finalize models and add initial migration

- Chốt ORM cho ba entity với khóa chính identity tương thích PostgreSQL/SQLite.
- Thêm migration schema đầu tiên và kiểm thử vòng upgrade → downgrade → upgrade trên SQLite.

## 2026-09-21 — chore(dev): add PostgreSQL compose service

- Thêm PostgreSQL 16 cho môi trường dev với volume bền vững và healthcheck.
- Bổ sung biến môi trường mẫu cho database, tài khoản và cổng PostgreSQL.
- Xác thực cấu hình Compose và cập nhật checklist Tuần 2.

## 2026-09-21 — feat(domain): add face embedder port

- Thêm `FaceEmbedder` ABC với tên model và hợp đồng sinh embedding từ ảnh.
- Export port qua package domain, thêm unit test và cập nhật checklist Tuần 2.

## 2026-09-21 — feat(domain): add entities and repository ports

- Thêm domain entity và enum cho `User`, `FaceProfile`, `CheckInRecord`.
- Thêm Repository ABC độc lập framework cho ba entity.
- Thêm unit test và cập nhật checklist Tuần 2.
- Thêm kế hoạch commit theo dependency cho toàn bộ Tuần 2–8.

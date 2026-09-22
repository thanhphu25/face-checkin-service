# Changelog

Mỗi commit mới phải thêm một mục ở đầu lịch sử theo định dạng:

```text
## YYYY-MM-DD — type(scope): mô tả ngắn

- Thay đổi chính thứ nhất.
- Thay đổi chính thứ hai.
```

Chỉ ghi thay đổi có ý nghĩa với dự án, viết ngắn gọn và sắp xếp commit mới nhất lên trước.

## 2026-09-22 — test(repo): add SQLite and PostgreSQL integration tests

- Chạy cùng bộ integration test qua Repository, domain mapping và migration thật trên SQLite lẫn PostgreSQL 16 cách ly.
- Bao phủ CRUD, enum, unique email, embedding float32/bytes/dimension/model, cascade/SET NULL, filter, thứ tự, limit và SQLite foreign keys; thêm migration `0002` sửa xung đột giữa CHECK và lịch sử được ẩn danh.

## 2026-09-22 — test(auth): verify protected endpoints and close week 4

- Thêm SQLite API integration cho login/JWT, 401/403/404, ownership/RBAC; kiểm tra OpenAPI security và auth không copy-paste.
- Cập nhật CI cho `week4`, chạy 78 test gồm InsightFace thật và xác minh PostgreSQL cách ly; ghi bằng chứng và đóng phần kỹ thuật Tuần 4.

## 2026-09-21 — test(service): cover face registration and check-in outcomes

- Củng cố fake Repository/FaceEmbedder đúng port cho đăng ký thành công, user thiếu, no-face và multiple-face.
- Bao phủ check-in success/unmatched/no-face, audit thất bại, loại profile sai model/dimension và ownership ở Service.

## 2026-09-21 — feat(auth): add shared authentication and RBAC

- Áp dụng `get_current_user`/`require_admin` dùng chung cho các route được bảo vệ, giữ `POST /checkins` công khai.
- Đưa ownership vào Service, giới hạn user thường ở tài nguyên/lịch sử của mình và phân biệt lỗi 401/403/404.

## 2026-09-21 — feat(auth): add password hashing and JWT login

- Thay hasher tạo mới bằng Argon2id có tương thích PBKDF2 Tuần 3; khóa Argon2/PyJWT và thêm JWT có `sub`, `role`, `iat`, `exp`.
- Thêm đăng nhập không làm lộ email tồn tại, dependency xác thực dùng chung và endpoint `/auth/login`, `/auth/me` không lộ password hash.

## 2026-09-21 — docs(auth): record dependency injection and sample-user contract

- Chốt OAuth2 dependency dùng chung, JWT contract, ma trận endpoint và ownership/RBAC Tuần 4.
- Xác nhận `role` đã có trong domain/ORM/migration `0001`, định nghĩa tài khoản mẫu không chứa secret và giữ các xác nhận pair/review của con người ở trạng thái chưa hoàn tất.

## 2026-09-21 — test(api): verify CRUD and face embedding flow

- Thêm kiểm thử API/OpenAPI, boundary Service và E2E dùng model InsightFace thật qua SQLite.
- Xác minh cùng luồng trên PostgreSQL cách ly, ghi bằng chứng và hoàn tất checklist/DoD Tuần 3.

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

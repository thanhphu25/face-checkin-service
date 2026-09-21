# Changelog

Mỗi commit mới phải thêm một mục ở đầu lịch sử theo định dạng:

```text
## YYYY-MM-DD — type(scope): mô tả ngắn

- Thay đổi chính thứ nhất.
- Thay đổi chính thứ hai.
```

Chỉ ghi thay đổi có ý nghĩa với dự án, viết ngắn gọn và sắp xếp commit mới nhất lên trước.

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

# ADR 0002 — Authentication và authorization

- Status: Accepted
- Date: 2026-09-22

## Context

API cần ít nhất một GET và một POST được bảo vệ, có RBAC `admin`/`user`, không lặp logic giải mã
token trong handler và không kéo FastAPI vào Service. Dữ liệu dev Tuần 3 từng có hash PBKDF2 tạm.

## Decision

- Login phát JWT access token có `sub`, `role`, `iat`, `exp`; FastAPI dùng một
  `OAuth2PasswordBearer` và dependency dùng chung `get_current_user`/`require_admin`.
- Không thêm auth middleware trùng chức năng. Mỗi request được bảo vệ chỉ decode token và lookup
  user hiện hành một lần; role trong database là nguồn quyết định cuối cùng.
- Mật khẩu mới dùng Argon2id. Adapter còn verify PBKDF2 tạm để dữ liệu Tuần 3 đăng nhập được, nhưng
  không tạo hash PBKDF2 mới.
- Rule role/ownership nằm trong Service/helper thuần Python. Router chỉ lấy principal đã xác thực,
  chuyển request/response và ánh xạ lỗi domain.

## Alternatives considered

- Auth middleware cho toàn bộ prefix: khó biểu diễn router có cả route công khai và bảo vệ; dùng
  cùng dependency sẽ decode/lookup hai lần.
- Copy kiểm tra bearer/role vào từng handler: trực tiếp nhưng dễ lệch quyền và vi phạm yêu cầu dùng
  cơ chế chung.
- Session cookie hoặc opaque token: hỗ trợ revoke dễ hơn nhưng cần state/server-side store ngoài
  phạm vi Pha 1.
- Chỉ dùng PBKDF2 cũ: giữ tương thích nhưng yếu hơn cấu hình Argon2id hiện tại cho password mới.

## Consequences

- JWT access token không thể revoke tức thời; token sống đến `exp`, trong khi việc khóa/xóa user có
  hiệu lực ngay vì dependency luôn lookup database.
- PBKDF2 chỉ là đường tương thích tạm. Cần bỏ sau khi có cơ chế rehash/migration và không còn hash
  cũ cần hỗ trợ.
- Cần xem lại quyết định nếu có refresh token/logout, SSO, nhiều issuer, hoặc yêu cầu revoke tức
  thời. Middleware chỉ nên được thêm cho concern khác và không được xác thực lại cùng path.

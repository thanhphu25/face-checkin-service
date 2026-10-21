# ADR 0002 — Authentication và authorization

- Status: Accepted
- Date: 2026-09-22
- Updated: 2026-10-19 — dùng AuthenticationMiddleware để đáp ứng trực tiếp tiêu chí middleware.

## Context

API cần ít nhất một GET và một POST được bảo vệ, có RBAC `admin`/`user`, không lặp logic giải mã
token trong handler và không kéo FastAPI vào Service. Dữ liệu dev Tuần 3 từng có hash PBKDF2 tạm.

## Decision

- Login phát JWT access token có `sub`, `role`, `iat`, `exp`.
- Starlette `AuthenticationMiddleware` dùng `JWTAuthenticationBackend` để xác minh Bearer JWT,
  lookup user hiện hành và gắn principal vào `request.user`. JWT/user chỉ xác minh một lần/request;
  role trong database là nguồn quyết định cuối cùng.
- `get_current_user` lấy domain user từ principal; `require_admin` kiểm tra role. Dependency
  `OAuth2PasswordBearer` yêu cầu bearer header và khai báo OAuth2 cho Swagger, không decode JWT.
- Không có Bearer credential: middleware cho đi tiếp ở trạng thái chưa đăng nhập. Dependency của
  endpoint được bảo vệ trả `401`; endpoint công khai tiếp tục hoạt động. Nếu gửi Bearer token
  lỗi/hết hạn/user đã xóa, middleware trả JSON `401` và `WWW-Authenticate: Bearer`, kể cả route
  công khai. Header dùng scheme khác Bearer không xác thực user.
- Lookup SQLAlchemy đồng bộ chạy trong threadpool; session đọc được tạo/đóng trong cùng worker
  thread trước khi gọi endpoint. Endpoint có session nghiệp vụ riêng; không truyền ORM object
  hay session qua request và không chia sẻ transaction giữa xác thực và nghiệp vụ.
- Mật khẩu mới dùng Argon2id. Adapter còn verify PBKDF2 tạm để dữ liệu Tuần 3 đăng nhập được, nhưng
  không tạo hash PBKDF2 mới.
- Rule role/ownership nằm trong Service/helper thuần Python. Router chỉ lấy principal đã xác thực,
  chuyển request/response và ánh xạ lỗi domain.

## Alternatives considered

- Chỉ dùng dependency: ít thay đổi hơn nhưng không trực tiếp sử dụng middleware như đề yêu cầu.
- Middleware chặn toàn bộ prefix: phải duy trì danh sách ngoại lệ cho login/check-in/docs.
- Thêm middleware nhưng giữ decode/lookup ở dependency: xác thực hai lần và tốn thêm truy vấn.
- Copy kiểm tra bearer/role vào từng handler: trực tiếp nhưng dễ lệch quyền và vi phạm yêu cầu dùng
  cơ chế chung.
- Session cookie hoặc opaque token: hỗ trợ revoke dễ hơn nhưng cần state/server-side store ngoài
  phạm vi Pha 1.
- Chỉ dùng PBKDF2 cũ: giữ tương thích nhưng yếu hơn cấu hình Argon2id hiện tại cho password mới.

## Consequences

- JWT access token chưa có revocation store; token sống đến `exp`, nhưng request sau khi xóa user
  bị từ chối vì middleware luôn lookup database. Role thay đổi có hiệu lực ở request tiếp theo.
- Các request có Bearer credential dùng thêm một session đọc ngắn; request công khai không có
  credential không decode token hoặc lookup user. Kiểm thử middleware đếm một decode/một lookup,
  kiểm tra lỗi token, role hiện hành và endpoint công khai.
- PBKDF2 chỉ là đường tương thích tạm. Cần bỏ sau khi có cơ chế rehash/migration và không còn hash
  cũ cần hỗ trợ.
- Cần xem lại quyết định nếu có refresh token/logout, SSO, nhiều issuer, hoặc yêu cầu revoke tức
  thời. Mọi mở rộng phải giữ một điểm xác thực và không decode/lookup lại ở dependency.

# Hợp đồng xác thực và phân quyền Tuần 4

Ngày chốt kỹ thuật: 2026-09-21.

## 1. Dependency injection dùng chung

- API dùng `OAuth2PasswordBearer` và hai FastAPI dependency dùng chung:
  `get_current_user` giải mã token rồi tải user hiện hành từ Repository;
  `require_admin` dùng lại `get_current_user` và kiểm tra vai trò.
- Dependency được gắn ở từng route theo ma trận bên dưới. Một router có cả route công khai và
  route được bảo vệ nên không thể gắn một dependency xác thực cho toàn router.
- Không thêm auth middleware. Dependency là cơ chế xác thực duy nhất, vì vậy một request không bị
  giải mã token hoặc tra user trong database hai lần.
- Handler chỉ nhận `current_user` đã xác thực. Logic ownership có ý nghĩa nghiệp vụ nằm trong
  Service; handler không tự decode JWT và không rải `if role == ...` ở các router.
- Service chỉ phụ thuộc domain entity/port Python thuần, không import FastAPI, Starlette,
  SQLAlchemy, ORM model, Repository implementation hay Pydantic schema.

## 2. Hợp đồng đăng nhập và JWT

- `POST /api/v1/auth/login` nhận JSON `email` và `password`. Email được chuẩn hóa bằng cùng quy tắc
  `strip + casefold` của `UserService`.
- Email không tồn tại và mật khẩu sai cùng trả `401` với một thông điệp chung. API không trả hoặc
  ghi log mật khẩu hay password hash.
- Access token chứa `sub` là user id dạng chuỗi, `role`, `iat` và `exp`; thuật toán, secret và thời
  hạn lấy từ settings. Khi xác thực, user và vai trò hiện hành trong database là nguồn quyết định
  quyền, không tin riêng claim `role` có thể đã cũ.
- Token thiếu, sai chữ ký, malformed, hết hạn hoặc trỏ đến user không còn tồn tại đều trả `401` và
  có `WWW-Authenticate: Bearer`. User đã đăng nhập nhưng thiếu quyền trả `403`; tài nguyên hợp lệ
  về quyền nhưng không tồn tại trả `404`.
- Chỉ có access token trong phạm vi Tuần 4; không có refresh token, logout hay rate limiting.

## 3. Tài khoản mẫu

Đây là hợp đồng dữ liệu cho seed ở giai đoạn bàn giao, không phải credential được commit:

| Tên logic | Email mẫu | Vai trò | Mục đích |
|---|---|---|---|
| `admin` | `admin.sample@example.test` | `admin` | Kiểm tra thao tác quản trị |
| `user` | `user.sample@example.test` | `user` | Kiểm tra ownership của user thường |

Mật khẩu mẫu phải là giá trị giả do người chạy cung cấp lúc seed/test và chỉ password hash được
lưu. Không đặt mật khẩu mặc định, token hay secret thật trong source, tài liệu, log hoặc fixture
được commit.

## 4. Ma trận endpoint và ownership

| Endpoint | Quyền gọi | Quy tắc |
|---|---|---|
| `GET /health`, `/docs`, `/openapi.json` | Công khai | Endpoint hệ thống/tài liệu |
| `POST /api/v1/auth/login` | Công khai | Trả JWT khi credential hợp lệ |
| `GET /api/v1/auth/me` | Đã đăng nhập | Trả user hiện hành, không có password hash |
| `POST /api/v1/checkins` | Công khai | Máy chấm công; vẫn lưu audit `unmatched`/`no_face` |
| `POST /api/v1/users` | Chỉ admin | Client được chọn role cho user mới |
| `GET /api/v1/users` | Chỉ admin | Danh sách toàn bộ user |
| `GET /api/v1/users/{id}` | Admin hoặc chính user | Service kiểm tra ownership |
| `DELETE /api/v1/users/{id}` | Chỉ admin | Thao tác quản trị |
| `POST /api/v1/face-profiles` | Đã đăng nhập | Luôn đăng ký cho `current_user.id`; không nhận `user_id` từ client |
| `GET /api/v1/face-profiles` | Đã đăng nhập | User chỉ thấy profile của mình; admin được lọc/xem toàn bộ |
| `DELETE /api/v1/face-profiles/{id}` | Admin hoặc chủ profile | Service kiểm tra ownership |
| `GET /api/v1/checkins` | Đã đăng nhập | User chỉ thấy lịch sử của mình; admin được lọc/xem toàn bộ |
| `GET /api/v1/checkins/{id}` | Admin hoặc user của record | Service kiểm tra ownership |
| `DELETE /api/v1/checkins/{id}` | Chỉ admin | Thao tác quản trị |

## 5. Xác nhận schema và trạng thái review

Field `role` đã tồn tại trước Tuần 4 ở cả ba lớp:

- domain: `Role` và `User.role` trong `app/domain/entities.py`;
- ORM: `UserORM.role` cùng CHECK constraint trong `app/models/user.py`;
- migration đầu: cột `users.role` và `ck_users_role` trong
  `alembic/versions/0001_initial_schema.py`.

Vì vậy không tạo migration Tuần 4 rỗng hoặc dư thừa.

Phần kỹ thuật trong tài liệu này được đối chiếu với kiến trúc, code Tuần 3 và kế hoạch commit.
Checklist yêu cầu pair session nửa buổi và review chéo A/C là xác nhận của con người; chưa có bằng
chứng nên hai mục đó chưa được tick và không được tuyên bố đã hoàn thành.

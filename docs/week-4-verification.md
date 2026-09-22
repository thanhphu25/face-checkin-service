# Xác minh hoàn tất kỹ thuật Tuần 4

Ngày chạy cuối: 2026-09-22.

## Môi trường và phạm vi

- Python 3.12.5, FastAPI, SQLAlchemy/Alembic, Argon2id (`argon2-cffi==25.1.0`) và
  PyJWT (`pyjwt==2.10.1`) từ `uv.lock`.
- SQLite dùng database tạm do pytest tạo; PostgreSQL 16 dùng database cách ly
  `facecheckin_w4_verify_20260921_001` trong Compose.
- InsightFace 2.0, ONNX Runtime 1.23.2, model thật `buffalo_s` chạy CPU.
- Tất cả email, mật khẩu và JWT secret dùng trong kiểm thử là giá trị giả chỉ dành cho test. Không
  có `.env`, token, password, database, model cache hay ảnh khuôn mặt được thêm vào Git.

## Password hashing, login và JWT

- User mới được lưu bằng Argon2id; test xác nhận hash bắt đầu bằng `$argon2id$`, có salt khác nhau,
  không chứa plaintext, verify đúng/sai chính xác. Adapter vẫn verify hash PBKDF2 tạm từ Tuần 3 để
  dữ liệu dev cũ không bị khóa đăng nhập.
- `POST /api/v1/auth/login` dùng OAuth2 password form; email được `strip + casefold` trong
  `UserService`. Email không tồn tại và password sai cùng trả `401` với body
  `AuthenticationFailed`, không tiết lộ user có tồn tại.
- JWT có `sub` là user id, `role`, `iat`, `exp`; secret, thuật toán và thời hạn lấy từ settings.
  Test bao phủ token hợp lệ, malformed, sai chữ ký và hết hạn.
- `/api/v1/auth/me` trả user hiện hành nhưng không có `hashed_password`. Authentication dependency
  luôn tải user hiện hành từ Repository; role trong database là nguồn phân quyền cuối cùng.

## 401, 403, 404 và ownership/RBAC

`tests/api/test_auth_rbac_integration.py` chạy toàn bộ API trên SQLite thật qua migration, Service,
Repository và Argon2/JWT thật. Chỉ FaceEmbedder được thay bằng fake xác định để kiểm soát vector.

| Tình huống | Kết quả đã kiểm chứng |
|---|---:|
| Thiếu token ở `/auth/me`, `POST /face-profiles`, `GET /checkins` | 401 |
| Token malformed hoặc hết hạn | 401 |
| User thường gọi `POST /users` | 403 |
| User đọc user/check-in hoặc xóa face profile của người khác | 403 |
| User thường xóa check-in, kể cả record của mình | 403 |
| Tài nguyên không tồn tại sau khi đã xác thực | 404 |
| Admin tạo/đọc user, xem toàn bộ lịch sử và xóa profile/check-in | thành công |
| User truyền `user_id` người khác khi đăng ký mặt | bị bỏ qua; profile gắn current user |
| User filter profile/check-in theo người khác | Service ép scope về chính user |
| `POST /checkins` không có token | 201, vẫn công khai |

Unit test Service dùng fake triển khai đúng domain port, bao phủ admin/chính chủ/user khác. Logic
ownership nằm trong Service/helper `app/services/authorization.py`; router không tự decode JWT hoặc
rải điều kiện role.

## OpenAPI/Swagger và CI

- OpenAPI có security scheme `OAuth2PasswordBearer`, password flow trỏ đến
  `/api/v1/auth/login`.
- Các GET/POST/DELETE được bảo vệ đều có `security` và hiện ổ khóa trong Swagger; login và
  `POST /api/v1/checkins` không bị gắn security.
- AST test xác nhận không router nào gọi/import `decode_access_token`; việc decode và lookup user
  chỉ nằm trong dependency dùng chung.
- Workflow CI chạy `uv sync --frozen --extra dev`, Ruff lint, Ruff format, import-linter, app smoke
  test và pytest. Push vào cả `main` và `week4` đều kích hoạt workflow; bước pytest có JWT secret giả
  dành riêng cho CI.

## SQLite, PostgreSQL và InsightFace thật

Lượt SQLite model thật:

```text
RUN_REAL_MODEL_TESTS=1
tests/api/test_real_embedding_e2e.py: 1 passed
model=buffalo_s, embedding_dim=512, dtype=float32, norm=1.0
check-in=success, similarity=1.0, no_face=422
admin login=200, user login=200, /auth/me=200, invalid token=401, RBAC=403
```

Lượt PostgreSQL dùng chính `scripts/verify_week3.py` đã nâng cấp để đi qua auth/RBAC mới:

```json
{
  "admin_login_http_status": 200,
  "auth_me_http_status": 200,
  "check_in_status": "success",
  "database": "postgresql+psycopg",
  "embedding_dim": 512,
  "embedding_dtype": "float32",
  "embedding_norm": 1.0,
  "history_statuses": ["no_face", "success"],
  "invalid_token_http_status": 401,
  "model": "buffalo_s",
  "no_face_http_status": 422,
  "persisted_statuses": ["no_face", "success"],
  "profile_persisted": true,
  "rbac_forbidden_http_status": 403,
  "similarity_score": 1.0,
  "user_history_statuses": ["success"],
  "user_login_http_status": 200
}
```

Sau script, PostgreSQL trả `users|face_profiles|check_in_records|alembic_version = 0|0|0|0001`.
Database test đã được drop và container đã dừng; volume/database dev không bị reset hoặc xóa.

## Suite và quality gates cuối

Các lệnh chạy từ lockfile:

```powershell
uv sync --frozen --extra dev
$env:RUN_REAL_MODEL_TESTS='1'
$env:JWT_SECRET='week4-final-suite-secret'
uv run pytest -q -p no:cacheprovider
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
git diff --check
```

Kết quả: **78 test pass**, gồm E2E InsightFace thật; Ruff lint pass; 70 file đúng format; 3/3
import contract được giữ; `git diff --check` pass. InsightFace phát một `FutureWarning` từ dependency
`face_align.py`, không phải test failure.

## Trạng thái xác nhận của con người

Phần kỹ thuật về DI/auth và kiểm tra không copy-paste đã có test tự động và được rà soát trong quá
trình triển khai. Tuy nhiên checklist yêu cầu pair session nửa buổi và review chéo A/C là hoạt động
của con người; chưa có biên bản hoặc xác nhận từ thành viên nhóm nên vẫn để **chưa tick**. Tài liệu
này không tuyên bố hai hoạt động đó đã diễn ra.

### Cập nhật tiêu chí ngày 2026-09-22

Theo chấp thuận rõ ràng của chủ project, hai hoạt động quy trình trên được thay bằng
[technical review auth có cấu trúc](week-4-auth-technical-review.md), gồm rà soát code/dependency,
AST test, API integration và 27 test auth/DI/RBAC. Checklist đánh dấu hoàn tất theo **tiêu chí thay
thế** này; project vẫn không tuyên bố pair session nửa buổi hoặc review chéo A/C của con người đã
diễn ra.

# Technical review thay thế cho pair/review auth Tuần 4

Ngày review: 2026-09-22.

## Trạng thái và giới hạn bằng chứng

Chủ project đã chấp thuận dùng technical review có cấu trúc này để thay thế hai hoạt động quy trình
trong checklist Tuần 4: pair session về dependency injection và review chéo A/C về việc tránh
copy-paste auth.

Đây là review kỹ thuật do Codex thực hiện trên code và test thật. Tài liệu này **không tuyên bố** đã
có pair session nửa buổi, review chéo giữa hai thành viên A/C, biên bản họp hoặc chữ ký của người
khác. Checklist được đánh dấu hoàn tất theo tiêu chí thay thế do chủ project chấp thuận, không phải
do các hoạt động con người ban đầu đã diễn ra.

## Phạm vi review

- Composition root và dependency: `app/api/deps.py`.
- Login/JWT/password hashing: `app/api/v1/auth.py`, `app/core/security.py` và
  `app/services/user_service.py`.
- RBAC/ownership: `app/services/authorization.py`, các Service và router `/api/v1`.
- OpenAPI security contract và test unit/API/integration liên quan auth.
- Import contracts để bảo đảm Service không phụ thuộc FastAPI, Starlette, SQLAlchemy, Pydantic
  schema, ORM model hoặc Repository implementation.

## Kết quả review

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Điểm xác thực dùng chung | Đạt | `OAuth2PasswordBearer` → `get_current_user`; router nhận `CurrentUserDependency` |
| Decode token trong handler | Không có | AST test quét toàn bộ `app/api/v1/*.py` |
| Nguồn role cuối cùng | Đạt | JWT lấy `sub`, dependency tải lại user/role hiện hành từ Repository |
| RBAC và ownership | Đạt | Admin dependency ở biên API; ownership/scoping nằm trong Service thuần Python |
| Phân biệt 401/403/404 | Đạt | API integration bao phủ token lỗi, thiếu quyền và tài nguyên không tồn tại |
| Password | Đạt | Hash mới Argon2id có salt; PBKDF2 chỉ còn đường verify tương thích dữ liệu cũ |
| JWT validation | Đạt | Bắt buộc `sub`, `role`, `iat`, `exp`; cố định algorithm; reject malformed/sai chữ ký/hết hạn |
| OpenAPI | Đạt | OAuth2 password flow đúng token URL; chỉ operation được bảo vệ có security requirement |
| Transaction | Đạt | Dependency session commit thành công/audit domain; rollback lỗi hệ thống; luôn close |
| Boundary Service | Đạt | 3/3 import-linter contracts được giữ |

Không phát hiện lỗi mức high hoặc medium trong phạm vi review. Hai hàm cùng tên `require_admin` ở
API dependency và Service helper phục vụ hai biên khác nhau: dependency tạo route-level guard,
Service helper giữ business authorization độc lập framework. Chúng không decode JWT lặp lại và
không làm Service phụ thuộc FastAPI.

## Test đã chạy

```text
uv run pytest -q \
  tests/unit/test_security.py \
  tests/unit/test_user_service.py \
  tests/api/test_auth.py \
  tests/api/test_openapi_auth.py \
  tests/api/test_auth_rbac_integration.py \
  tests/api/test_resource_routers.py \
  -p no:cacheprovider

27 passed in 2.60s
```

Full suite sau thay đổi đạt 100 test với PostgreSQL và InsightFace thật; Ruff, format và
import-linter đều pass.

## Trade-off còn chấp nhận ở Pha 1

- Chỉ có access token; chưa có refresh-token rotation hoặc revocation store.
- JWT chưa cấu hình issuer/audience vì Pha 1 chỉ có một service phát và nhận token.
- PBKDF2 verifier tạm còn tồn tại để dữ liệu dev Tuần 3 đăng nhập được; hash mới luôn là Argon2id.
- Không thêm auth middleware song song vì sẽ decode token/lookup user hai lần và làm mờ dependency
  graph của FastAPI.

Các điểm này đã được ghi trong ADR và không phải blocker của phạm vi Pha 1. Nếu threat model, số
service hoặc yêu cầu logout/revocation thay đổi, quyết định auth cần được xem lại.

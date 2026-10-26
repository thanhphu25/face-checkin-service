# Đặc tả API — Face Check-in Service Pha 1

Đối chiếu router, schema, service và repository; cơ chế middleware cập nhật ngày 2026-10-19.
Dùng cho review nghiệp vụ và bàn giao. [OpenAPI JSON](openapi.json) chứa schema máy đọc được; tài liệu này bổ sung
quyền, lỗi nghiệp vụ và các hành vi chưa thể hiện hết trong OpenAPI.

## 1. Quy ước chung

- URL local mặc định: `http://localhost:8000`; API nghiệp vụ có tiền tố `/api/v1`.
- Swagger: `/docs`; OpenAPI runtime: `/openapi.json`.
- API được bảo vệ nhận `Authorization: Bearer <access_token>`.
- `AuthenticationMiddleware` xác minh JWT và tải user hiện hành một lần/request; dependency
  lấy user từ request và kiểm tra quyền. Không có Bearer credential thì endpoint công khai vẫn
  hoạt động. Nếu chủ động gửi Bearer token sai/hết hạn hoặc user đã xóa, middleware trả JSON
  `401` với `WWW-Authenticate: Bearer` trên mọi route, kể cả `/health`, login và check-in công khai.
- Đăng nhập dùng `application/x-www-form-urlencoded`, quản lý user dùng `application/json`,
  upload ảnh dùng `multipart/form-data` với field bắt buộc `image`.
- Upload mặc định tối đa `5 * 1024 * 1024` bytes; MIME JPEG/PNG, nội dung phải giải mã được.
- Các ID trên path và query `user_id` phải là số nguyên dương.
- Response thời gian có timezone; dữ liệu domain/repository chuẩn hóa UTC. Nên gửi query thời
  gian theo ISO 8601 có timezone, ví dụ `2026-10-11T00:00:00Z`.
- Danh sách là JSON array, không có envelope `items`/`total`. DELETE thành công trả `204`, body rỗng.
- Access token mặc định hết hạn sau 30 phút; chưa có refresh token/logout. Quyền lấy từ user hiện
  hành trong DB sau khi xác minh token.

## 2. Schema response

| Schema | Field | Kiểu / ý nghĩa |
|---|---|---|
| `UserRead` | `id`, `email`, `role`, `full_name`, `created_at` | ID dương; email; `admin`/`user`; tên; thời điểm có timezone |
| `FaceProfileRead` | `id`, `user_id`, `model_name`, `created_at` | ID profile/chủ sở hữu; model; thời điểm có timezone |
| `CheckInResult` | `id`, `user_id`, `matched_face_profile_id` | ID bản ghi; các liên kết có thể `null` |
| `CheckInResult` | `checkin_time`, `similarity_score`, `threshold` | Thời điểm; score `[-1,1]` hoặc `null`; ngưỡng `[-1,1]` |
| `CheckInResult` | `status`, `full_name` | `success`/`unmatched`/`no_face`; tên hoặc `null` |
| `TokenResponse` | `access_token`, `token_type` | Chuỗi token; `"bearer"` |

Chỉ POST check-in bổ sung `full_name` khi khớp user. GET danh sách/chi tiết check-in hiện trả
`full_name: null`, kể cả record `success`, vì chỉ ánh xạ record domain. `success` trong lịch sử
có thể có `user_id`/`matched_face_profile_id: null` nếu user/profile đã bị xóa.

## 3. Danh mục endpoint

Path có dấu `{...}` dùng đúng tên tham số trong OpenAPI.

| Method và path | Quyền | Input | Thành công | Lỗi nghiệp vụ/chính |
|---|---|---|---|---|
| `GET /health` | Công khai | Không | `200 {"status":"ok"}` | Chỉ phản ánh handler hoạt động, không kiểm tra DB/model |
| `POST /api/v1/auth/login` | Công khai | OAuth2 form `username`, `password` | `200 TokenResponse` | `401` sai credential; `422` thiếu field |
| `GET /api/v1/auth/me` | Đăng nhập | Bearer token | `200 UserRead` | `401` token thiếu/sai/hết hạn hoặc user đã xóa |
| `POST /api/v1/users` | Admin | JSON `UserCreate` | `201 UserRead` | `400` email trùng; `401`/`403`; `422` input sai |
| `GET /api/v1/users` | Admin | Không | `200 UserRead[]` | `401`/`403` |
| `GET /api/v1/users/{user_id}` | Admin hoặc chính user | ID trên path | `200 UserRead` | `401`/`403`/`404`; `422` ID sai |
| `DELETE /api/v1/users/{user_id}` | Admin | ID trên path | `204` | `401`/`403`/`404`; `422` ID sai |
| `POST /api/v1/face-profiles` | Đăng nhập | Multipart `image` | `201 FaceProfileRead` | `400` ảnh sai; `401`; `422` thiếu ảnh/không mặt/nhiều mặt/lỗi embedding |
| `GET /api/v1/face-profiles` | Đăng nhập | Query `user_id` tùy chọn | `200 FaceProfileRead[]` | `401`; `404` user lọc không tồn tại; `422` query sai |
| `DELETE /api/v1/face-profiles/{profile_id}` | Admin hoặc chủ profile | ID trên path | `204` | `401`/`403`/`404`; `422` ID sai |
| `POST /api/v1/checkins` | Công khai | Multipart `image` | `201 CheckInResult` | `400` ảnh sai; `404` unmatched; `422` thiếu ảnh/không mặt/nhiều mặt/lỗi embedding |
| `GET /api/v1/checkins` | Đăng nhập | Query `user_id`, `start`, `end`, `limit` | `200 CheckInResult[]` | `401`; `422` query sai |
| `GET /api/v1/checkins/{record_id}` | Admin hoặc user của record | ID trên path | `200 CheckInResult` | `401`/`403`/`404`; `422` ID sai |
| `DELETE /api/v1/checkins/{record_id}` | Admin | ID trên path | `204` | `401`/`403`/`404`; `422` ID sai |

Tất cả API được bảo vệ đều có thể trả `401`. User đã xác thực nhưng thiếu quyền trả `403`.
Handler truy xuất có thể tìm resource trước khi kiểm tra ownership; không bảo đảm luôn trả
`403` trước `404` cho mọi tổ hợp đầu vào. API không có PUT/PATCH trong baseline.

## 4. Đăng nhập và quản lý user

### POST `/api/v1/auth/login`

`username` chứa email; không gửi JSON với field `email`. Email chuẩn hóa bằng `strip + casefold`.
Email không tồn tại và mật khẩu sai cùng trả `401`, thông điệp chung.

### POST `/api/v1/users`

Admin tạo user; các field `email`, `password`, `full_name` bắt buộc, `role` mặc định `user`.
Email 3–255 ký tự và theo pattern email của schema; password 8–128 ký tự; tên sau trim 1–255
ký tự. Role chỉ nhận `admin` hoặc `user`.

GET user/me dùng cùng schema, không trả password/hash. GET danh sách user chưa có pagination,
sắp xếp ID tăng dần. Xóa user xóa các profile thuộc user và giữ lịch sử check-in với liên kết
đã xóa thành `null`.

## 5. Đăng ký và quản lý khuôn mặt

### POST `/api/v1/face-profiles`

Bearer token bắt buộc. Gửi một file `image`, không cần đặt `Content-Type` thủ công khi dùng
Swagger hoặc thư viện multipart vì boundary được client tạo. Ảnh phải có đúng một khuôn mặt.
API tự gắn profile vào user hiện hành; `user_id` không phải tham số của thao tác đăng ký.

Không có mặt khi **đăng ký** trả `422 NoFaceDetected` và không tạo check-in audit. Một user có
thể đăng ký nhiều profile; baseline chưa có giới hạn số profile hoặc phát hiện đăng ký trùng.

### GET `/api/v1/face-profiles`

`user_id` tùy chọn, số nguyên dương. Admin bỏ filter sẽ xem toàn bộ, đặt filter sẽ xem profile
của user đó; filter tới user không tồn tại trả `404`. User thường luôn xem profile của mình,
kể cả truyền ID của người khác: filter bị giới hạn về ID hiện hành, không trả `403` vì filter.
Danh sách sắp xếp ID tăng dần, chưa có pagination; không có profile trả `[]`.

### DELETE `/api/v1/face-profiles/{profile_id}`

Admin hoặc chủ profile được xóa; record check-in đã khớp profile đó vẫn tồn tại và
`matched_face_profile_id` thành `null`. User liên quan vẫn giữ nguyên nếu chưa bị xóa.

## 6. Điểm danh và tra cứu lịch sử

### POST `/api/v1/checkins`

API công khai cho thiết bị; không nhận ID user, hệ thống xác định danh tính từ ảnh. Sau L2
normalization, chọn profile cùng model/dimension có cosine similarity cao nhất. Điểm bằng ngưỡng
được chấp nhận. Giá trị ngưỡng mặc định `0.40`, có thể đổi bằng cấu hình.

Hai nhánh thất bại nghiệp vụ **vẫn ghi DB**, nhưng response là lỗi thay vì `CheckInResult`:

| Nhánh | HTTP | Bản ghi lưu | Field thêm trong lỗi |
|---|---|---|---|
| Không có profile phù hợp hoặc điểm dưới ngưỡng | `404` | `status=unmatched`, liên kết user/profile `null` | `record_id`, `best_score` (có thể `null`) |
| Không có mặt trong ảnh giải mã được | `422` | `status=no_face`, score/liên kết `null` | `record_id` |

Ảnh rỗng, quá dung lượng, MIME sai hoặc không giải mã được trả `400`; nhiều mặt/lỗi embedding
trả `422`. Các nhánh này không tạo bản ghi audit. Mỗi request success tạo một record mới;
baseline không chống gửi lặp và không có idempotency key.

### GET `/api/v1/checkins`

| Query | Bắt buộc | Quy tắc hiện tại |
|---|---|---|
| `user_id` | Không | Số nguyên dương; admin được lọc, user thường luôn bị scope về chính mình |
| `start` | Không | Datetime ISO 8601; lọc `checkin_time >= start` |
| `end` | Không | Datetime ISO 8601; lọc `checkin_time < end` |
| `limit` | Không | Số nguyên 1–200, mặc định 50 |

Khoảng thời gian là `[start, end)`. Route hiện khai báo trực tiếp các query, chưa
kiểm tra `start < end` hay bắt buộc timezone ở query. Khoảng đảo
chiều hợp lệ về định dạng trả danh sách rỗng. Đây là giới hạn contract hiện tại.

Kết quả mới nhất trước (`checkin_time DESC`, rồi `id DESC`); chưa có offset/cursor. Admin không
lọc thấy cả `unmatched`/`no_face`; user thường chỉ thấy record có ID user của mình. Admin lọc một
user không tồn tại nhận `[]` ở endpoint này.

### GET/DELETE `/api/v1/checkins/{record_id}`

GET cho admin hoặc user được gắn vào record. Record không có user (unmatched/no_face hoặc user
đã xóa) chỉ admin được đọc. DELETE chỉ admin, xóa vật lý record và trả `204`; gọi lại sau xóa
trả `404`.

## 7. Lỗi và giới hạn contract

Lỗi domain có `detail` và `error`; lỗi điểm danh có thể thêm `record_id`/`best_score`.
Lỗi validation FastAPI dùng `detail` dạng array chứa `loc`, `msg`, `type` và có thể thêm field
khác. Lỗi thiếu Bearer token do framework xử lý có thể chỉ có `detail`, không có `error`.
Không nên giả định mọi response lỗi cùng một schema. `401` có header `WWW-Authenticate: Bearer`.

| HTTP | Các tình huống tiêu biểu |
|---|---|
| `400` | `EmailAlreadyExists`, `InvalidEmail`, `InvalidImage` |
| `401` | Thiếu/sai/hết hạn token, user trong token không còn tồn tại, đăng nhập sai |
| `403` | Thiếu vai trò admin hoặc không sở hữu tài nguyên |
| `404` | User/profile/record không tồn tại; riêng POST check-in là `UnmatchedFace` có audit |
| `422` | Validation input; `NoFaceDetected`, `MultipleFacesDetected`, `FaceEmbeddingFailed` |

OpenAPI tự sinh hiện mô tả response thành công và validation `422`, chưa khai báo đầy đủ schema
lỗi domain cho từng route. Client cần đọc bảng lỗi ở tài liệu này. Việc đồng bộ error contract
vào OpenAPI là một hạng mục có thể cải tiến sau review.

## 8. Kiểm thử thủ công trên Swagger

Dựng stack và seed theo [hướng dẫn vận hành](running.md#4-chạy-từ-máy-sạch-bằng-docker-compose).
Có thể dùng seed chỉ tài khoản với `--skip-face-profile`, rồi đăng ký mặt trực tiếp. Mật khẩu
lấy từ `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD` của người chạy, không có mật khẩu demo cố định.

Mở http://localhost:8000/docs, dùng **Try it out** và **Execute**. Bấm **Authorize**, điền email
vào `username`, mật khẩu vào `password`; để trống client ID/secret. Gọi API login trực tiếp chỉ
trả token, không tự Authorize Swagger. Khi đổi vai trò, Logout trong Authorize rồi đăng nhập lại.
Logout tại Swagger chỉ bỏ credential ở trình duyệt, không thu hồi JWT trên server.

Chuẩn bị ảnh một mặt để đăng ký/điểm danh, ảnh người chưa đăng ký, ảnh không mặt, ảnh nhiều mặt
và một file sai định dạng. Ảnh khác người không bảo đảm luôn unmatched: kết quả phụ thuộc score.
Ghi lại ID thực tế từ response, không giả định ID bắt đầu từ 1.

| Bước | Thao tác | Kết quả đối chiếu |
|---|---|---|
| 1 | Gọi health, login, auth/me | Health 200; login hợp lệ có JWT; me không có token trả 401 |
| 2 | Admin tạo, liệt kê và đọc user | 201/200; thử cùng thao tác tạo bằng user thường nhận 403 |
| 3 | User đăng ký ảnh một mặt | 201; profile thuộc user hiện hành, không trả embedding |
| 4 | Gửi lại ảnh đó tới POST checkins công khai | 201 khi đạt ngưỡng; lưu ID record và user khớp |
| 5 | Gửi ảnh dưới ngưỡng, ảnh không mặt, file sai và ảnh nhiều mặt | Unmatched 404 có record_id; no_face 422 có record_id; file sai/nhiều mặt không tạo record |
| 6 | User/admin xem profile và lịch sử, thử bộ lọc | User chỉ thấy dữ liệu mình; admin thấy cả unmatched/no_face |
| 7 | User khác đọc record hoặc xóa profile của người khác | 403 với tài nguyên tồn tại; thiếu token trả 401 |
| 8 | Admin hoặc chủ profile xóa profile; admin xóa user/check-in thử nghiệm | 204; sau xóa profile/user, lịch sử còn với liên kết đã xóa thành null |

Khi dọn dữ liệu, chỉ xóa các ID tạo cho lần thử; dọn record trước, rồi profile/user. Không xóa
user đang dùng để test khi vẫn cần token của user đó. Lệnh xóa volume trong hướng dẫn vận hành chỉ dành cho
project cách ly hoặc khi chủ động bỏ toàn bộ dữ liệu.

## 9. Nguồn đối chiếu

- [Router](../app/api/v1/), [schema DTO](../app/schemas/), [Service](../app/services/).
- [Upload](../app/api/uploads.py), [ánh xạ lỗi](../app/api/errors.py),
  [middleware](../app/api/authentication.py), [dependency](../app/api/deps.py).
- [OpenAPI JSON](openapi.json), [quyết định JWT/RBAC](architecture.md#auth).

# Hướng dẫn kiểm thử từng API bằng Swagger UI

Tài liệu này hướng dẫn kiểm thử thủ công toàn bộ API của Face Check-in Service trên
Swagger UI. Các bước đi theo một luồng hoàn chỉnh: kiểm tra hệ thống, đăng nhập, quản lý
user, đăng ký khuôn mặt, check-in, xem lịch sử và dọn dữ liệu thử nghiệm.

## 1. Điều kiện trước khi test

### 1.1. Kiểm tra stack Docker

Tại thư mục project, chạy:

```powershell
docker compose up -d --wait
docker compose ps -a
```

Trạng thái đúng:

| Service | Trạng thái mong đợi |
|---|---|
| `app` | `healthy` |
| `postgres` | `healthy` |
| `redis` | `healthy` |
| `migrate` | `Exited (0)` |

Kiểm tra nhanh:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Kết quả phải chứa `status: ok`.

### 1.2. Tạo tài khoản mẫu

Nếu database chưa có tài khoản mẫu, chạy lệnh sau. Cách này dùng image Docker đã build,
không cần cài dependency Python trên máy host:

```powershell
$env:SEED_ADMIN_PASSWORD = "AdminDemo123!"
$env:SEED_USER_PASSWORD = "UserDemo123!"

docker compose run --rm `
  -e SEED_ADMIN_PASSWORD `
  -e SEED_USER_PASSWORD `
  -v "${PWD}/scripts:/app/scripts:ro" `
  app python -m scripts.seed --skip-face-profile
```

Hai tài khoản dùng trong tài liệu:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Admin | `admin.sample@example.test` | `AdminDemo123!` |
| User | `user.sample@example.test` | `UserDemo123!` |

Script seed chạy lặp lại không tạo bản ghi trùng. Tùy chọn `--skip-face-profile` chỉ tạo
tài khoản và lịch sử mẫu; khuôn mặt sẽ được đăng ký trực tiếp qua Swagger ở phần sau.

### 1.3. Chuẩn bị ảnh thử nghiệm

Nên chuẩn bị:

- `face-user.jpg`: ảnh rõ, chính diện, chỉ có một khuôn mặt; dùng để đăng ký và check-in.
- `face-other.jpg`: khuôn mặt khác để thử trường hợp không khớp.
- `no-face.jpg`: ảnh không có khuôn mặt.
- `multiple-faces.jpg`: ảnh có từ hai khuôn mặt trở lên.
- `invalid.txt`: file văn bản để thử định dạng không hợp lệ.

Ảnh phải là JPEG hoặc PNG và không vượt quá `MAX_UPLOAD_MB` (mặc định 5 MB).

## 2. Mở Swagger và xác thực

Mở <http://localhost:8000/docs>.

Với mỗi API: mở endpoint → **Try it out** → điền dữ liệu → **Execute** → đối chiếu
`Server response`, đặc biệt là `Code` và `Response body`.

### Đăng nhập cho API có biểu tượng ổ khóa

1. Bấm **Authorize** ở đầu trang.
2. Điền email vào `username` và mật khẩu vào `password`.
3. Để trống `client_id` và `client_secret`.
4. Bấm **Authorize**, sau đó bấm **Close**.

Swagger sẽ tự gắn header `Authorization: Bearer ...` vào các API được bảo vệ.

> Gọi trực tiếp `POST /api/v1/auth/login` chỉ kiểm tra response token. Swagger không tự
> lưu token từ response đó. Muốn gọi API được bảo vệ, vẫn phải dùng nút **Authorize**.

Khi cần đổi giữa admin và user, bấm **Authorize** → **Logout**, rồi đăng nhập lại.

Ghi lại các ID trả về trong quá trình test:

```text
USER_ID=<id của user mẫu>
NEW_USER_ID=<id của user tạo để test>
PROFILE_ID=<id của face profile>
CHECKIN_ID=<id của lần check-in thành công>
```

## 3. System API

### `GET /health` — kiểm tra ứng dụng

Không cần đăng nhập.

1. Mở nhóm **system** → `GET /health`.
2. Bấm **Try it out** → **Execute**.

Kết quả mong đợi: HTTP `200`.

```json
{
  "status": "ok"
}
```

## 4. Auth API

### 4.1. `POST /api/v1/auth/login` — đăng nhập

Không cần đăng nhập trước.

1. Mở nhóm **auth** → `POST /api/v1/auth/login` → **Try it out**.
2. Điền:
   - `username`: `user.sample@example.test`
   - `password`: `UserDemo123!`
   - `grant_type`: để trống hoặc dùng `password`
   - `scope`, `client_id`, `client_secret`: để trống
3. Bấm **Execute**.

Kết quả mong đợi: HTTP `200`.

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer"
}
```

Ca lỗi nên thử:

| Dữ liệu | Kết quả mong đợi |
|---|---|
| Sai mật khẩu | `401`, `AuthenticationFailed` |
| Email không tồn tại | `401`, cùng thông báo `Incorrect email or password` |

Không nhập email vào cả ô `username` và `password`.

### 4.2. `GET /api/v1/auth/me` — tài khoản hiện tại

1. Dùng nút **Authorize** để đăng nhập bằng user mẫu.
2. Mở `GET /api/v1/auth/me` → **Execute**.

Kết quả mong đợi: HTTP `200`; response có `id`, `email`, `role`, `full_name`,
`created_at` và không có password/hash. Ghi lại `id` làm `USER_ID`.

Ca lỗi: **Logout** rồi gọi lại endpoint. Kết quả phải là HTTP `401` với
`detail: Not authenticated`.

## 5. Users API

### Quyền truy cập

| Endpoint | Admin | User thường |
|---|---:|---:|
| `POST /users` | Có | Không |
| `GET /users` | Có | Không |
| `GET /users/{id}` | Mọi user | Chỉ chính mình |
| `DELETE /users/{id}` | Có | Không |

### 5.1. `POST /api/v1/users` — tạo user

Đăng nhập bằng admin qua nút **Authorize**, sau đó gửi body:

```json
{
  "email": "swagger.test@example.test",
  "password": "SwaggerTest123!",
  "role": "user",
  "full_name": "Swagger Test User"
}
```

Kết quả mong đợi: HTTP `201`. Ghi `id` trả về làm `NEW_USER_ID`. Response không được
chứa password hoặc password hash.

| Ca kiểm thử | Kết quả mong đợi |
|---|---|
| Gửi lại cùng email | `400`, `EmailAlreadyExists` |
| Password ngắn hơn 8 ký tự | `422` |
| Email sai định dạng | `422` |
| Đăng nhập user thường rồi tạo user | `403`, `PermissionDenied` |
| Không đăng nhập | `401` |

### 5.2. `GET /api/v1/users` — liệt kê user

1. Đăng nhập bằng admin và gọi API.
2. Kết quả `200` phải có admin mẫu, user mẫu và user vừa tạo.
3. Đăng nhập user thường rồi gọi lại; kết quả phải là `403`.

### 5.3. `GET /api/v1/users/{user_id}` — xem một user

| Người gọi | `user_id` | Kết quả mong đợi |
|---|---|---|
| Admin | ID bất kỳ tồn tại | `200` |
| User mẫu | `USER_ID` của chính mình | `200` |
| User mẫu | `NEW_USER_ID` của người khác | `403` |
| Admin | ID không tồn tại, ví dụ `999999` | `404`, `UserNotFound` |
| Chưa đăng nhập | ID bất kỳ | `401` |

### 5.4. `DELETE /api/v1/users/{user_id}` — xóa user

Để tránh ảnh hưởng bước sau, chưa xóa user mẫu. Chỉ xóa `NEW_USER_ID` ở phần dọn dữ
liệu cuối tài liệu.

- Admin + ID tồn tại: HTTP `204`, body rỗng.
- User thường + ID tồn tại: HTTP `403`.
- Admin + ID không tồn tại: HTTP `404`, `UserNotFound`.

## 6. Face Profiles API

### 6.1. `POST /api/v1/face-profiles` — đăng ký khuôn mặt

1. Đăng nhập bằng `user.sample@example.test`.
2. Mở endpoint → **Try it out**.
3. Ở trường `image`, chọn `face-user.jpg` → **Execute**.

Lần đầu có thể lâu hơn vì model InsightFace cần được tải hoặc khởi tạo.

Kết quả mong đợi: HTTP `201`.

```json
{
  "id": 1,
  "user_id": 2,
  "model_name": "buffalo_s",
  "created_at": "<thời gian>"
}
```

Ghi `id` làm `PROFILE_ID`. `user_id` phải bằng tài khoản đang đăng nhập. API không nhận
`user_id` từ client, nên user không thể đăng ký khuôn mặt hộ người khác. Response không
được trả embedding sinh trắc học.

| File/điều kiện | Kết quả mong đợi |
|---|---|
| Không đăng nhập + ảnh hợp lệ | `401` |
| `invalid.txt` | `400`, `InvalidImage` |
| `no-face.jpg` | `422`, `NoFaceDetected` |
| `multiple-faces.jpg` | `422`, `MultipleFacesDetected` |
| JPEG/PNG lớn hơn giới hạn | `400`, `InvalidImage` |

### 6.2. `GET /api/v1/face-profiles` — liệt kê profile

Với user mẫu:

- Để trống `user_id`: response `200` chỉ chứa profile của chính user.
- Nhập ID user khác: service vẫn giới hạn kết quả về user hiện tại.

Với admin:

- Để trống `user_id`: xem tất cả profile.
- Nhập `USER_ID`: lọc profile theo user đó.
- Nhập ID không tồn tại: `404`, `UserNotFound`.

### 6.3. `DELETE /api/v1/face-profiles/{profile_id}` — xóa profile

Chủ sở hữu profile hoặc admin được xóa và nhận HTTP `204`. User khác phải nhận `403`;
ID không tồn tại phải nhận `404`, `FaceProfileNotFound`.

Giữ lại `PROFILE_ID` đến khi hoàn thành phần check-in; nếu xóa sớm, ảnh sẽ không còn
profile để so khớp.

## 7. Check-ins API

### 7.1. `POST /api/v1/checkins` — chấm công

Endpoint này công khai, không yêu cầu đăng nhập.

#### Ca thành công

Upload đúng `face-user.jpg` đã đăng ký. Kết quả mong đợi: HTTP `201`.

```json
{
  "id": 1,
  "user_id": 2,
  "matched_face_profile_id": 1,
  "checkin_time": "<thời gian>",
  "similarity_score": 0.9,
  "threshold": 0.4,
  "status": "success",
  "full_name": "User Mau"
}
```

`similarity_score` thay đổi theo ảnh nhưng phải lớn hơn hoặc bằng `threshold`. Ghi `id`
làm `CHECKIN_ID`.

#### Ca không khớp

Upload `face-other.jpg`. Kết quả mong đợi: HTTP `404`, `error: UnmatchedFace`, kèm
`record_id` và `best_score`. Dù response là `404`, hệ thống vẫn ghi record trạng thái
`unmatched` để audit.

#### Ca không có khuôn mặt

Upload `no-face.jpg`. Kết quả mong đợi: HTTP `422`, `error: NoFaceDetected`, kèm
`record_id`. Hệ thống vẫn ghi record trạng thái `no_face`.

#### Ca file không hợp lệ

Upload `invalid.txt`. Kết quả mong đợi: HTTP `400`, `error: InvalidImage`. File bị từ
chối trước inference.

### 7.2. `GET /api/v1/checkins` — xem lịch sử

| Tham số | Ý nghĩa |
|---|---|
| `user_id` | Lọc theo user; admin mới được chọn user tùy ý |
| `start` | ISO 8601, ví dụ `2026-09-22T00:00:00Z` |
| `end` | Thời điểm kết thúc; phải sau `start` |
| `limit` | Từ 1 đến 200; mặc định 50 |

Với user mẫu:

- Để trống `user_id`: chỉ thấy lịch sử `success` thuộc user đó.
- Nhập ID user khác: service vẫn giới hạn dữ liệu về user hiện tại.
- Không thấy `unmatched`/`no_face` vì các record đó không thuộc user nào.

Với admin:

- Để trống `user_id`: thấy tất cả `success`, `unmatched`, `no_face`.
- Điền `USER_ID`: chỉ thấy record của user đó.
- Dùng `start`, `end`, `limit` để kiểm tra bộ lọc.

Kết quả hợp lệ: HTTP `200`, danh sách sắp xếp mới nhất trước.

### 7.3. `GET /api/v1/checkins/{record_id}` — xem một record

| Người gọi | Record | Kết quả mong đợi |
|---|---|---|
| User mẫu | `CHECKIN_ID` thuộc user | `200` |
| User khác | `CHECKIN_ID` | `403` |
| Admin | Record bất kỳ | `200` |
| Admin | ID không tồn tại | `404`, `CheckInNotFound` |
| Chưa đăng nhập | Record bất kỳ | `401` |

Record `unmatched` và `no_face` không có owner, nên chỉ admin đọc trực tiếp được.

### 7.4. `DELETE /api/v1/checkins/{record_id}` — xóa record

Chỉ admin được phép xóa:

- Admin + ID tồn tại: HTTP `204`, body rỗng.
- User thường + ID tồn tại: HTTP `403`.
- Admin + ID không tồn tại: HTTP `404`, `CheckInNotFound`.

Giữ `CHECKIN_ID` đến phần dọn dữ liệu để kiểm tra đủ GET trước DELETE.

## 8. Dọn dữ liệu sau khi test

Đăng nhập bằng admin và thực hiện theo thứ tự:

1. `DELETE /api/v1/checkins/{CHECKIN_ID}` → `204`.
2. `DELETE /api/v1/face-profiles/{PROFILE_ID}` → `204`.
3. `DELETE /api/v1/users/{NEW_USER_ID}` → `204`.

Không xóa admin mẫu trước khi hoàn tất thao tác quản trị.

Muốn xóa toàn bộ database demo và model cache của riêng Compose project:

```powershell
docker compose down -v
```

Lệnh trên xóa dữ liệu. Chỉ dùng khi chắc chắn không cần giữ database hiện tại.

## 9. Cách đọc mã phản hồi

| HTTP code | Ý nghĩa trong project |
|---:|---|
| `200` | Đọc/đăng nhập thành công |
| `201` | Tạo user, profile hoặc check-in thành công |
| `204` | Xóa thành công, không có response body |
| `400` | File/dữ liệu nghiệp vụ không hợp lệ hoặc email trùng |
| `401` | Chưa đăng nhập, token sai/hết hạn hoặc sai thông tin đăng nhập |
| `403` | Đã đăng nhập nhưng không đủ quyền/không sở hữu tài nguyên |
| `404` | Không tìm thấy tài nguyên hoặc khuôn mặt không khớp |
| `422` | Schema lỗi, không thấy mặt, nhiều mặt hoặc embedding lỗi |

## 10. Checklist hoàn tất

- [ ] `/health` trả `200` và `status: ok`.
- [ ] Login đúng trả JWT; login sai trả `401`.
- [ ] `/auth/me` trả đúng user và không lộ password hash.
- [ ] Admin tạo/liệt kê/xóa user được; user thường nhận `403`.
- [ ] User chỉ xem được chính mình.
- [ ] Đăng ký ảnh một mặt trả `201`; response không lộ embedding.
- [ ] Ảnh sai loại, không mặt và nhiều mặt trả đúng lỗi.
- [ ] Ảnh đã đăng ký check-in thành công.
- [ ] Ảnh khác trả `UnmatchedFace` và vẫn sinh `record_id`.
- [ ] User chỉ xem lịch sử của mình; admin xem được toàn bộ.
- [ ] Chỉ admin xóa được check-in record.

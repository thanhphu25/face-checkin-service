# Đề xuất hệ thống & Kế hoạch 8 tuần — Đồ án Backend (nhóm 3 người)

## ⚠️ 0. Lưu ý quan trọng: Pha 1 sẽ bị "đổi chủ" ở Pha 2

Bản kế hoạch gốc bên dưới giả định **cùng một nhóm** đi từ Pha 1 sang Pha 2. Nếu quy trình thực tế là **các nhóm tráo hệ thống cho nhau sau Pha 1**, có 3 khác biệt bắt buộc phải xử lý — nếu không xử lý thì mục 7 (timeline) và mục 10 (README) bên dưới sẽ **thiếu**, không phải chỉ cần thêm việc:

1. **Pha 1 phải "đọc được bởi người lạ", không chỉ chạy được với nhóm mình.** Code, README, ADR phải đủ để một đội khác — không hỏi lại được tác giả gốc — hiểu và chạy trong vài giờ, không phải vài ngày.
2. **Rủi ro khác stack công nghệ.** Đề bài ghi "ngôn ngữ không cố định", nghĩa là nhóm nhận hệ thống của bạn có thể không biết Python/FastAPI. Nên hỏi rõ giảng viên: việc tráo đổi có giới hạn trong cùng stack không? Nếu không chắc, ưu tiên chọn stack phổ biến, tránh pattern lạ, đặt tên file/thư mục theo quy ước chuẩn (không viết tắt riêng của nhóm) để giảm chi phí onboarding cho bất kỳ ai.
3. **Cần một "khoảng đệm bàn giao"** giữa Pha 1 và Pha 2 mà bản kế hoạch gốc chưa có: thời gian để nhóm mới đọc hiểu, chạy thử, và **tự đo lại baseline** trên hệ thống họ vừa nhận (không nên chỉ tin số liệu do nhóm cũ để lại, vì môi trường/thao tác đo có thể khác).

Phần **7 (timeline)**, **8**, **9** và **10** bên dưới đã được cập nhật để đưa các điểm này vào — xem đánh dấu **[Bàn giao]**.

---

## 1. Chọn nghiệp vụ

Đề bài cho phép chọn nghiệp vụ tự do. Ba lựa chọn dưới đây đều đáp ứng đủ yêu cầu Pha 1, khác nhau ở độ rủi ro và "chất liệu" cho Pha 2.

| Nghiệp vụ | Độ khó Pha 1 | Chất liệu tốt cho Pha 2 | Ghi chú |
|---|---|---|---|
| **Check-in/điểm danh bằng khuôn mặt** (đề xuất chính) | Trung bình-cao | Rất tốt: suy luận CV nặng CPU → tối ưu hiệu năng, cache embedding, batch inference | Tận dụng được kinh nghiệm có sẵn về face detection/embedding/ANN search |
| Đặt vé rạp phim | Trung bình | Tốt: giữ ghế đồng thời (concurrency), idempotency, cache lịch chiếu | An toàn, ít phụ thuộc mô hình ML, dễ kiểm soát tiến độ |
| Bãi đỗ xe thông minh | Thấp-trung bình | Khá: cập nhật slot thời gian thực, rate limiting, hàng đợi | Đơn giản nhất, phù hợp nếu muốn giảm rủi ro tối đa |

**Khuyến nghị:** chọn **hệ thống Check-in bằng khuôn mặt**, vì:
- Yêu cầu đề bài bắt buộc kiểm thử tải trên **Kaggle CPU** — đây đúng là môi trường quen thuộc để benchmark pipeline nhận diện khuôn mặt (detection/embedding/ANN search vốn nặng CPU), nên nhóm có sẵn kinh nghiệm viết script benchmark kiểu Kaggle.
- Pha 2 (tối ưu hiệu năng) sẽ có nhiều câu chuyện thật để kể: tối ưu suy luận model (ONNX/quantization), cache embedding, batch hóa request, so sánh ANN index (FAISS/HNSW) — đúng thế mạnh sẵn có.
- Vẫn giữ được các entity CRUD chuẩn (User, FaceProfile, CheckInRecord) nên không lệch khỏi yêu cầu "chỉ cần chức năng cơ bản" ở Pha 1.

Nếu muốn giảm rủi ro (vì phải làm ML + kiến trúc + Docker + auth trong 8 tuần với 3 người), **đặt vé rạp phim** là phương án dự phòng an toàn — kiến trúc bên dưới áp dụng y hệt cho cả 3 lựa chọn, chỉ khác entity nghiệp vụ.

Phần còn lại của tài liệu minh họa theo phương án chính (Face Check-in), có ghi chú tương đương cho phương án dự phòng.

---

## 2. Kiến trúc tổng thể (Pha 1)

```
Client (Swagger UI / Postman)
        │  JSON/REST
        ▼
┌─────────────────────┐
│   API Layer          │  FastAPI routers, Pydantic schemas,
│   (framework-aware)  │  auth dependency, exception handlers
└──────────┬───────────┘
           │  gọi qua interface (không import framework)
           ▼
┌─────────────────────┐
│   Service Layer      │  Business logic thuần Python (use-case
│   (framework-free)   │  classes), KHÔNG import FastAPI/SQLAlchemy
└──────────┬───────────┘
           │  gọi qua Repository interface (ABC)
           ▼
┌─────────────────────┐
│  Repository/DAO      │  SQLAlchemy ORM implementation,
│  Layer               │  chuyển đổi Model ↔ Domain object
└──────────┬───────────┘
           ▼
      PostgreSQL / SQLite (dev)
```

**Nguyên tắc bắt buộc của đề bài mà kiến trúc này đảm bảo:**
- Tầng Service chỉ phụ thuộc **interface/abstract class** của Repository (Dependency Inversion), không phụ thuộc SQLAlchemy trực tiếp → tầng nghiệp vụ không import framework web/DB.
- Có thể chứng minh điều này tự động (điểm cộng, xem mục 8) bằng công cụ `import-linter` (Python) hoặc test kiểm tra import.

**Stack đề xuất** (dựa trên kinh nghiệm sẵn có với Python/FastAPI):
- **Framework**: FastAPI (tự sinh OpenAPI/Swagger miễn phí tại `/docs`)
- **ORM**: SQLAlchemy 2.0 + Alembic (migration)
- **DB**: PostgreSQL (prod/docker-compose), SQLite (test nhanh)
- **Auth**: JWT (python-jose hoặc pyjwt) + OAuth2PasswordBearer
- **Face embedding** (nếu chọn phương án chính): model nhẹ chạy CPU (vd. buffalo_s của InsightFace, hoặc MobileFaceNet) để không cần GPU khi benchmark trên Kaggle CPU

---

## 3. Thiết kế API tối thiểu

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| POST | `/auth/login` | Không | Đăng nhập, trả JWT |
| GET | `/auth/me` | **Có** | Lấy thông tin user hiện tại (endpoint GET có auth) |
| POST | `/users` | Có (admin) | Tạo nhân viên mới |
| GET | `/users/{id}` | Có | Xem thông tin nhân viên |
| POST | `/face-profiles` | **Có** | Đăng ký khuôn mặt (upload ảnh, sinh embedding) — endpoint POST có auth |
| DELETE | `/face-profiles/{id}` | Có | Xóa hồ sơ khuôn mặt |
| POST | `/checkins` | Tùy chọn | Check-in bằng ảnh khuôn mặt → so khớp embedding |
| GET | `/checkins` | Có | Lịch sử check-in (filter theo user/ngày) |
| DELETE | `/checkins/{id}` | Có (admin) | Xóa bản ghi check-in |

Đủ tối thiểu POST/GET/DELETE, và có ít nhất 1 GET + 1 POST yêu cầu xác thực như đề bài yêu cầu.

*(Phương án đặt vé rạp phim: thay `face-profiles`/`checkins` bằng `movies`, `showtimes`, `bookings` — cấu trúc auth/layer giữ nguyên.)*

---

## 4. Bảo mật

- Đăng nhập bằng JWT, hash mật khẩu bằng bcrypt/argon2.
- Xác thực triển khai **một lần** dưới dạng FastAPI dependency (`Depends(get_current_user)`) gắn ở cấp router, **không copy code** vào từng handler — tương đương middleware/interceptor theo tinh thần đề bài. Nếu muốn bám sát chữ "middleware" hơn, có thể bổ sung một Starlette `BaseHTTPMiddleware` chặn các path `/protected/*` để chấm điểm chắc chắn không bị trừ.
- Phân quyền cơ bản (role `admin`/`user`) — vừa đáp ứng yêu cầu, vừa là chất liệu tốt cho Pha 2 (authorization là một quality attribute).

---

## 5. Triển khai & Docker

- `Dockerfile` multi-stage (build → runtime nhẹ, image nhỏ).
- `docker-compose.yml`: app + PostgreSQL (+ Redis, chuẩn bị sẵn cho Pha 2 caching).
- README.md gồm: sơ đồ kiến trúc (như mục 2), đặc tả API (link Swagger + bảng endpoint), hướng dẫn chạy (`docker compose up`), quyết định thiết kế quan trọng (ADR ngắn gọn).

---

## 6. Kiểm thử tải trên Kaggle CPU

Vì Kaggle notebook không chạy Docker, cách thực tế nhất:
1. Cài đặt dependencies trực tiếp trong notebook, chạy `uvicorn` app ở background process (hoặc dùng `nest_asyncio` + `TestClient`/`httpx.AsyncClient` để gọi trực tiếp trong process, tránh network overhead không cần thiết).
2. Viết script benchmark (locust, hoặc script tự viết với `asyncio`/`httpx` bắn concurrent requests) đo: latency p50/p95/p99, throughput (req/s), CPU usage theo số lượng concurrent users.
3. Lưu kết quả thành bảng/biểu đồ cố định — đây sẽ là **baseline** để so sánh trước/sau ở Pha 2. Vì đề bài yêu cầu đánh giá trên **cùng một cấu hình phần cứng**, cần chạy đúng loại Kaggle CPU instance cho cả hai lần đo (Pha 1 baseline và Pha 2 sau tối ưu).

---

## 7. Kế hoạch 8 tuần — nhóm 3 người

| Tuần | Nội dung chính | Mốc kiểm tra |
|---|---|---|
| 1 | Chốt nghiệp vụ, đặc tả use-case, thiết kế DB schema, khung repo (3 tầng), setup GitHub Projects/board | Có schema + kiến trúc doc đầu tiên |
| 2 | Data layer: models SQLAlchemy, Alembic migration, Repository interface + implementation cho entity chính | CRUD qua repository chạy được (test thủ công) |
| 3 | Service layer (business logic thuần), API layer (routers, Pydantic schema), Swagger tự sinh | Toàn bộ endpoint CRUD cơ bản chạy qua `/docs` |
| 4 | Auth JWT + dependency toàn cục, RBAC, unit test cho service layer (mock repository) | 1 GET + 1 POST có auth hoạt động, test pass |
| 5 | Docker hóa, docker-compose, README (kiến trúc + đặc tả), integration test | `docker compose up` chạy được từ máy sạch |
| 6 | Viết script load test, chạy baseline trên Kaggle CPU, ghi nhận số liệu. **[Bàn giao]** Dành 1–2 buổi cuối tuần để hoàn thiện checklist bàn giao (mục 11): README onboarding, seed data, ADR, xuất OpenAPI spec, tag release `v1.0-phase1` | **Nộp/Bàn giao Pha 1**: repo gắn tag + README + báo cáo benchmark baseline. Nhận hệ thống từ nhóm khác |
| 7 | **[Bàn giao]** 1–2 ngày đầu tuần: onboarding sprint trên hệ thống mới nhận — chạy thử, đọc kiến trúc, **tự đo lại baseline** trên đúng cấu hình Kaggle CPU để đối chiếu với số liệu nhóm cũ để lại. Sau đó: phân tích điểm nghẽn → chọn 2–3 cải tiến phù hợp (mục 9), triển khai | Baseline được xác nhận lại (số liệu khớp/giải thích được chênh lệch); cải tiến chạy được, chưa cần đo lại |
| 8 | Chạy lại benchmark **cùng cấu hình Kaggle CPU** trên hệ thống đã tiếp nhận, so sánh trước/sau, viết báo cáo lý giải nguyên nhân cải thiện, hoàn thiện slide/demo | **Nộp Pha 2**: báo cáo so sánh + code + slide, dựa trên hệ thống nhận từ nhóm khác |

### Phân công gợi ý (xoay vòng khi cần)
- **Thành viên A** — Data/Repository layer, DB schema, migration, script load test.
- **Thành viên B** — API layer, Auth/bảo mật, Docker/CI.
- **Thành viên C** — Service/business logic, (nếu chọn face check-in: tích hợp embedding model), tài liệu OpenAPI, dẫn dắt phần tối ưu Pha 2.

Nên pair lại ở tuần 1 (thiết kế) và tuần 4 (auth — phần dễ vi phạm yêu cầu "không viết lặp") để tránh lệch chuẩn kiến trúc giữa 3 người.

---

## 8. Các điểm có thể làm "vượt yêu cầu" (ít công sức, nhiều điểm cộng)

- `import-linter` (hoặc test tự viết) chứng minh tầng Service không import framework/DB — biến yêu cầu ngầm thành bằng chứng tự động.
- GitHub Actions CI: lint + test + build Docker image mỗi lần push.
- Versioning API (`/api/v1/...`).
- Structured logging (JSON log) + một endpoint `/metrics` kiểu Prometheus — vừa chuyên nghiệp, vừa là dữ liệu đầu vào tốt cho phần đo lường Pha 2.
- Idempotency key cho các POST quan trọng (vd. check-in/booking) để tránh double-submit khi tải cao — vừa là tính năng tốt, vừa là câu chuyện chất lượng cho Pha 2 (consistency).

---

## 9. Gợi ý cụ thể cho Pha 2 (map theo quality attribute)

| Quality attribute | Cải tiến đề xuất | Cách đo trước/sau |
|---|---|---|
| Performance/Throughput | Cache Redis cho GET đọc nhiều, dùng async DB driver (`asyncpg`), connection pool tuning | So sánh p95 latency & req/s cùng kịch bản tải trên Kaggle CPU |
| Hiệu năng suy luận (nếu chọn face check-in) | Batch inference, xuất model sang ONNX + quantization int8, cache embedding đã trích xuất | So sánh CPU time/request, throughput suy luận |
| Scalability | Chạy nhiều worker (Gunicorn + Uvicorn workers), so sánh 1 vs N worker cùng CPU | Throughput/CPU-core, độ trễ khi tăng concurrency |
| Reliability/Resilience | Retry + backoff, circuit breaker cho dependency ngoài (nếu có) | Tỷ lệ lỗi khi giả lập dependency chậm/lỗi |
| Security | Rate limiting chống brute-force login, rotate refresh token | Số request bị chặn, thời gian phản hồi khi bị tấn công giả lập |
| Maintainability | Enforce boundary bằng `import-linter`, tăng test coverage | Coverage % trước/sau, số vi phạm layering bị phát hiện |

Chỉ cần chọn **2–3 cải tiến** thực sự triển khai và đo được — đề bài không yêu cầu làm hết, nhưng yêu cầu **lý giải rõ vì sao chọn** (dựa trên số liệu baseline Pha 1) và **đo lại trên đúng cấu hình cũ**.

---

## 10. README.md nên có gì (tối thiểu)

Viết README như thể **người đọc không quen ai trong nhóm và không hỏi lại được** — vì sau Pha 1 đúng là như vậy.

1. Mô tả nghiệp vụ & phạm vi (scope Pha 1 vs Pha 2)
2. Sơ đồ kiến trúc (như mục 2) + giải thích từng tầng
3. Bảng đặc tả endpoint + link Swagger UI
4. Hướng dẫn chạy (docker compose) — **test lại trên máy sạch/máy người khác**, không chỉ máy của nhóm
5. Kết quả benchmark Pha 1 (baseline) kèm biểu đồ, và cách chạy lại đúng script đó (để nhóm nhận tự tái lập được)
6. Quyết định thiết kế quan trọng & lý do (ADR ngắn) — **[Bàn giao]**: đây là phần quan trọng nhất khi bàn giao, giúp nhóm mới không mất thời gian đoán "tại sao lại làm thế này"
7. Danh sách biến môi trường cần thiết (`.env.example`) và tài khoản mẫu để đăng nhập thử (không dùng secret thật)

*Không nên* viết sẵn phần "gợi ý cải tiến cho Pha 2" trong README bàn giao — việc tự đánh giá và đề xuất kiến trúc cải tiến là chính phần được chấm ở Pha 2, viết sẵn sẽ làm mất giá trị đánh giá của nhóm nhận.

---

## 11. Checklist bàn giao trước khi hết Pha 1 **[Bàn giao]**

- [ ] `docker compose up` chạy được trên máy hoàn toàn sạch (không có `.env` cũ, không cache image cá nhân)
- [ ] Có seed script/data mẫu để nhóm mới có dữ liệu test ngay, không phải tự tạo từ đầu
- [ ] Swagger UI (`/docs`) liệt kê đầy đủ endpoint, có ví dụ request/response
- [ ] Xuất file `openapi.json` tĩnh kèm theo repo (phòng khi nhóm mới chưa chạy được app vẫn đọc được đặc tả)
- [ ] Script/lệnh benchmark Kaggle CPU có hướng dẫn chạy lại rõ ràng, kèm số liệu baseline đã lưu sẵn (không chỉ ảnh chụp màn hình)
- [ ] Tag Git rõ ràng cho bản nộp Pha 1 (vd. `v1.0-phase1`) để nhóm mới biết chính xác điểm bắt đầu
- [ ] ADR ghi lại các quyết định dễ gây hiểu lầm nếu không giải thích (vd. vì sao chọn HDBSCAN thay vì K-means, vì sao cache ở tầng nào...)
- [ ] Không có thông tin nhạy cảm/secret thật nào bị commit (API key, mật khẩu DB thật)

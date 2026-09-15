# Kế hoạch 8 tuần — Face Check-in Backend (nhóm 3 người)

> Đề bài gốc của giảng viên giữ riêng ở [2026.md](2026.md). Checklist việc cụ thể để tick theo tuần nằm riêng ở [checklist-tien-do-8-tuan.md](checklist-tien-do-8-tuan.md) — đọc file này trước để hiểu kiến trúc/API/stack/RACI/rủi ro, rồi dùng file checklist để theo dõi tiến độ hàng ngày.

---

# Phần A — Thiết kế hệ thống (đề xuất)

## A0. Lưu ý quan trọng: Pha 1 sẽ bị "đổi chủ" ở Pha 2

Giả định **có tráo đổi hệ thống** giữa các nhóm sau Pha 1 (cần xác nhận với giảng viên ở Tuần 1). Nếu đúng, có 3 khác biệt bắt buộc phải xử lý — nếu không xử lý thì timeline và README bên dưới sẽ **thiếu**, không phải chỉ cần thêm việc:

1. **Pha 1 phải "đọc được bởi người lạ", không chỉ chạy được với nhóm mình.** Code, README, ADR phải đủ để một đội khác — không hỏi lại được tác giả gốc — hiểu và chạy trong vài giờ, không phải vài ngày.
2. **Rủi ro khác stack công nghệ.** Đề bài ghi "ngôn ngữ không cố định" — nhóm nhận hệ thống của bạn có thể không biết Python/FastAPI. Ưu tiên chọn stack phổ biến, tránh pattern lạ, đặt tên file/thư mục theo quy ước chuẩn để giảm chi phí onboarding.
3. **Cần một "khoảng đệm bàn giao"** giữa Pha 1 và Pha 2: thời gian để nhóm mới đọc hiểu, chạy thử, và **tự đo lại baseline** trên hệ thống họ vừa nhận (không nên chỉ tin số liệu nhóm cũ để lại).

## A1. Nghiệp vụ đã chọn

**Check-in bằng khuôn mặt** (`User`, `FaceProfile`, `CheckInRecord`), vì:
- Đề bài bắt buộc kiểm thử tải trên **Kaggle CPU** — đúng môi trường quen thuộc để benchmark pipeline nhận diện khuôn mặt (detection/embedding/ANN search vốn nặng CPU).
- Pha 2 (tối ưu hiệu năng) có nhiều câu chuyện thật để kể: tối ưu suy luận model (ONNX/quantization), cache embedding, batch hóa request, so sánh ANN index.
- Vẫn giữ được các entity CRUD chuẩn nên không lệch khỏi yêu cầu "chỉ cần chức năng cơ bản" ở Pha 1.

*(Phương án dự phòng an toàn hơn nếu cần giảm rủi ro: đặt vé rạp phim — kiến trúc bên dưới áp dụng y hệt, chỉ khác entity nghiệp vụ.)*

## A2. Kiến trúc tổng thể (Pha 1)

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

**Nguyên tắc bắt buộc của đề bài mà kiến trúc này đảm bảo:** tầng Service chỉ phụ thuộc **interface/abstract class** của Repository (Dependency Inversion), không phụ thuộc SQLAlchemy trực tiếp. Có thể chứng minh điều này tự động bằng `import-linter` (xem A7).

**Stack:**
- **Framework**: FastAPI (tự sinh OpenAPI/Swagger tại `/docs`)
- **ORM**: SQLAlchemy 2.0 + Alembic (migration)
- **DB**: PostgreSQL (prod/docker-compose), SQLite (test nhanh)
- **Auth**: JWT (python-jose hoặc pyjwt) + OAuth2PasswordBearer
- **Face embedding**: model nhẹ chạy CPU (vd. buffalo_s của InsightFace, hoặc MobileFaceNet) để không cần GPU khi benchmark trên Kaggle CPU

## A3. Thiết kế API tối thiểu

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| POST | `/auth/login` | Không | Đăng nhập, trả JWT |
| GET | `/auth/me` | **Có** | Lấy thông tin user hiện tại |
| POST | `/users` | Có (admin) | Tạo nhân viên mới |
| GET | `/users/{id}` | Có | Xem thông tin nhân viên |
| POST | `/face-profiles` | **Có** | Đăng ký khuôn mặt (upload ảnh, sinh embedding) |
| DELETE | `/face-profiles/{id}` | Có | Xóa hồ sơ khuôn mặt |
| POST | `/checkins` | Tùy chọn | Check-in bằng ảnh khuôn mặt → so khớp embedding |
| GET | `/checkins` | Có | Lịch sử check-in (filter theo user/ngày) |
| DELETE | `/checkins/{id}` | Có (admin) | Xóa bản ghi check-in |

Đủ tối thiểu POST/GET/DELETE, có ít nhất 1 GET + 1 POST yêu cầu xác thực.

## A4. Bảo mật

- Đăng nhập bằng JWT, hash mật khẩu bằng bcrypt/argon2.
- Xác thực triển khai **một lần** dưới dạng FastAPI dependency (`Depends(get_current_user)`) gắn ở cấp router, **không copy code** vào từng handler. Có thể bổ sung `BaseHTTPMiddleware` chặn `/protected/*` để bám sát chữ "middleware" hơn.
- Phân quyền cơ bản (role `admin`/`user`).

## A5. Triển khai & Docker

- `Dockerfile` multi-stage (build → runtime nhẹ, image nhỏ).
- `docker-compose.yml`: app + PostgreSQL (+ Redis, chuẩn bị sẵn cho Pha 2 caching).
- README.md gồm: sơ đồ kiến trúc, đặc tả API (link Swagger + bảng endpoint), hướng dẫn chạy (`docker compose up`), ADR ngắn gọn.

## A6. Kiểm thử tải trên Kaggle CPU

Kaggle notebook không chạy Docker:
1. Cài dependencies trực tiếp trong notebook, chạy `uvicorn` ở background process (hoặc `nest_asyncio` + `TestClient`/`httpx.AsyncClient`).
2. Viết script benchmark (locust, hoặc tự viết với `asyncio`/`httpx`) đo: latency p50/p95/p99, throughput (req/s), CPU usage theo số concurrent users.
3. Lưu kết quả thành bảng/biểu đồ cố định — đây là **baseline** so sánh Pha 2. Phải chạy đúng loại Kaggle CPU instance cho cả hai lần đo (Pha 1 baseline và Pha 2 sau tối ưu).

## A7. Điểm "vượt yêu cầu" (ít công sức, nhiều điểm cộng)

- `import-linter` (hoặc test tự viết) chứng minh tầng Service không import framework/DB.
- GitHub Actions CI: lint + test + build Docker image mỗi lần push.
- Versioning API (`/api/v1/...`).
- Structured logging (JSON log) + endpoint `/metrics` kiểu Prometheus.
- Idempotency key cho các POST quan trọng (vd. check-in) để tránh double-submit khi tải cao.

## A8. Gợi ý cải tiến Pha 2 (map theo quality attribute)

| Quality attribute | Cải tiến đề xuất | Cách đo trước/sau |
|---|---|---|
| Performance/Throughput | Cache Redis cho GET đọc nhiều, async DB driver (`asyncpg`), connection pool tuning | So sánh p95 latency & req/s cùng kịch bản tải trên Kaggle CPU |
| Hiệu năng suy luận | Batch inference, ONNX + quantization int8, cache embedding đã trích xuất | So sánh CPU time/request, throughput suy luận |
| Scalability | Nhiều worker (Gunicorn + Uvicorn), so sánh 1 vs N worker cùng CPU | Throughput/CPU-core, độ trễ khi tăng concurrency |
| Reliability/Resilience | Retry + backoff, circuit breaker cho dependency ngoài | Tỷ lệ lỗi khi giả lập dependency chậm/lỗi |
| Security | Rate limiting chống brute-force login, rotate refresh token | Số request bị chặn, thời gian phản hồi khi bị tấn công giả lập |
| Maintainability | Enforce boundary bằng `import-linter`, tăng test coverage | Coverage % trước/sau, số vi phạm layering |

Chỉ cần chọn **2–3 cải tiến** thực sự triển khai và đo được, lý giải rõ vì sao chọn (dựa trên baseline Pha 1), đo lại trên đúng cấu hình cũ.

## A9. README.md nên có gì (tối thiểu)

Viết như thể **người đọc không quen ai trong nhóm và không hỏi lại được**:
1. Mô tả nghiệp vụ & phạm vi (scope Pha 1 vs Pha 2)
2. Sơ đồ kiến trúc + giải thích từng tầng
3. Bảng đặc tả endpoint + link Swagger UI
4. Hướng dẫn chạy (docker compose) — test lại trên máy sạch/máy người khác
5. Kết quả benchmark Pha 1 (baseline) kèm biểu đồ, cách chạy lại đúng script đó
6. Quyết định thiết kế quan trọng & lý do (ADR ngắn) — quan trọng nhất khi bàn giao
7. Danh sách biến môi trường (`.env.example`) và tài khoản mẫu để đăng nhập thử (không dùng secret thật)

*Không nên* viết sẵn phần "gợi ý cải tiến cho Pha 2" trong README bàn giao — việc tự đánh giá là chính phần được chấm ở Pha 2.

---

# Phần B — Quản lý dự án

## B1. Quyết định đã chốt

| Hạng mục | Quyết định |
|---|---|
| Nghiệp vụ | Check-in bằng khuôn mặt (`User`, `FaceProfile`, `CheckInRecord`) |
| Kịch bản Pha 2 | Giả định **có tráo đổi hệ thống** giữa các nhóm — áp dụng toàn bộ checklist bàn giao |
| Stack | FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL + JWT |
| Vai trò | A = Data/Repository/DB/load-test; B = API/Auth-Security/Docker-CI; C = Service-logic/Face-embedding/tài liệu OpenAPI, dẫn dắt Pha 2 |
| Quy ước lịch | "Tuần N" — nhóm tự gắn ngày dương lịch cụ thể khi khởi động, không thay đổi thứ tự |

**Việc phải làm ngay đầu Tuần 1, không được hoãn:** hỏi giảng viên xác nhận chính thức việc tráo đổi hệ thống Pha 2 có diễn ra không, và có giới hạn cùng stack công nghệ hay không. Nếu câu trả lời khác giả định trên, cập nhật lại checklist bàn giao (Tuần 6) — phần còn lại của kế hoạch không đổi.

## B2. Ma trận vai trò (RACI rút gọn)

| Hạng mục công việc | A (Data) | B (API/Auth/Docker) | C (Service/ML/Docs) |
|---|---|---|---|
| DB schema & migration | R | C | C |
| Repository interface + impl | R | I | C |
| FastAPI routers & Pydantic schema | C | R | C |
| JWT auth + RBAC + middleware | I | R | C |
| Service layer (business logic) | I | C | R |
| Face embedding integration | C | I | R |
| Docker/docker-compose/CI | C | R | I |
| Load test script (Kaggle CPU) | R | C | C |
| README/ADR/OpenAPI export | C | C | R |
| Benchmark Pha 1 & Pha 2, báo cáo | C | C | R |

(R = Responsible/thực hiện chính, C = Contribute/hỗ trợ hoặc review, I = Informed/cần biết kết quả)

## B3. Điểm bàn giao/phụ thuộc giữa 3 người (không được trễ)

| Ai bàn giao gì | Cho ai | Chậm nhất cuối |
|---|---|---|
| Repository interface + impl (3 entity) | B, C | Tuần 2 |
| `FaceEmbedder` interface | C tự dùng, nhưng B cần biết chữ ký hàm để nối API | Tuần 2 |
| Router skeleton | C (để nối Service vào) | Tuần 2 (đầu Tuần 3) |
| Service layer hoàn chỉnh | B (để nối auth/RBAC vào đúng chỗ) | Tuần 3 |
| Auth dependency (`get_current_user`) | A, C (dùng chung, không tự viết lại) | Tuần 4 |
| docker-compose chạy được | A, C (để test integration, để chạy Kaggle) | Tuần 5 |
| Script benchmark + baseline | Nhóm nhận hệ thống ở Pha 2 (qua bàn giao) | Tuần 6 |

## B4. Rủi ro chính & phương án dự phòng

| Rủi ro | Tác động | Phương án dự phòng |
|---|---|---|
| Model embedding không chạy nhẹ trên Kaggle CPU như kỳ vọng | Chặn benchmark Tuần 6 | Yêu cầu C xác nhận chạy được trên CPU ngay Tuần 1 |
| Giảng viên xác nhận **không** tráo đổi hệ thống | Tốn công vô ích cho checklist bàn giao | Không lãng phí nhiều — README tốt, ADR, seed data vẫn hữu ích cho chính nhóm ở Pha 2 |
| Hệ thống nhận từ nhóm khác dùng stack lạ (không phải Python) | Tuần 7 mất nhiều thời gian đọc hiểu hơn dự kiến | Dành nguyên ngày đầu Tuần 7 chỉ để onboarding; nếu vẫn không kịp, báo giảng viên xin thêm buffer |
| Auth bị viết lặp ở nhiều handler (vi phạm yêu cầu đề bài) | Mất điểm yêu cầu bắt buộc | Bắt buộc pair session Tuần 4 + review chéo trước khi merge |
| Số liệu benchmark Pha 1 vs Pha 2 không cùng điều kiện đo | Mất giá trị so sánh, vi phạm yêu cầu đề bài | A giữ nguyên script + hướng dẫn chạy lại chính xác giữa Tuần 6 và Tuần 8, không đổi loại Kaggle instance |

## B5. Theo dõi tiến độ

- Mỗi task trong checklist (Phần C) = 1 issue trên GitHub Projects, gắn label `Tuần-N`, assignee đúng người phụ trách.
- Sync ngắn cuối mỗi tuần (15–20 phút): mỗi người trả lời 3 câu — làm gì tuần này, có gì chặn, có kịp DoD không. Nếu không kịp, dời task sang đầu tuần sau **và** báo ngay cho người đang phụ thuộc vào mình (xem B3) — không để họ tự phát hiện ra khi đã trễ.
- Buffer đã có sẵn trong lịch: Tuần 5 (docker/README) và Tuần 8 (buffer 1–2 ngày cuối) là 2 tuần ít rủi ro nhất, có thể hấp thụ chậm trễ nhỏ.
- Nếu trễ hơn 1 tuần ở bất kỳ mốc nào thuộc Tuần 1–4 (phần lõi kiến trúc), ưu tiên cắt giảm phạm vi ở A7 (điểm cộng: import-linter, CI đầy đủ, idempotency key) trước khi cắt giảm phần lõi (auth, layering, Docker) — vì phần lõi là yêu cầu bắt buộc, phần điểm cộng thì không.

## B6. Deliverables nộp bài

- **Cuối Tuần 6 (Pha 1)**: repo tag `v1.0-phase1`, README đầy đủ, báo cáo benchmark baseline.
- **Cuối Tuần 8 (Pha 2)**: repo tag `v2.0-phase2`, báo cáo so sánh trước/sau + lý giải, slide, demo.

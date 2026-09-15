# Checklist tiến độ 8 tuần — Face Check-in Backend

> Đi kèm bản kế hoạch [ke-hoach-8-tuan.md](ke-hoach-8-tuan.md) (kiến trúc, API, stack, RACI, rủi ro). Đọc file đó để hiểu *vì sao*; đọc file này để tick việc *cụ thể theo tuần*, không lặp lại nội dung thiết kế.

## Cách dùng file này

1. Khi làm xong 1 việc, đổi `- [ ]` thành `- [x]` ngay tại dòng đó.
2. Commit thay đổi trong file này **cùng** commit code liên quan (hoặc ngay sau đó), ví dụ: `git commit -m "feat(repo): CheckInRepository impl + tick checklist tuần 2"`.
3. Push lên branch/PR của mình — người khác chỉ cần mở file này trên GitHub là thấy checkbox tick trực quan, không cần hỏi lại.
4. Chỉ tick việc của **chính mình**. Nếu việc là "Cả nhóm", người tick cuối cùng xác nhận cả nhóm đã đồng ý.
5. Điền tên/GitHub handle thật vào bảng dưới đây ngay từ Tuần 1 để thay cho ký hiệu A/B/C.

| Ký hiệu | Vai trò | Tên / GitHub handle |
|---|---|---|
| **A** | Data/Repository/DB/load-test | _điền tên_ |
| **B** | API/Auth-Security/Docker-CI | _điền tên_ |
| **C** | Service-logic/Face-embedding/tài liệu, dẫn dắt Pha 2 | _điền tên_ |

---

## Tuần 1 — Khởi động & Thiết kế

> Mục tiêu: chốt use-case chi tiết, ERD, khung repo 3 tầng, board quản lý việc.

### Cả nhóm
- [x] Pha 2 có tráo đổi hệ thống giữa các nhóm, không giới hạn cùng stack công nghệ
- [x] Vẽ ERD: `User(id, email, hashed_password, role, full_name, created_at)`
- [x] Vẽ ERD: `FaceProfile(id, user_id FK, embedding, created_at)`
- [x] Vẽ ERD: `CheckInRecord(id, user_id FK, checkin_time, similarity_score, status)`
- [ ] Review kiến trúc 3 tầng, thống nhất tên thư mục: `app/api`, `app/services`, `app/repositories`, `app/models`, `app/schemas`, `tests/`
- [x] Tạo repo GitHub công khai + bật branch protection cho `main`
- [ ] Tạo GitHub Projects board (cột Backlog/To Do/In Progress/Review/Done)
- [ ] Tạo issue cho toàn bộ WBS Tuần 2–8 (tiêu đề + assignee + label tuần)

### A
- [x] Viết ERD thành `docs/erd.md` (mermaid)
- [x] Draft SQLAlchemy models (chưa cần chạy)
- [x] `alembic init`

### B
- [x] Khởi tạo FastAPI skeleton
- [x] `.env.example`
- [x] Cấu hình `pydantic-settings`
- [x] Pre-commit (ruff/black) — dùng `ruff format` thay black; mỗi máy chạy `pre-commit install` một lần
- [x] GitHub Actions skeleton (chạy lint)

### C
- [x] Viết đặc tả use-case: đăng ký khuôn mặt (sequence ngắn)
- [x] Viết đặc tả use-case: check-in (sequence ngắn)
- [x] Viết đặc tả use-case: xem lịch sử (sequence ngắn)
- [ ] Khảo sát & chốt model embedding (buffalo_s/InsightFace hay MobileFaceNet)
- [ ] Chạy thử offline 1 ảnh, xác nhận chạy được trên CPU thường

### DoD cuối Tuần 1
- [x] `docs/architecture.md` + `docs/erd.md` đã commit
- [ ] Repo skeleton đã push, CI lint chạy xanh
- [ ] Board có đủ issue cho Tuần 2–8
- [x] Có câu trả lời (hoặc ghi nhận "chưa trả lời, giả định X") từ giảng viên về tráo đổi Pha 2
- [ ] Đã chốt model embedding cụ thể (tên + kích thước + license)

---

## Tuần 2 — Data layer

> Mục tiêu: CRUD qua Repository chạy được cho cả 3 entity.
> Phụ thuộc: B/C cần A hoàn thành Repository interface (ABC) trước cuối tuần để không bị chặn ở Tuần 3.

### A (chính)
- [ ] SQLAlchemy models thật (không phải draft)
- [ ] Alembic migration đầu tiên chạy được trên Postgres
- [ ] Alembic migration chạy được trên SQLite
- [ ] Repository interface (ABC, framework-free): `UserRepository`
- [ ] Repository interface: `FaceProfileRepository`
- [ ] Repository interface: `CheckInRepository`
- [ ] Implementation SQLAlchemy cho cả 3 repository trên
- [ ] Script/test thủ công `scripts/manual_test_repo.py` chứng minh CRUD chạy qua repository

### B
- [ ] Dựng docker-compose cho Postgres dev
- [ ] Hỗ trợ A test kết nối DB
- [ ] Bắt đầu FastAPI router rỗng (chưa nối service)

### C
- [ ] Interface `FaceEmbedder` (abstract, độc lập với DB, chưa cần tối ưu)
- [ ] Pydantic schema request/response cho `User`
- [ ] Pydantic schema request/response cho `FaceProfile`
- [ ] Pydantic schema request/response cho `CheckInRecord`

### DoD cuối Tuần 2
- [ ] Repository interface + impl cho 3 entity, có test thủ công log lại (screenshot/script output)
- [ ] Migration chạy sạch từ DB rỗng (`alembic upgrade head` trên máy sạch)
- [ ] `FaceEmbedder` interface sẵn sàng (chưa cần implementation hoàn chỉnh)

---

## Tuần 3 — Service layer + API layer

> Mục tiêu: toàn bộ endpoint CRUD cơ bản chạy qua `/docs` (chưa có auth).
> Phụ thuộc: cần Repository (Tuần 2, A) đã xong; C cần B dựng router skeleton xong.

### A
- [ ] Hỗ trợ B/C khi vướng mắc về Repository
- [ ] Dựng khung script load test (`locustfile.py` hoặc `benchmark.py`, chưa chạy thật)

### B
- [ ] Router `/users` (chưa auth)
- [ ] Router `/face-profiles` (chưa auth)
- [ ] Router `/checkins` (chưa auth)
- [ ] Exception handler chuẩn (400/404/422)
- [ ] Versioning `/api/v1/...`

### C (chính)
- [ ] `UserService` (thuần Python, không import FastAPI/SQLAlchemy)
- [ ] `FaceProfileService` (gọi `FaceEmbedder` + Repository)
- [ ] `CheckInService` (so khớp embedding, tính similarity)
- [ ] Kiểm tra kỹ: Service layer không import framework/DB

### DoD cuối Tuần 3
- [ ] Toàn bộ endpoint CRUD cơ bản (POST/GET/DELETE cho 3 entity) chạy qua `/docs`, test tay bằng Swagger UI thành công
- [ ] Service layer không có import framework/DB — kiểm tra bằng `grep` nhanh
- [ ] Face embedding thật (không mock) chạy end-to-end: upload ảnh → sinh embedding → lưu DB

---

## Tuần 4 — Auth, RBAC, Unit test

> Mục tiêu: 1 GET + 1 POST có auth hoạt động; test pass cho service layer.
> Đây là điểm dễ lệch chuẩn kiến trúc nhất → cả nhóm pair lại.

### Cả nhóm
- [ ] Pair session ≥ nửa buổi: thống nhất cách implement dependency injection cho auth

### A
- [ ] Thêm field `role` cho `User` (nếu chưa có) + migration cập nhật
- [ ] Seed data user mẫu (`admin`, `user`)

### B (chính)
- [ ] JWT login (hash bcrypt/argon2)
- [ ] `Depends(get_current_user)` dùng chung ở router (không copy code từng handler)
- [ ] RBAC theo role
- [ ] (Cân nhắc) `BaseHTTPMiddleware` chặn `/protected/*`

### C
- [ ] Unit test Service layer (mock Repository): đăng ký khuôn mặt
- [ ] Unit test Service layer: check-in thành công
- [ ] Unit test Service layer: check-in thất bại

### DoD cuối Tuần 4
- [ ] `POST /face-profiles` và `GET /checkins` yêu cầu JWT — xác nhận 401 khi không có token (Postman/Swagger)
- [ ] RBAC hoạt động: user thường không xóa được record người khác / không tạo được user mới
- [ ] Unit test service layer chạy pass trong CI (không chỉ local)
- [ ] Auth code không bị copy-paste lặp ở từng handler — xác nhận bằng review chéo

---

## Tuần 5 — Docker hóa, README, Integration test

> Mục tiêu: `docker compose up` chạy được từ máy sạch.

### A
- [ ] Integration test cho Repository (SQLite/Postgres test container)

### B (chính)
- [ ] `Dockerfile` multi-stage
- [ ] `docker-compose.yml` (app + Postgres + Redis dự phòng Pha 2)
- [ ] Test lại trên máy khác/máy sạch trong nhóm (không chỉ máy đã dev)

### C
- [ ] README đầy đủ: kiến trúc
- [ ] README đầy đủ: đặc tả API
- [ ] README đầy đủ: hướng dẫn chạy
- [ ] README đầy đủ: ADR ngắn
- [ ] Bắt đầu ADR ghi lại quyết định dễ gây hiểu lầm (vd. vì sao chọn model embedding X, vì sao auth implement kiểu Y)

### DoD cuối Tuần 5
- [ ] `docker compose up` chạy thành công trên máy chưa từng cài project (người thứ 3 trong nhóm test chéo)
- [ ] README có đủ 7 mục theo kế hoạch (mục A9 trong ke-hoach-8-tuan.md), trừ phần benchmark
- [ ] Integration test chạy trong CI, không chỉ unit test

---

## Tuần 6 — Load test + Bàn giao Pha 1

> Mục tiêu kép: (1) đo baseline hiệu năng trên Kaggle CPU, (2) hoàn thiện toàn bộ checklist bàn giao vì hệ thống sẽ bị tráo đổi.

### Nửa đầu tuần — benchmark

**A (chính)**
- [ ] Hoàn thiện script benchmark (locust hoặc `httpx`/`asyncio` tự viết)
- [ ] Chạy trên Kaggle CPU notebook
- [ ] Đo p50/p95/p99 latency, throughput, CPU usage theo số concurrent users
- [ ] Lưu kết quả dạng bảng/CSV (không chỉ ảnh chụp màn hình)

**B**
- [ ] Hỗ trợ A dựng môi trường chạy app trong Kaggle notebook (uvicorn background hoặc TestClient/httpx.AsyncClient)

**C**
- [ ] Viết báo cáo baseline (biểu đồ + nhận xét ngắn) đưa vào README

### Nửa cuối tuần — checklist bàn giao

**Cả nhóm**
- [ ] Rà lại checklist bàn giao bên dưới, mỗi dòng có 1 người ký xác nhận

**C (chính)**
- [ ] Hoàn thiện ADR
- [ ] Xuất `openapi.json` tĩnh
- [ ] Viết seed script/data mẫu

**B**
- [ ] Tag Git `v1.0-phase1`
- [ ] Rà soát không có secret thật bị commit

**A**
- [ ] Đóng gói script + số liệu benchmark kèm hướng dẫn chạy lại rõ ràng

### Checklist bàn giao Pha 1 (ký xác nhận trước khi tag)
- [ ] `docker compose up` chạy được trên máy hoàn toàn sạch — phụ trách: **B**
- [ ] Seed script/data mẫu — phụ trách: **C**
- [ ] Swagger UI đầy đủ endpoint + ví dụ request/response — phụ trách: **C**
- [ ] Xuất `openapi.json` tĩnh — phụ trách: **C**
- [ ] Script/lệnh benchmark có hướng dẫn chạy lại + số liệu baseline đã lưu — phụ trách: **A**
- [ ] Tag Git `v1.0-phase1` — phụ trách: **B**
- [ ] ADR các quyết định dễ gây hiểu lầm — phụ trách: **C** (input từ A, B)
- [ ] Không có secret thật bị commit — phụ trách: **B** (rà soát cuối cùng trước khi tag)

### DoD cuối Tuần 6 (= Nộp/Bàn giao Pha 1)
- [ ] Toàn bộ checklist bàn giao ở trên đã tick, có người ký tên phụ trách từng dòng
- [ ] Repo gắn tag `v1.0-phase1`
- [ ] Báo cáo benchmark baseline (số liệu + cách chạy lại) đã có trong README hoặc `docs/benchmark-phase1.md`
- [ ] Đã nhận hệ thống từ nhóm khác (nếu tráo đổi diễn ra đúng lịch nhà trường)

---

## Tuần 7 — Onboarding hệ thống mới nhận + Chọn & triển khai cải tiến Pha 2

> Mục tiêu: xác nhận lại baseline trên hệ thống mới nhận, chọn 2–3 cải tiến, triển khai xong (chưa cần đo lại).

### Đầu tuần — cả nhóm (ưu tiên cao nhất, không bỏ qua)
- [ ] Đọc README/ADR của nhóm bàn giao
- [ ] Chạy `docker compose up` trên hệ thống mới nhận
- [ ] Chạy thử toàn bộ endpoint qua Swagger
- [ ] Tự đo lại baseline bằng đúng script benchmark của nhóm cũ, cùng loại Kaggle CPU instance
- [ ] Đối chiếu với số liệu nhóm cũ; nếu chênh lệch lớn, ghi nghi vấn nguyên nhân vào `docs/benchmark-reconciliation.md`

### Chọn cải tiến (chỉ chọn sau khi đo, không chọn cứng trước)
- [ ] Chốt 2–3 cải tiến dựa trên điểm nghẽn thực tế đo được (tham khảo bảng A8 trong ke-hoach-8-tuan.md)
- [ ] **C** dẫn dắt (nếu chọn): tối ưu suy luận face embedding (ONNX + quantization, cache embedding)
- [ ] **A** dẫn dắt (nếu chọn): cache Redis cho GET đọc nhiều + async DB driver
- [ ] **B** dẫn dắt (nếu chọn): multi-worker (Gunicorn+Uvicorn), so sánh 1 vs N worker

### Triển khai (cuối tuần)

**A**
- [ ] Implement cải tiến performance/scalability đã chọn (cache/async driver/worker)

**B**
- [ ] Implement cải tiến thuộc mảng phụ trách (vd. rate limiting nếu chọn security)
- [ ] Đảm bảo docker-compose vẫn chạy được với thay đổi mới (Redis, thêm worker)

**C**
- [ ] Implement cải tiến ML/inference nếu chọn
- [ ] Bắt đầu viết khung báo cáo so sánh trước/sau

### DoD cuối Tuần 7
- [ ] Baseline hệ thống mới nhận đã được xác nhận lại, có giải thích cho mọi chênh lệch so với số liệu nhóm cũ
- [ ] 2–3 cải tiến đã chọn, có lý do bằng văn bản dựa trên baseline (không phải "nghe nói cái này nhanh hơn")
- [ ] Cải tiến chạy được (chưa cần đo lại số liệu)

---

## Tuần 8 — Đo lại, so sánh, báo cáo, demo

> Mục tiêu: nộp Pha 2.

### A
- [ ] Chạy lại benchmark đúng cấu hình Kaggle CPU như Tuần 6/7
- [ ] Xuất số liệu so sánh trước/sau cho phần mình phụ trách

### B
- [ ] Chạy lại benchmark cho phần mình phụ trách (vd. so sánh 1 vs N worker, hoặc số liệu rate limiting chặn brute-force)

### C (chính)
- [ ] Tổng hợp toàn bộ số liệu thành báo cáo so sánh trước/sau
- [ ] Lý giải nguyên nhân cải thiện (không chỉ nêu số — giải thích *tại sao*)
- [ ] Chuẩn bị slide
- [ ] Chuẩn bị kịch bản demo

### Buffer 1–2 ngày cuối tuần — cả nhóm
- [ ] Rehearsal demo ít nhất 1 lần
- [ ] Dự trù câu hỏi giảng viên có thể hỏi (vd. "tại sao không chọn cải tiến khác?")

### DoD cuối Tuần 8 (= Nộp Pha 2)
- [ ] Báo cáo so sánh trước/sau đầy đủ số liệu + lý giải, dựa trên hệ thống nhận từ nhóm khác
- [ ] Code cải tiến đã merge vào `main`, tag `v2.0-phase2`
- [ ] Slide + demo đã rehearsal ít nhất 1 lần trong nhóm

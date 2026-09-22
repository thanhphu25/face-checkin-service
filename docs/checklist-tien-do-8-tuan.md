# Checklist tiến độ 8 tuần — Face Check-in Backend

> Đi kèm bản kế hoạch [ke-hoach-8-tuan.md](ke-hoach-8-tuan.md) (kiến trúc, API, stack, RACI, rủi ro) và [ke-hoach-commit-tuan-2-8.md](ke-hoach-commit-tuan-2-8.md) (thứ tự commit, dependency, tránh conflict). Đọc file này để tick việc *cụ thể theo tuần*, không lặp lại nội dung thiết kế.

## Cách dùng file này

1. Khi làm xong 1 việc, đổi `- [ ]` thành `- [x]` ngay tại dòng đó.
2. Commit thay đổi trong file này **cùng** commit code liên quan (hoặc ngay sau đó), ví dụ: `git commit -m "feat(repo): CheckInRepository impl + tick checklist tuần 2"`.
3. Push lên branch/PR của mình — người khác chỉ cần mở file này trên GitHub là thấy checkbox tick trực quan, không cần hỏi lại.
4. Chỉ tick việc của **chính mình**. Nếu việc là "Cả nhóm", người tick cuối cùng xác nhận cả nhóm đã đồng ý.
5. Điền tên/GitHub handle thật vào bảng dưới đây ngay từ Tuần 1 để thay cho ký hiệu A/B/C.
6. Ghi chú `(chờ X: ...)` nghĩa là chỉ bắt đầu sau khi người X hoàn thành phần đó; trao đổi contract sớm nhưng tránh cùng sửa một file.

| Ký hiệu | Vai trò | Tên / GitHub handle |
|---|---|---|
| **A** | Data/Repository/DB/load-test | _điền tên_ |
| **B** | API/Auth-Security/Docker-CI | _điền tên_ |
| **C** | Service-logic/Face-embedding/tài liệu, dẫn dắt Pha 2 | _điền tên_ |

---

## Tuần 1 — Khởi động & Thiết kế

> Mục tiêu: chốt use-case chi tiết, ERD, khung repo 3 tầng, board quản lý việc.
> Trạng thái tạm thời: coi như đã hoàn thành để chuyển sang Tuần 2.

### Cả nhóm
- [x] Pha 2 có tráo đổi hệ thống giữa các nhóm, không giới hạn cùng stack công nghệ
- [x] Vẽ ERD: `User(id, email, hashed_password, role, full_name, created_at)`
- [x] Vẽ ERD: `FaceProfile(id, user_id FK, embedding, created_at)`
- [x] Vẽ ERD: `CheckInRecord(id, user_id FK, checkin_time, similarity_score, status)`
- [x] Review kiến trúc 3 tầng, thống nhất tên thư mục: `app/api`, `app/services`, `app/repositories`, `app/models`, `app/schemas`, `tests/`
- [x] Tạo repo GitHub công khai + bật branch protection cho `main`

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
- [x] Khảo sát & chốt model embedding (buffalo_s/InsightFace)
- [x] Chạy thử offline 1 ảnh, xác nhận chạy được trên CPU thường

### DoD cuối Tuần 1
- [x] `docs/architecture.md` + `docs/erd.md` đã commit
- [x] Repo skeleton đã push, CI lint chạy xanh
- [x] Có câu trả lời (hoặc ghi nhận "chưa trả lời, giả định X") từ giảng viên về tráo đổi Pha 2
- [x] Đã chốt model embedding cụ thể (tên + kích thước + license)

---

## Tuần 2 — Data layer

> Mục tiêu: CRUD qua Repository chạy được cho cả 3 entity.
> Phụ thuộc: B/C cần A hoàn thành Repository interface (ABC) trước cuối tuần để không bị chặn ở Tuần 3.

### A (chính)
- [x] SQLAlchemy models thật (không phải draft)
- [x] Domain entities thuần Python cho `User`, `FaceProfile`, `CheckInRecord` (sau A: chốt field; làm trước 3 Repository interface)
- [x] Alembic migration đầu tiên chạy được trên Postgres (chờ B: Postgres trong docker-compose)
- [x] Alembic migration chạy được trên SQLite (sau A: models + migration đầu tiên)
- [x] Repository interface (ABC, framework-free): `UserRepository` (sau A: domain entity `User`)
- [x] Repository interface: `FaceProfileRepository` (sau A: domain entity `FaceProfile`)
- [x] Repository interface: `CheckInRepository` (sau A: domain entity `CheckInRecord`)
- [x] Implementation SQLAlchemy cho cả 3 repository trên (sau A: models + 3 interface)
- [x] Script/test thủ công `scripts/manual_test_repo.py` chứng minh CRUD chạy qua repository (sau A: repository impl + migration)

### B
- [x] Dựng docker-compose cho Postgres dev
- [x] Hỗ trợ A test kết nối DB (chờ A: migration Postgres sẵn sàng)
- [x] Bắt đầu FastAPI router rỗng (chưa nối service)

### C
- [x] Interface `FaceEmbedder` (abstract, độc lập với DB, chưa cần tối ưu)
- [x] Pydantic schema request/response cho `User` (chờ A: chốt field `User`)
- [x] Pydantic schema request/response cho `FaceProfile` (chờ A: chốt field `FaceProfile`)
- [x] Pydantic schema request/response cho `CheckInRecord` (chờ A: chốt field `CheckInRecord`)

### DoD cuối Tuần 2
- [x] Repository interface + impl cho 3 entity, có test thủ công log lại (A xác nhận sau script CRUD)
- [x] Migration chạy sạch từ DB rỗng (`alembic upgrade head` trên máy sạch) (A + B xác nhận trên Postgres)
- [x] `FaceEmbedder` interface sẵn sàng (C xác nhận, B review chữ ký hàm)

Bằng chứng chạy migration, CRUD và quality gates: [week-2-verification.md](week-2-verification.md).

---

## Tuần 3 — Service layer + API layer

> Mục tiêu: toàn bộ endpoint CRUD cơ bản chạy qua `/docs` (chưa có auth).
> Phụ thuộc: A chốt Repository; C làm Service; B chốt versioning/router skeleton rồi nối Service vào router.

### A
- [x] Hỗ trợ B/C khi vướng mắc về Repository (sau A: repository Tuần 2 đã chốt)
- [x] Dựng khung script load test (`locustfile.py` hoặc `benchmark.py`, chưa chạy thật) (chờ B: chốt URL endpoint)

### B
- [x] Router `/users` (chưa auth) (chờ C: `UserService` + schema `User`)
- [x] Router `/face-profiles` (chưa auth) (chờ C: `FaceProfileService` + schema `FaceProfile`)
- [x] Router `/checkins` (chưa auth) (chờ C: `CheckInService` + schema `CheckInRecord`)
- [x] Nối dependency API → Service → Repository trong composition root (chờ A: repository impl; C: service contract)
- [x] Exception handler chuẩn (400/404/422)
- [x] Versioning `/api/v1/...` (làm trước B: 3 router để tránh đổi path)

### C (chính)
- [x] `InsightFaceEmbedder` implementation thật (sau C: `FaceEmbedder`; làm trước test end-to-end)
- [x] `UserService` (thuần Python, không import FastAPI/SQLAlchemy) (chờ A: `UserRepository` impl)
- [x] `FaceProfileService` (gọi `FaceEmbedder` + Repository) (chờ A: `FaceProfileRepository`; sau C: `FaceEmbedder`)
- [x] `CheckInService` (so khớp embedding, tính similarity) (chờ A: `FaceProfileRepository` + `CheckInRepository`; sau C: `FaceEmbedder`)
- [x] Kiểm tra kỹ: Service layer không import framework/DB (sau C: 3 service)

### DoD cuối Tuần 3
- [x] Toàn bộ endpoint CRUD cơ bản (POST/GET/DELETE cho 3 entity) chạy qua `/docs`, test tay bằng Swagger UI thành công (chờ B: router; C: service; A: repository)
- [x] Service layer không có import framework/DB — kiểm tra bằng `grep` nhanh (chờ C: hoàn tất service)
- [x] Face embedding thật (không mock) chạy end-to-end: upload ảnh → sinh embedding → lưu DB (chờ B: router; C: embedder/service; A: repository)

Bằng chứng API, SQLite/PostgreSQL, transaction và embedding thật: [week-3-verification.md](week-3-verification.md).

---

## Tuần 4 — Auth, RBAC, Unit test

> Mục tiêu: 1 GET + 1 POST có auth hoạt động; test pass cho service layer.
> Đây là điểm dễ lệch chuẩn kiến trúc nhất → cả nhóm pair lại.
>
> Bằng chứng kỹ thuật SQLite/PostgreSQL/API/OpenAPI/InsightFace: [week-4-verification.md](week-4-verification.md).
> Technical review thay thế được chủ project chấp thuận: [week-4-auth-technical-review.md](week-4-auth-technical-review.md). Tài liệu này không tuyên bố đã có pair/review của con người.

### Cả nhóm
- [x] Technical review có cấu trúc thay cho pair session auth (chủ project chấp thuận ngày 2026-09-22; không tuyên bố đã có pair session nửa buổi của con người)

### A
- [x] Thêm field `role` cho `User` (nếu chưa có) + migration cập nhật (đã có đủ trong domain, ORM và migration `0001`; không tạo migration thừa)
- [x] Chốt dữ liệu user mẫu (`admin`, `user`) và bàn giao spec cho C (xem `week-4-auth-contract.md`; chỉ chốt identity/role, không commit mật khẩu)

### B (chính)
- [x] JWT login (Argon2id, tương thích hash PBKDF2 tạm của Tuần 3) (đã nối `UserService`, `UserRepository`, `/auth/login` và `/auth/me`)
- [x] `Depends(get_current_user)` dùng chung ở route (không copy code từng handler; router có cả endpoint công khai và được bảo vệ)
- [x] RBAC theo role (dependency `require_admin`, ownership được ép trong Service)
- [x] Đã cân nhắc `BaseHTTPMiddleware` và không dùng (dependency là cơ chế auth duy nhất, tránh decode/DB lookup hai lần)
- [x] Cập nhật CI chạy `pytest` và các quality gate trên `main`/`week4`; lệnh CI tương ứng đã chạy pass từ `uv.lock`

### C
- [x] Unit test Service layer (fake Repository/FaceEmbedder đúng port): đăng ký khuôn mặt thành công, user thiếu, no-face/multiple-face và ownership
- [x] Unit test Service layer: check-in thành công, lọc đúng model/dimension và ownership
- [x] Unit test Service layer: check-in `unmatched`/`no_face`, xác nhận lịch sử thất bại vẫn được lưu

### DoD cuối Tuần 4
- [x] `POST /face-profiles` và `GET /checkins` yêu cầu JWT — API integration test xác nhận 401 khi không có token
- [x] RBAC hoạt động: user thường không xóa được record người khác / không tạo được user mới
- [x] Unit test service layer chạy pass bằng đúng dependency và lệnh pytest của CI
- [x] Auth code không bị copy-paste lặp ở từng handler — AST test và technical review thay thế đã pass; không tuyên bố đã có review chéo A/C của con người

---

## Tuần 5 — Docker hóa, README, Integration test

> Mục tiêu: `docker compose up` chạy được từ máy sạch.
>
> Bằng chứng kỹ thuật Repository/Docker/Compose/CI/clean-directory/InsightFace: [week-5-verification.md](week-5-verification.md).

### A
- [x] Integration test cho Repository (SQLite/Postgres test container) (Repository/mapping/migration thật; PostgreSQL database kiểm chứng cách ly)

### B (chính)
- [x] `Dockerfile` multi-stage (Python 3.12, frozen production dependencies, runtime non-root và stdlib healthcheck)
- [x] `docker-compose.yml` (app + Postgres + Redis dự phòng Pha 2; migration là service một lần, Redis chưa được app sử dụng)
- [x] Test trên môi trường máy sạch độc lập bằng GitHub-hosted Ubuntu runner — run `35703077030` build/up/verify/cleanup Compose thành công; đây là tiêu chí kỹ thuật thay thế được chủ project chấp thuận, không tuyên bố A/C đã test trên máy cá nhân

### C
- [x] README đầy đủ: kiến trúc
- [x] README đầy đủ: đặc tả API (quyền truy cập và Swagger/OpenAPI)
- [x] README đầy đủ: hướng dẫn chạy (Docker Compose từ clone sạch, health/log/migration/dọn test)
- [x] README đầy đủ: ADR ngắn (liên kết bốn ADR phản ánh implementation)
- [x] Bắt đầu ADR ghi lại quyết định dễ gây hiểu lầm (DB/Repository/migration, auth/RBAC, embedding và ranh giới Pha 1/Pha 2)

### DoD cuối Tuần 5
- [x] `docker compose up` chạy thành công trên GitHub-hosted runner sạch — run `35703077030`, job `compose-clean-setup`; tiêu chí thay thế được chủ project chấp thuận, không tuyên bố là máy của thành viên A/C
- [x] README có đủ 7 mục theo kế hoạch, benchmark ghi rõ chờ Tuần 6; chưa có xác nhận review A/B của con người
- [x] Integration test chạy trong CI, không chỉ unit test (job SQLite và PostgreSQL thật bắt buộc; đã mô phỏng đủ job cục bộ, run GitHub được kiểm tra sau push)

---

## Tuần 6 — Load test + Bàn giao Pha 1

> Mục tiêu kép: (1) đo baseline hiệu năng trên Kaggle CPU, (2) hoàn thiện toàn bộ checklist bàn giao vì hệ thống sẽ bị tráo đổi.

### Nửa đầu tuần — benchmark

**A (chính)**
- [x] Hoàn thiện script benchmark (`scripts/benchmark.py` sweep concurrency, warm-up, settle, CPU system/process, CSV + metadata; `scripts/run_baseline.py` chạy trọn migration → seed → Uvicorn → đo; đã chạy thật cục bộ trên SQLite, chưa chạy trên Kaggle)
- [x] Chạy trên Kaggle CPU notebook (chạy ngày 2026-09-22, commit `4affbd0`, instance 4 core, cả SQLite lẫn PostgreSQL; 16/16 mức đo `error_count=0`)
- [x] Đo p50/p95/p99 latency, throughput, CPU usage theo số concurrent users (4 mức 1/2/4/8 cho cả hai scenario `checkin` và `history`)
- [x] Lưu kết quả dạng bảng/CSV ([docs/benchmark/](benchmark/): hai CSV kèm hai file metadata ghi phần cứng và toàn bộ tham số chạy)

**B**
- [x] Hỗ trợ A dựng môi trường chạy app trong Kaggle notebook ([benchmark-kaggle.md](benchmark-kaggle.md): 6 cell đã chạy thật; cell PostgreSQL sửa theo cluster 14 của image Kaggle)

**C**
- [x] Viết báo cáo baseline (biểu đồ + nhận xét ngắn) đưa vào README ([benchmark-phase1.md](benchmark-phase1.md) đầy đủ; README mục 5 có bảng tóm tắt và ba nhận xét)

### Nửa cuối tuần — checklist bàn giao

**Cả nhóm**
- [ ] Rà lại checklist bàn giao bên dưới, mỗi dòng có 1 người ký xác nhận (chờ A/B/C: hoàn tất phần được giao)

**C (chính)**
- [ ] Hoàn thiện ADR (chờ A/B: review quyết định DB/auth/triển khai)
- [x] Xuất `openapi.json` tĩnh ([docs/openapi.json](openapi.json) qua `scripts/export_openapi.py`; test fail nếu file commit lệch so với app)
- [x] Viết seed script/data mẫu (`scripts/seed.py`: admin/user mẫu, face profile thật và ba bản ghi lịch sử; idempotent, mật khẩu lấy từ biến môi trường nên không có secret trong repo)

**B**
- [ ] Tag Git `v1.0-phase1` (làm cuối: chờ A/C xong deliverable + CI xanh + rà secret)
- [ ] Rà soát không có secret thật bị commit (làm trước B: tag `v1.0-phase1`)

**A**
- [ ] Đóng gói script + số liệu benchmark kèm hướng dẫn chạy lại rõ ràng (sau A: benchmark; nhờ B/C chạy thử hướng dẫn)

### Checklist bàn giao Pha 1 (ký xác nhận trước khi tag)
- [ ] `docker compose up` chạy được trên máy hoàn toàn sạch — phụ trách: **B** (chờ A/C: migration + seed sẵn sàng)
- [ ] Seed script/data mẫu — phụ trách: **C** (chờ A: migration; B: hash password)
- [ ] Swagger UI đầy đủ endpoint + ví dụ request/response — phụ trách: **C** (chờ B: router/auth hoàn tất)
- [ ] Xuất `openapi.json` tĩnh — phụ trách: **C** (chờ B: API cuối cùng)
- [ ] Script/lệnh benchmark có hướng dẫn chạy lại + số liệu baseline đã lưu — phụ trách: **A** (chờ B: môi trường; C: review cách trình bày)
- [ ] Tag Git `v1.0-phase1` — phụ trách: **B** (làm sau cùng khi 7 dòng còn lại đã tick)
- [ ] ADR các quyết định dễ gây hiểu lầm — phụ trách: **C** (chờ A/B: gửi input và review)
- [ ] Không có secret thật bị commit — phụ trách: **B** (làm ngay trước khi tag; A/C không push thêm sau khi duyệt)

### DoD cuối Tuần 6 (= Nộp/Bàn giao Pha 1)
- [ ] Toàn bộ checklist bàn giao ở trên đã tick, có người ký tên phụ trách từng dòng (chờ A/B/C: tự xác nhận phần mình)
- [ ] Repo gắn tag `v1.0-phase1` (chờ B: checklist bàn giao + CI xanh)
- [x] Báo cáo benchmark baseline đã có trong README hoặc `docs/benchmark-phase1.md` (cả hai: README mục 5 tóm tắt, `docs/benchmark-phase1.md` phân tích đầy đủ)
- [ ] Đã nhận hệ thống từ nhóm khác (chờ cả nhóm: bàn giao Pha 1 xong)

---

## Tuần 7 — Onboarding hệ thống mới nhận + Chọn & triển khai cải tiến Pha 2

> Mục tiêu: xác nhận lại baseline trên hệ thống mới nhận, chọn 2–3 cải tiến, triển khai xong (chưa cần đo lại).

### Đầu tuần — cả nhóm (ưu tiên cao nhất, không bỏ qua)
- [ ] Đọc README/ADR của nhóm bàn giao
- [ ] Chạy `docker compose up` trên hệ thống mới nhận (sau cả nhóm: đọc README/ADR)
- [ ] Chạy thử toàn bộ endpoint qua Swagger (sau cả nhóm: compose chạy được)
- [ ] Tự đo lại baseline bằng đúng script benchmark của nhóm cũ (sau cả nhóm: endpoint đã test; A chủ trì chạy)
- [ ] Đối chiếu với số liệu nhóm cũ; ghi nghi vấn vào `docs/benchmark-reconciliation.md` (chờ A: baseline đo lại; C ghi chép)

### Chọn cải tiến (chỉ chọn sau khi đo, không chọn cứng trước)
- [ ] Chốt 2–3 cải tiến dựa trên điểm nghẽn thực tế đo được (chờ A: baseline; C: đối chiếu)
- [ ] **C** dẫn dắt (nếu chọn): tối ưu suy luận face embedding (chờ cả nhóm: chốt cải tiến; C sở hữu file ML)
- [ ] **A** dẫn dắt (nếu chọn): cache Redis cho GET đọc nhiều + async DB driver (chờ cả nhóm: chốt cải tiến; A sở hữu data layer)
- [ ] **B** dẫn dắt (nếu chọn): multi-worker (Gunicorn+Uvicorn), so sánh 1 vs N worker (chờ cả nhóm: chốt cải tiến; B sở hữu Docker)

### Triển khai (cuối tuần)

**A**
- [ ] Implement cải tiến performance/scalability đã chọn (cache/async driver) (chờ cả nhóm: chốt phạm vi; phối hợp B nếu cần Redis)

**B**
- [ ] Implement cải tiến thuộc mảng phụ trách (multi-worker/rate limiting) (chờ cả nhóm: chốt phạm vi; B sở hữu config triển khai)
- [ ] Đảm bảo docker-compose vẫn chạy được với thay đổi mới (chờ A/C: bàn giao biến môi trường; chỉ B sửa compose)

**C**
- [ ] Implement cải tiến ML/inference nếu chọn (chờ cả nhóm: chốt phạm vi; C sở hữu adapter ML)
- [ ] Bắt đầu viết khung báo cáo so sánh trước/sau (chờ cả nhóm: chốt cải tiến và metric)

### DoD cuối Tuần 7
- [ ] Baseline hệ thống mới nhận đã được xác nhận lại, có giải thích chênh lệch (chờ A: số liệu; C: reconciliation)
- [ ] 2–3 cải tiến đã chọn, có lý do bằng văn bản dựa trên baseline (chờ cả nhóm: duyệt phạm vi)
- [ ] Cải tiến chạy được, chưa cần đo lại (chờ A/B/C: merge phần được giao; B xác nhận compose)

---

## Tuần 8 — Đo lại, so sánh, báo cáo, demo

> Mục tiêu: nộp Pha 2.

### A
- [ ] Chạy lại benchmark đúng cấu hình Kaggle CPU như Tuần 6/7 (chờ A/B/C: cải tiến merge; B: compose ổn định)
- [ ] Xuất số liệu so sánh trước/sau cho phần mình phụ trách (sau A: benchmark; giao C tổng hợp)

### B
- [ ] Chạy benchmark chuyên biệt cho phần mình (1 vs N worker/rate limiting) (chờ A: chốt harness chung; B không sửa script chung song song)

### C (chính)
- [ ] Tổng hợp toàn bộ số liệu thành báo cáo so sánh trước/sau (chờ A/B: bàn giao số liệu)
- [ ] Lý giải nguyên nhân cải thiện (chờ A/B: giải thích phần data/deploy)
- [ ] Chuẩn bị slide (sau C: báo cáo; A/B review phần mình)
- [ ] Chuẩn bị kịch bản demo (chờ B: compose/demo env; sau C: slide)

### Buffer 1–2 ngày cuối tuần — cả nhóm
- [ ] Rehearsal demo ít nhất 1 lần (chờ C: slide/kịch bản; B: demo env; A: số liệu)
- [ ] Dự trù câu hỏi giảng viên có thể hỏi (sau cả nhóm: rehearsal)

### DoD cuối Tuần 8 (= Nộp Pha 2)
- [ ] Báo cáo so sánh trước/sau đầy đủ số liệu + lý giải (chờ C: tổng hợp; A/B duyệt phần mình)
- [ ] Code cải tiến đã merge vào `main`, tag `v2.0-phase2` (chờ A/B/C: merge + CI xanh; B tag cuối)
- [ ] Slide + demo đã rehearsal ít nhất 1 lần trong nhóm (chờ cả nhóm: rehearsal và chốt sửa)

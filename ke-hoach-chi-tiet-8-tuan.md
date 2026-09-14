# Kế hoạch chi tiết 8 tuần — Face Check-in Backend (nhóm 3 người)

> Tài liệu này là bản **"thi công"** đi kèm bản **"thiết kế"** [de-xuat-he-thong-va-plan-8-tuan.md](de-xuat-he-thong-va-plan-8-tuan.md). Đọc file đó trước để hiểu kiến trúc, API, stack; đọc file này để biết lịch làm việc và phân công cụ thể theo từng tuần, từng người. Không lặp lại nội dung kiến trúc/API/stack đã có ở file đó — chỉ trích dẫn khi cần ra quyết định phụ thuộc.

## 1. Mục tiêu & phạm vi tài liệu

Khi đọc xong tài liệu này, mỗi thành viên biết chính xác: **tuần này mình phải làm gì, xong khi nào được coi là Done (DoD), và đang chờ ai / đang bị ai chờ.**

## 2. Quyết định đã chốt

| Hạng mục | Quyết định |
|---|---|
| Nghiệp vụ | Check-in bằng khuôn mặt (`User`, `FaceProfile`, `CheckInRecord`) |
| Kịch bản Pha 2 | Giả định **có tráo đổi hệ thống** giữa các nhóm — áp dụng toàn bộ checklist bàn giao |
| Stack | FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL + JWT (giữ nguyên đề xuất gốc) |
| Vai trò | A = Data/Repository/DB/load-test; B = API/Auth-Security/Docker-CI; C = Service-logic/Face-embedding/tài liệu OpenAPI, dẫn dắt Pha 2 |
| Quy ước lịch | "Tuần N" — nhóm tự gắn ngày dương lịch cụ thể khi khởi động, không thay đổi thứ tự |

**Việc phải làm ngay đầu Tuần 1, không được hoãn:** hỏi giảng viên xác nhận chính thức việc tráo đổi hệ thống Pha 2 có diễn ra không, và có giới hạn cùng stack công nghệ hay không. Nếu câu trả lời khác với giả định trên, cập nhật lại mục 8 (checklist bàn giao) — mọi phần khác của kế hoạch không đổi.

## 3. Ma trận vai trò tổng quan (RACI rút gọn)

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

## 4. WBS chi tiết theo tuần

Mỗi tuần có: **Mục tiêu**, **Việc cụ thể theo người**, **Phụ thuộc/bàn giao**, **Definition of Done (DoD)**.

---

### Tuần 1 — Khởi động & Thiết kế

Mục tiêu: chốt use-case chi tiết, ERD, khung repo 3 tầng, board quản lý việc.

Cả nhóm (1 buổi họp kickoff đầu tuần):
- Xác nhận với giảng viên về tráo đổi Pha 2 + giới hạn stack (xem mục 2).
- Vẽ ERD: `User(id, email, hashed_password, role, full_name, created_at)`, `FaceProfile(id, user_id FK, embedding, created_at)`, `CheckInRecord(id, user_id FK, checkin_time, similarity_score, status)`.
- Review lại sơ đồ kiến trúc 3 tầng trong đề xuất gốc, thống nhất tên thư mục: `app/api`, `app/services`, `app/repositories`, `app/models`, `app/schemas`, `tests/`.
- Tạo repo GitHub công khai + branch protection cho `main` + GitHub Projects board (cột: Backlog/To Do/In Progress/Review/Done) + tạo issue cho toàn bộ WBS Tuần 2–8 (tiêu đề + assignee + label tuần).

Theo người:
- **A**: viết ERD thành file `docs/erd.md` (mermaid) + draft SQLAlchemy models (chưa cần chạy) + `alembic init`.
- **B**: khởi tạo FastAPI skeleton, `.env.example`, `pydantic-settings`, pre-commit (ruff/black), GitHub Actions skeleton (chạy lint, chưa cần test).
- **C**: viết đặc tả use-case (đăng ký khuôn mặt, check-in, xem lịch sử) dạng sequence ngắn; khảo sát & chốt model embedding (buffalo_s/InsightFace hay MobileFaceNet), chạy thử offline 1 ảnh để xác nhận chạy được trên CPU thường (không cần GPU).

DoD cuối Tuần 1:
- [ ] `docs/architecture.md` + `docs/erd.md` đã commit.
- [ ] Repo skeleton push lên, CI lint chạy xanh.
- [ ] Board có đủ issue cho Tuần 2–8.
- [ ] Đã có câu trả lời (hoặc ghi nhận "chưa trả lời, giả định X") từ giảng viên về tráo đổi Pha 2.
- [ ] Đã chốt model embedding cụ thể (tên + kích thước + license).

---

### Tuần 2 — Data layer

Mục tiêu: CRUD qua Repository chạy được cho cả 3 entity.

Phụ thuộc: B/C cần A hoàn thành Repository interface (ABC) trước cuối tuần để không bị chặn ở Tuần 3.

Theo người:
- **A** (chính): SQLAlchemy models thật (không phải draft), Alembic migration đầu tiên chạy được trên Postgres + SQLite, Repository **interface** (ABC, framework-free) cho `UserRepository`, `FaceProfileRepository`, `CheckInRepository`, và **implementation** SQLAlchemy cho cả 3. Viết script/test thủ công (`scripts/manual_test_repo.py`) chứng minh CRUD chạy qua repository.
- **B**: dựng docker-compose cho Postgres dev, hỗ trợ A test kết nối, bắt đầu FastAPI router rỗng (chưa nối service) để sẵn sàng Tuần 3.
- **C**: viết interface cho hàm sinh embedding (`FaceEmbedder` abstract, chưa cần tối ưu) độc lập với DB, để Tuần 3 cắm vào Service layer; bắt đầu viết Pydantic schema request/response cho 3 entity.

DoD cuối Tuần 2:
- [ ] Repository interface + impl cho 3 entity, có test thủ công log lại (screenshot hoặc script output) chứng minh CRUD chạy được.
- [ ] Migration chạy sạch từ DB rỗng (`alembic upgrade head` trên máy sạch).
- [ ] `FaceEmbedder` interface sẵn sàng, chưa cần hoàn chỉnh implementation.

---

### Tuần 3 — Service layer + API layer

Mục tiêu: toàn bộ endpoint CRUD cơ bản chạy qua `/docs` (chưa có auth).

Phụ thuộc: cần Repository (Tuần 2, A) đã xong; C cần B dựng router skeleton xong.

Theo người:
- **A**: hỗ trợ B/C khi có vướng mắc về Repository, bắt đầu viết script load test khung (chưa chạy thật, chỉ dựng cấu trúc `locustfile.py` hoặc `benchmark.py`).
- **B**: FastAPI routers cho `/users`, `/face-profiles`, `/checkins` (chưa auth), exception handler chuẩn (400/404/422), versioning `/api/v1/...`.
- **C** (chính): Service layer thuần Python — `UserService`, `FaceProfileService` (gọi `FaceEmbedder` + Repository), `CheckInService` (so khớp embedding, tính similarity). **Không import FastAPI/SQLAlchemy trong tầng này** — đây là ràng buộc bắt buộc của đề bài, kiểm tra kỹ.

DoD cuối Tuần 3:
- [ ] Toàn bộ endpoint CRUD cơ bản (POST/GET/DELETE cho 3 entity) chạy qua `/docs`, test tay bằng Swagger UI thành công.
- [ ] Service layer không có import framework/DB — kiểm tra bằng mắt hoặc `grep` nhanh (chính thức hóa bằng `import-linter` ở Tuần 4/5, xem mục 8 đề xuất gốc).
- [ ] Face embedding thật (không mock) chạy được end-to-end: upload ảnh → sinh embedding → lưu DB.

---

### Tuần 4 — Auth, RBAC, Unit test

Mục tiêu: 1 GET + 1 POST có auth hoạt động; test pass cho service layer.

Phụ thuộc: đây là điểm dễ lệch chuẩn kiến trúc nhất → **cả nhóm pair lại** (theo khuyến nghị đề xuất gốc) ít nhất nửa buổi để thống nhất cách implement dependency injection cho auth, tránh mỗi người viết một kiểu.

Theo người:
- **A**: thêm field `role` cho User nếu chưa có, viết migration cập nhật, hỗ trợ seed data user mẫu (`admin`, `user`).
- **B** (chính): JWT (login, hash bcrypt/argon2), `Depends(get_current_user)` dùng chung ở router (không copy code từng handler), RBAC theo role, cân nhắc thêm `BaseHTTPMiddleware` chặn `/protected/*` để chắc chắn đúng tinh thần "middleware" của đề bài.
- **C**: viết unit test cho Service layer bằng mock Repository (không đụng DB thật) — coverage tối thiểu cho các use-case chính (đăng ký khuôn mặt, check-in thành công/thất bại).

DoD cuối Tuần 4:
- [ ] `POST /face-profiles` và `GET /checkins` (hoặc endpoint tương đương) yêu cầu JWT, test bằng Postman/Swagger xác nhận 401 khi không có token.
- [ ] RBAC hoạt động: user thường không xóa được record của người khác/không tạo được user mới.
- [ ] Unit test service layer chạy pass trong CI (không chỉ local).
- [ ] Auth code không bị copy-paste lặp ở từng handler — xác nhận bằng review chéo.

---

### Tuần 5 — Docker hóa, README, Integration test

Mục tiêu: `docker compose up` chạy được từ máy sạch.

Theo người:
- **A**: integration test cho Repository (test thật với SQLite/Postgres test container).
- **B** (chính): `Dockerfile` multi-stage, `docker-compose.yml` (app + Postgres + Redis dự phòng Pha 2), test lại trên máy khác/máy sạch trong nhóm (không chỉ máy đã dev).
- **C**: viết README bản đầy đủ theo mục 10 đề xuất gốc (kiến trúc, đặc tả API, hướng dẫn chạy, ADR ngắn), bắt đầu ADR ghi lại các quyết định dễ gây hiểu lầm (vd. vì sao chọn model embedding X, vì sao auth implement kiểu Y).

DoD cuối Tuần 5:
- [ ] `docker compose up` chạy thành công trên **máy chưa từng cài project** (nhờ người thứ 3 trong nhóm test chéo, không phải người viết docker-compose tự test).
- [ ] README có đủ 7 mục theo mục 10 đề xuất gốc (trừ phần benchmark — sẽ bổ sung Tuần 6).
- [ ] Integration test chạy trong CI, không chỉ unit test.

---

### Tuần 6 — Load test + Bàn giao Pha 1

Mục tiêu kép: (1) đo baseline hiệu năng trên Kaggle CPU, (2) hoàn thiện toàn bộ checklist bàn giao vì hệ thống sẽ bị tráo đổi.

Theo người (nửa đầu tuần — benchmark):
- **A** (chính): hoàn thiện script benchmark (locust hoặc `httpx`/`asyncio` tự viết), chạy trên Kaggle CPU notebook, đo p50/p95/p99 latency, throughput, CPU usage theo số concurrent users. Lưu kết quả dạng bảng/CSV, không chỉ ảnh chụp màn hình.
- **B**: hỗ trợ A dựng môi trường chạy app trong Kaggle notebook (uvicorn background process hoặc TestClient/httpx.AsyncClient).
- **C**: viết báo cáo baseline (biểu đồ + nhận xét ngắn) để đưa vào README.

Theo người (nửa cuối tuần — checklist bàn giao, xem mục 8 để biết ai làm gì):
- Cả nhóm cùng rà lại checklist mục 8, mỗi dòng có 1 người chịu trách nhiệm ký xác nhận.
- **C** (chính): hoàn thiện ADR, xuất `openapi.json` tĩnh, viết seed script/data mẫu.
- **B**: tag Git `v1.0-phase1`, rà soát không có secret thật bị commit.
- **A**: đóng gói script + số liệu benchmark kèm hướng dẫn chạy lại rõ ràng.

DoD cuối Tuần 6 (= Nộp/Bàn giao Pha 1):
- [ ] Toàn bộ checklist mục 8 đã tick, có người ký tên phụ trách từng dòng.
- [ ] Repo gắn tag `v1.0-phase1`.
- [ ] Báo cáo benchmark baseline (số liệu + cách chạy lại) đã có trong README hoặc `docs/benchmark-phase1.md`.
- [ ] Đã nhận hệ thống từ nhóm khác (nếu tráo đổi diễn ra đúng lịch nhà trường).

---

### Tuần 7 — Onboarding hệ thống mới nhận + Chọn & triển khai cải tiến Pha 2

Mục tiêu: xác nhận lại baseline trên hệ thống mới nhận, chọn 2–3 cải tiến, triển khai xong (chưa cần đo lại).

Ngày đầu tuần (cả nhóm, ưu tiên cao nhất — không bỏ qua dù có áp lực tiến độ):
- Đọc README/ADR của nhóm bàn giao, chạy `docker compose up`, chạy thử toàn bộ endpoint qua Swagger.
- **Tự đo lại baseline** bằng đúng script benchmark của nhóm cũ, trên đúng loại Kaggle CPU instance — đối chiếu với số liệu họ để lại. Nếu chênh lệch lớn, ghi rõ nghi vấn nguyên nhân (khác thao tác đo, khác thời điểm, khác tải nền của Kaggle) vào `docs/benchmark-reconciliation.md`.

Phân tích & chọn cải tiến (dựa bảng mục 9 đề xuất gốc), khuyến nghị chọn theo thế mạnh của nhóm:
1. Tối ưu suy luận face embedding (ONNX + quantization, cache embedding) — do **C** dẫn dắt.
2. Cache Redis cho GET đọc nhiều + async DB driver — do **A** dẫn dắt.
3. Multi-worker (Gunicorn+Uvicorn) so sánh 1 vs N worker — do **B** dẫn dắt.

(Chỉ chọn 2–3 trong số này hoặc từ bảng mục 9, tùy điểm nghẽn thực tế đo được ở hệ thống mới nhận — không chọn cứng trước khi đo.)

Theo người (triển khai, cuối tuần):
- **A**: implement cải tiến performance/scalability đã chọn (cache/async driver/worker).
- **B**: implement cải tiến còn lại thuộc mảng mình phụ trách (vd. rate limiting nếu chọn security) + đảm bảo docker-compose vẫn chạy được với thay đổi mới (Redis, thêm worker).
- **C**: implement cải tiến ML/inference nếu chọn, đồng thời bắt đầu viết khung báo cáo so sánh trước/sau.

DoD cuối Tuần 7:
- [ ] Baseline hệ thống mới nhận đã được xác nhận lại, có giải thích cho mọi chênh lệch so với số liệu nhóm cũ để lại.
- [ ] 2–3 cải tiến đã chọn, có lý do bằng văn bản (dựa trên baseline, không phải "nghe nói cái này nhanh hơn").
- [ ] Cải tiến chạy được (chưa cần đo lại số liệu).

---

### Tuần 8 — Đo lại, so sánh, báo cáo, demo

Mục tiêu: nộp Pha 2.

Theo người:
- **A**: chạy lại benchmark **đúng cấu hình Kaggle CPU** như Tuần 6/7, xuất số liệu so sánh trước/sau cho phần cải tiến mình phụ trách.
- **B**: tương tự cho phần mình phụ trách (vd. so sánh 1 vs N worker, hoặc số liệu rate limiting chặn brute-force).
- **C** (chính): tổng hợp toàn bộ số liệu thành báo cáo so sánh trước/sau + lý giải nguyên nhân cải thiện (không chỉ nêu số, phải giải thích *tại sao* — vd. "giảm p95 từ Xms xuống Yms nhờ cache vì Z% request là đọc lặp lại"), chuẩn bị slide + kịch bản demo.

Buffer 1–2 ngày cuối tuần: cả nhóm rehearsal demo, dự trù câu hỏi giảng viên có thể hỏi (vd. "tại sao không chọn cải tiến khác trong bảng mục 9?").

DoD cuối Tuần 8 (= Nộp Pha 2):
- [ ] Báo cáo so sánh trước/sau đầy đủ số liệu + lý giải, dựa trên hệ thống nhận từ nhóm khác.
- [ ] Code cải tiến đã merge vào `main`, tag `v2.0-phase2`.
- [ ] Slide + demo đã rehearsal ít nhất 1 lần trong nhóm.

## 5. Điểm bàn giao/phụ thuộc giữa 3 người (không được trễ)

| Ai bàn giao gì | Cho ai | Chậm nhất cuối |
|---|---|---|
| Repository interface + impl (3 entity) | B, C | Tuần 2 |
| `FaceEmbedder` interface | C tự dùng, nhưng B cần biết chữ ký hàm để nối API | Tuần 2 |
| Router skeleton | C (để nối Service vào) | Tuần 2 (đầu Tuần 3) |
| Service layer hoàn chỉnh | B (để nối auth/RBAC vào đúng chỗ) | Tuần 3 |
| Auth dependency (`get_current_user`) | A, C (dùng chung, không tự viết lại) | Tuần 4 |
| docker-compose chạy được | A, C (để test integration, để chạy Kaggle) | Tuần 5 |
| Script benchmark + baseline | Nhóm nhận hệ thống ở Pha 2 (qua bàn giao) | Tuần 6 |

## 6. Theo dõi tiến độ

- Mỗi task trong WBS ở mục 4 = 1 issue trên GitHub Projects, gắn label `Tuần-N`, assignee đúng người phụ trách.
- Sync ngắn cuối mỗi tuần (15–20 phút): mỗi người trả lời 3 câu — làm gì tuần này, có gì chặn, có kịp DoD không. Nếu không kịp, dời task sang đầu tuần sau **và** báo ngay cho người đang phụ thuộc vào mình (xem mục 5) — không để họ tự phát hiện ra khi đã trễ.
- Buffer đã có sẵn trong lịch: Tuần 5 (docker/README) và Tuần 8 (buffer 1–2 ngày cuối) là 2 tuần ít rủi ro nhất, có thể hấp thụ chậm trễ nhỏ từ tuần trước mà không cần xin gia hạn.
- Nếu trễ hơn 1 tuần so với WBS ở bất kỳ mốc nào thuộc Tuần 1–4 (phần lõi kiến trúc), ưu tiên cắt giảm phạm vi ở mục 8 đề xuất gốc (điểm cộng: import-linter, CI đầy đủ, idempotency key) trước khi cắt giảm phần lõi (auth, layering, Docker) — vì phần lõi là yêu cầu bắt buộc của đề bài, phần điểm cộng thì không.

## 7. Rủi ro chính & phương án dự phòng

| Rủi ro | Tác động | Phương án dự phòng |
|---|---|---|
| Model embedding không chạy nhẹ trên Kaggle CPU như kỳ vọng | Chặn benchmark Tuần 6 | Đã yêu cầu C xác nhận chạy được trên CPU ngay Tuần 1 (không đợi tới Tuần 6 mới phát hiện) |
| Giảng viên xác nhận **không** tráo đổi hệ thống | Tốn công vô ích cho checklist bàn giao | Không lãng phí nhiều — checklist bàn giao (README tốt, ADR, seed data) vẫn hữu ích cho chính nhóm ở Pha 2, không mất công |
| Hệ thống nhận từ nhóm khác dùng stack lạ (không phải Python) | Tuần 7 mất nhiều thời gian đọc hiểu hơn dự kiến | Đã dành nguyên ngày đầu Tuần 7 chỉ để onboarding, không xen task khác; nếu vẫn không kịp, báo giảng viên xin thêm buffer thay vì tự cắt góc |
| Auth bị viết lặp ở nhiều handler (vi phạm yêu cầu đề bài) | Mất điểm yêu cầu bắt buộc | Bắt buộc pair session Tuần 4 + review chéo trước khi merge |
| Số liệu benchmark Pha 1 vs Pha 2 không cùng điều kiện đo | Mất giá trị so sánh, vi phạm yêu cầu đề bài "cùng cấu hình phần cứng" | A giữ nguyên script + hướng dẫn chạy lại chính xác giữa Tuần 6 và Tuần 8, không đổi loại Kaggle instance |

## 8. Checklist bàn giao Pha 1 (gán người phụ trách)

Dựa trên mục 11 của đề xuất gốc, mỗi dòng gán 1 người chịu trách nhiệm ký xác nhận trước khi tag `v1.0-phase1`:

| Việc | Phụ trách |
|---|---|
| `docker compose up` chạy được trên máy hoàn toàn sạch | B |
| Seed script/data mẫu | C |
| Swagger UI đầy đủ endpoint + ví dụ request/response | C |
| Xuất `openapi.json` tĩnh | C |
| Script/lệnh benchmark có hướng dẫn chạy lại + số liệu baseline đã lưu | A |
| Tag Git `v1.0-phase1` | B |
| ADR các quyết định dễ hiểu lầm | C (với input từ A, B cho phần thuộc mảng của mình) |
| Không có secret thật bị commit | B (rà soát cuối cùng trước khi tag) |

## 9. Deliverables nộp bài

- **Cuối Tuần 6 (Pha 1)**: repo tag `v1.0-phase1`, README đầy đủ, báo cáo benchmark baseline.
- **Cuối Tuần 8 (Pha 2)**: repo tag `v2.0-phase2`, báo cáo so sánh trước/sau + lý giải, slide, demo.

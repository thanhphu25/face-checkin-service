# Kế hoạch commit Tuần 2–8

> Nguồn công việc: [checklist-tien-do-8-tuan.md](checklist-tien-do-8-tuan.md).
> File này quy đổi checklist thành thứ tự commit thực tế để một người lần lượt đóng vai A, B và C mà không làm sai dependency hoặc sửa chồng cùng file.

## 1. Quy ước chung

Mỗi commit phải:

1. Chỉ giải quyết một thay đổi logic có thể review độc lập.
2. Cập nhật mục tương ứng trong `changelog.md`, đặt commit mới nhất lên đầu.
3. Tick các dòng checklist thực sự đã hoàn thành trong cùng commit.
4. Chạy test liên quan, `ruff check`, `ruff format --check` và `lint-imports` trước khi commit.
5. Không tick DoD chỉ vì code đã viết; chỉ tick sau khi đã chạy kịch bản xác nhận.

Thứ tự trong từng tuần là thứ tự merge/commit. Khi có thể làm song song, vẫn phải nhập vào branch tích hợp theo thứ tự bảng để `changelog.md` và checklist không conflict.

### File dùng chung cần một người sửa tại một thời điểm

| File/phạm vi | Quy tắc sở hữu |
|---|---|
| `app/domain/ports.py` | A hoàn tất Repository port trước; C chỉ thêm `FaceEmbedder` sau đó |
| `app/api/deps.py`, `app/main.py` | B sở hữu khi lắp dependency/API |
| `compose.yaml` hoặc `docker-compose.yml` | Chỉ B sửa; A/C bàn giao biến môi trường cần thêm |
| `scripts/benchmark.py` | A sở hữu; B không sửa song song khi chạy benchmark chuyên biệt |
| `README.md`, `docs/adr/` | C sở hữu; A/B cung cấp nội dung và review |
| `changelog.md`, checklist | Người tạo commit cập nhật sau khi đã lấy phiên bản mới nhất |

Sau khi một commit đã push, không amend/rebase commit đó trừ khi cả nhóm chủ động quyết định viết lại lịch sử. Mặc định dùng commit tiếp theo.

## 2. Tổng số commit dự kiến

| Tuần | Số commit | Ghi chú |
|---|---:|---|
| Tuần 2 | 8 | `W2-C01` đã hoàn thành; còn 7 commit |
| Tuần 3 | 8 | Service, ML adapter, API và kiểm chứng end-to-end |
| Tuần 4 | 5 | Auth, RBAC và unit/API test |
| Tuần 5 | 6 | Integration test, Docker và tài liệu |
| Tuần 6 | 7 | Baseline, bàn giao và tag Pha 1 |
| Tuần 7 | 6–7 | Phụ thuộc chọn 2 hay 3 cải tiến |
| Tuần 8 | 4–5 | Benchmark chuyên biệt của B chỉ có khi cải tiến tương ứng được chọn |
| **Tổng** | **44–46** | **Còn 43–45 sau `W2-C01`** |

## 3. Tuần 2 — Data layer

Mục tiêu cuối tuần: migration chạy trên SQLite/Postgres và CRUD của ba entity chạy hoàn toàn qua Repository.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W2-C01` | A | `feat(domain): add entities and repository ports` | Domain entity, enum và ba Repository ABC | Đã hoàn thành |
| `W2-C02` | C | `feat(domain): add face embedder port` | Thêm `FaceEmbedder` với `model_name` và `embed(image_bytes)` | Sau `W2-C01`; cùng sửa `ports.py` nên không làm song song |
| `W2-C03` | B | `chore(dev): add PostgreSQL compose service` | Postgres dev, volume, healthcheck và biến môi trường mẫu | Không phụ thuộc code; merge trước lúc test migration Postgres |
| `W2-C04` | A | `feat(db): finalize models and add initial migration` | Chốt ORM, migration đầu tiên; chạy upgrade → downgrade → upgrade trên SQLite và Postgres | Sau `W2-C03` |
| `W2-C05` | A | `feat(repo): implement SQLAlchemy repositories` | Mapper ORM ↔ domain và implementation của ba repository | Sau `W2-C01`, `W2-C04` |
| `W2-C06` | C | `feat(schema): add API request and response schemas` | Schema ba entity; không lộ hash mật khẩu hoặc embedding | Sau `W2-C01` |
| `W2-C07` | B | `feat(api): scaffold v1 resource routers` | Router rỗng cho users, face profiles, check-ins; chưa có nghiệp vụ | Sau `W2-C06` để không đổi contract hai lần |
| `W2-C08` | A | `test(repo): add CRUD smoke script and close week 2` | Script CRUD qua repository, log kết quả, chạy lại migration và xác nhận DoD | Sau toàn bộ commit Tuần 2 |

Điểm đóng tuần:

- `alembic upgrade head`, `downgrade base`, rồi `upgrade head` chạy sạch trên cả hai DB.
- Script tạo/đọc/liệt kê/xóa cả ba entity qua port, không truy cập ORM từ bên ngoài repository.
- B review chữ ký `FaceEmbedder`; A/B xác nhận Postgres; checklist và changelog đã cập nhật.

## 4. Tuần 3 — Service layer và API layer

Mục tiêu cuối tuần: CRUD cơ bản chạy qua `/api/v1` và face embedding thật chạy end-to-end.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W3-C01` | C | `feat(ml): implement InsightFace embedder` | Adapter InsightFace, chuẩn hóa vector float32/L2 và ánh xạ lỗi không thấy mặt | `W2-C02` |
| `W3-C02` | C | `feat(service): implement user service` | Tạo/đọc/liệt kê/xóa user, chuẩn hóa email; chỉ import domain | `W2-C05` |
| `W3-C03` | C | `feat(service): implement face profile service` | Đăng ký/xóa/list profile qua `FaceEmbedder` và repository | `W3-C01`, `W2-C05` |
| `W3-C04` | C | `feat(service): implement check-in service` | So khớp cosine, ba trạng thái check-in và truy vấn lịch sử | `W3-C01`, `W2-C05` |
| `W3-C05` | B | `feat(api): add v1 composition root and error handlers` | Versioning, session/dependency factories và map domain error sang 400/404/422 | `W3-C02`–`W3-C04` |
| `W3-C06` | B | `feat(api): implement resource routers` | Endpoint users, face profiles và check-ins nối Service → Repository | `W3-C05` |
| `W3-C07` | A | `perf(benchmark): scaffold API load harness` | Khung benchmark dùng URL/path cuối cùng, chưa thu số liệu baseline | `W3-C06` |
| `W3-C08` | A/B/C | `test(api): verify CRUD and face embedding flow` | Test/manual evidence qua Swagger, kiểm tra boundary Service và đóng DoD | Sau toàn bộ commit Tuần 3 |

Quy tắc tránh conflict:

- C hoàn tất từng service trước khi B nối service đó vào composition root.
- Chỉ B sửa `app/api/deps.py`, router và `app/main.py` trong tuần này.
- Chỉ A sửa harness benchmark sau khi B đã chốt toàn bộ URL.
- A hỗ trợ lỗi Repository ngay tại commit đang bị chặn, không tạo một commit “support” rỗng.

## 5. Tuần 4 — Auth, RBAC và unit test

Mục tiêu cuối tuần: auth dùng chung hoạt động, RBAC đúng và test chạy trong CI.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W4-C01` | A/B/C | `docs(auth): record dependency injection and sample-user contract` | Kết quả pair session, xác nhận field `role`, spec user mẫu và quyết định có/không dùng middleware | Tuần 3 hoàn tất |
| `W4-C02` | B | `feat(auth): add password hashing and JWT login` | Password hasher, encode/decode JWT, `/auth/login` và `/auth/me` | `W4-C01`, `UserService` |
| `W4-C03` | B/C | `feat(auth): add shared authentication and RBAC` | `get_current_user`, `require_admin`, rule sở hữu ở Service và bảo vệ router | `W4-C02` |
| `W4-C04` | C | `test(service): cover face registration and check-in outcomes` | Repository/embedder giả; đăng ký mặt, check-in thành công và thất bại | Service Tuần 3 ổn định |
| `W4-C05` | B | `test(auth): verify protected endpoints and close week 4` | Test 401/403/RBAC, xác nhận CI chạy pytest, review không copy auth và tick DoD | `W4-C03`, `W4-C04` |

Lưu ý:

- `role` đã có trong ERD/model thì không tạo migration rỗng; chỉ ghi nhận xác nhận trong `W4-C01`.
- Nếu chọn middleware, B thực hiện trong `W4-C03`; không tạo một cơ chế auth thứ hai cho cùng đường dẫn.
- C sở hữu test Service; B sở hữu test HTTP/auth và workflow CI.

## 6. Tuần 5 — Docker, README và integration test

Mục tiêu cuối tuần: máy sạch chạy được toàn hệ thống bằng Docker Compose.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W5-C01` | A | `test(repo): add SQLite and PostgreSQL integration tests` | Mapping, CRUD, cascade/SET NULL và filter repository trên DB thật | Repository/migration ổn định |
| `W5-C02` | B | `build(docker): add multi-stage application image` | Dockerfile build/runtime, non-root nếu phù hợp, healthcheck app | Dependencies Tuần 4 ổn định |
| `W5-C03` | B | `build(compose): run app with PostgreSQL and Redis` | Mở rộng Compose Tuần 2 thành app + DB + Redis; migration bằng lệnh rõ ràng | `W5-C02`, migration Postgres |
| `W5-C04` | C | `docs(adr): record database auth and embedding decisions` | ADR cho DB, auth, embedding và các quyết định dễ hiểu nhầm | Input từ A/B |
| `W5-C05` | C | `docs(readme): document architecture API and local setup` | Kiến trúc, API, hướng dẫn chạy, env, tài khoản mẫu placeholder và link ADR | `W5-C03`, API/auth ổn định |
| `W5-C06` | A/B/C | `ci: run integration tests and verify clean setup` | Nối integration test vào CI, test chéo trên máy sạch và đóng DoD | Sau toàn bộ commit Tuần 5 |

Quy tắc tránh conflict:

- B là người duy nhất sửa Dockerfile/Compose; A chỉ cung cấp lệnh test DB.
- C chỉ chốt README sau khi Compose của B chạy được, tránh tài liệu đi trước hành vi thật.
- Nếu kiểm thử máy sạch phát hiện lỗi, sửa bằng commit có scope đúng trước khi tick `W5-C06`.

## 7. Tuần 6 — Baseline và bàn giao Pha 1

Mục tiêu cuối tuần: có baseline tái lập được, bộ bàn giao đầy đủ và tag `v1.0-phase1`.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W6-C01` | A/B | `perf(benchmark): finalize Kaggle CPU harness` | Hoàn thiện script, notebook/setup Kaggle, concurrency và thu latency/throughput/CPU | API/auth ổn định |
| `W6-C02` | A | `perf(results): add phase 1 baseline data` | CSV/raw result, metadata phần cứng và tham số chạy | Chạy xong `W6-C01` |
| `W6-C03` | C | `docs(benchmark): report phase 1 baseline` | Biểu đồ, p50/p95/p99, throughput, CPU và nhận xét | `W6-C02` |
| `W6-C04` | C | `feat(seed): add reproducible sample data` | Seed admin/user, face profile và check-in mẫu, không chứa secret thật | Schema/auth cuối cùng |
| `W6-C05` | C | `docs(api): export OpenAPI and finalize ADRs` | `openapi.json`, ví dụ Swagger và ADR hoàn chỉnh | API cuối cùng, review A/B |
| `W6-C06` | A | `docs(handoff): document benchmark reproduction` | Đóng gói script/số liệu và hướng dẫn chạy lại chính xác | `W6-C01`–`W6-C03` |
| `W6-C07` | B | `chore(release): finalize phase 1 handoff` | Rà secret, chạy Compose/seed/Swagger/CI từ sạch, ký checklist và đóng DoD | Tất cả commit Tuần 6 |

Sau `W6-C07` và CI xanh:

1. B tạo tag `v1.0-phase1` — tag là thao tác release, không phải commit riêng.
2. Không ai push thêm vào tag đã phát hành.
3. Cả nhóm nhận hệ thống mới và bắt đầu quy trình Tuần 7.

## 8. Tuần 7 — Onboarding và triển khai cải tiến Pha 2

Tuần này diễn ra trên hệ thống được bàn giao. Không chọn trước cải tiến; commit cải tiến chỉ được tạo sau khi đo lại baseline.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W7-C01` | A/C | `docs(benchmark): reconcile received-system baseline` | Ghi việc đọc README/ADR, chạy Compose/Swagger, số đo lại và giải thích chênh lệch | Nhận hệ thống mới |
| `W7-C02` | A/B/C | `docs(phase2): select measured improvements` | Chọn 2–3 cải tiến, metric mục tiêu, owner, file sở hữu và lý do từ baseline | `W7-C01` |
| `W7-C03` | A | `perf(data): implement selected data-layer improvement` | Cache Redis/async driver/pool tuning nếu được chọn; kèm test | `W7-C02` |
| `W7-C04` | C | `perf(ml): implement selected inference improvement` | ONNX/quantization/batch/cache embedding nếu được chọn; kèm test | `W7-C02` |
| `W7-C05` | B | `perf(deploy): implement selected deployment improvement` | Multi-worker/rate limiting nếu được chọn; kèm test/cấu hình | `W7-C02` |
| `W7-C06` | B | `build(compose): integrate phase 2 configuration` | Tích hợp biến môi trường/service mới và xác nhận Compose còn chạy | Các commit cải tiến đã chọn |
| `W7-C07` | C | `docs(phase2): scaffold comparison report and close week 7` | Khung báo cáo, phạm vi đo lại, xác nhận cải tiến chạy được và tick DoD | `W7-C06` |

Chỉ tạo `W7-C03`–`W7-C05` cho cải tiến thực sự được chọn. Vì vậy Tuần 7 có 6 commit nếu chọn 2 cải tiến, hoặc 7 commit nếu chọn cả 3.

Ranh giới file:

- A sở hữu data layer; C sở hữu ML adapter; B sở hữu deployment/Compose.
- B chỉ sửa Compose sau khi A/C đã bàn giao danh sách biến môi trường.
- Mỗi cải tiến phải nằm trong commit riêng và có test riêng để có thể revert/đo độc lập.

## 9. Tuần 8 — Đo lại, báo cáo và demo

Mục tiêu cuối tuần: có so sánh trước/sau hợp lệ, demo đã rehearsal và tag `v2.0-phase2`.

| ID | Vai | Commit message | Nội dung chính | Phụ thuộc |
|---|---|---|---|---|
| `W8-C01` | A | `perf(results): add post-improvement benchmark data` | Chạy đúng cấu hình/harness cũ, lưu raw data và bảng trước/sau | Toàn bộ cải tiến Tuần 7 đã merge |
| `W8-C02` | B | `perf(results): compare deployment configurations` | Benchmark 1/N worker hoặc rate limiting nếu cải tiến B được chọn | Harness của A đã khóa; B không sửa song song |
| `W8-C03` | C | `docs(report): finalize phase 2 comparison` | Tổng hợp số liệu, biểu đồ, lý giải và hạn chế; A/B duyệt phần mình | `W8-C01` và `W8-C02` nếu có |
| `W8-C04` | C | `docs(demo): add slides and rehearsal script` | Slide, kịch bản demo, câu hỏi dự kiến và phân vai | `W8-C03`, demo env của B |
| `W8-C05` | A/B/C | `chore(release): finalize phase 2 delivery` | Sửa lỗi từ rehearsal, chạy CI/demo lần cuối, tick DoD và chốt release | `W8-C04` |

Nếu không chọn cải tiến deployment của B thì bỏ `W8-C02`, nên Tuần 8 còn 4 commit.

Sau `W8-C05` và CI xanh, B merge vào `main` rồi tạo tag `v2.0-phase2`. Tag không thay thế commit kiểm chứng cuối cùng.

## 10. Chuỗi dependency tổng quát

```text
Tuần 2: Domain → DB/Migration → Repository → Schema/Router → CRUD proof
   ↓
Tuần 3: ML adapter + Repository → Services → API/DI → End-to-end proof
   ↓
Tuần 4: Auth design → JWT → Shared auth/RBAC → Tests/CI
   ↓
Tuần 5: Integration tests + Image → Compose → README/ADR → Clean-machine proof
   ↓
Tuần 6: Benchmark harness → Raw data → Report/Handoff → v1.0-phase1
   ↓
Tuần 7: Re-measure received system → Select improvements → Implement → Compose proof
   ↓
Tuần 8: Re-benchmark → Compare/report → Slides/demo → v2.0-phase2
```

Khi một dependency chưa đạt, không nhảy sang commit phía sau chỉ để giữ lịch. Ghi blocker vào checklist, hoàn tất commit đang chặn, rồi tiếp tục đúng chuỗi trên.

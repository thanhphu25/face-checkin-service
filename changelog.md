# Changelog

Mỗi commit mới phải thêm một mục ở đầu lịch sử theo định dạng:

```text
## YYYY-MM-DD — type(scope): mô tả ngắn

- Thay đổi chính thứ nhất.
- Thay đổi chính thứ hai.
```

Chỉ ghi thay đổi có ý nghĩa với dự án, viết ngắn gọn và sắp xếp commit mới nhất lên trước.

## 2026-09-22 — docs(handoff): document benchmark reproduction

- Liệt kê đủ gói bàn giao benchmark: harness, runner, seed, nguồn ảnh mẫu và số liệu Tuần 6.
- Thêm lệnh smoke chạy được ngoài Kaggle trong khoảng một phút, đã chạy đúng nguyên văn trước khi ghi vào tài liệu.
- Chốt 5 điều kiện để một lượt đo Tuần 8 được coi là so sánh được với baseline Tuần 6.

## 2026-09-22 — docs(benchmark): report phase 1 baseline

- Thêm `docs/benchmark-phase1.md`: bảng, biểu đồ throughput/p50 cho hai scenario và hai backend, nhận xét và giới hạn của baseline.
- README mục 5 có bảng tóm tắt baseline và ba kết luận chính, thay cho ghi chú "chờ Tuần 6".
- Ghi rõ điểm nghẽn đo được là CPU inference (~200 ms/request) và việc đường đọc để trống hơn nửa máy; không chọn cải tiến Pha 2 ở đây.

## 2026-09-22 — perf(results): add phase 1 baseline data

- Thêm số liệu baseline đo thật trên Kaggle CPU (commit `4affbd0`, 4 core) cho SQLite và PostgreSQL: 16 mức đo, `error_count=0` toàn bộ.
- Sửa cell PostgreSQL trong hướng dẫn Kaggle theo lệnh chạy được thật: image Kaggle cài cluster 14 nên dùng `service postgresql start`.
- Sửa mô tả sai đơn vị CPU: `cpu_percent_system` là phần trăm toàn máy (0–100%), `cpu_percent_server` mới là phần trăm của một core.

## 2026-09-22 — docs(api): export OpenAPI and record benchmark method

- Thêm `scripts/export_openapi.py` và bản `docs/openapi.json` đã commit; test so sánh với app nên schema lệch sẽ fail thay vì âm thầm cũ đi.
- Thêm ADR 0005 ghi điều kiện đo baseline: một worker, hai scenario, hai database, percentile nearest-rank, warm-up và khoảng lặng CPU.
- README trỏ tới OpenAPI tĩnh, quy trình Kaggle và ADR mới; vẫn chưa công bố số liệu vì chưa chạy trên Kaggle.

## 2026-09-22 — perf(benchmark): finalize Kaggle CPU harness

- Nâng `scripts/benchmark.py` từ scaffold Tuần 3 thành harness baseline: sweep nhiều mức concurrency, warm-up riêng, hai scenario `checkin`/`history`, CSV kết quả và metadata phần cứng/tham số.
- Đo CPU toàn máy và CPU riêng tiến trình server từ `/proc`; bỏ qua cửa sổ quá ngắn và chờ `--settle-seconds` sau warm-up để thread pool ONNX không bị tính sang mức đo kế tiếp.
- Thêm `scripts/run_baseline.py` chạy trọn migration → seed → Uvicorn một worker → benchmark → dừng server, và hướng dẫn Kaggle CPU cho cả SQLite lẫn PostgreSQL.

## 2026-09-22 — feat(seed): add reproducible sample data

- Thêm `scripts/seed.py` tạo admin/user mẫu, face profile thật và lịch sử `success`/`unmatched`/`no_face`; chạy lại không nhân đôi dữ liệu.
- Mật khẩu seed đọc từ `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD` và bị từ chối nếu thiếu hoặc quá ngắn; repo không chứa giá trị thật.
- Tách ảnh mẫu InsightFace thành `scripts/sample_images.py` dùng chung cho seed/benchmark, và ghi cách seed vào README cùng `.env.example`.

## 2026-09-22 — ci: run pipeline on the week 6 branch

- Thêm `week6` vào push trigger để pipeline chạy trước khi tag `v1.0-phase1`, thay vì chỉ chạy qua pull request.
- Cập nhật test workflow theo danh sách branch mới và đặt lại tên test cho không gắn cứng vào một tuần.

## 2026-09-22 — docs(checklist): record hosted clean-setup evidence

- Ghi GitHub Actions run `35703077030`: bốn job xanh, gồm Compose build/up/migration/health/HTTP và cleanup trên hosted runner sạch.
- Tick hai tiêu chí máy sạch Tuần 5 theo phương án thay thế được chủ project chấp thuận, không tuyên bố A/C đã test trên máy cá nhân.

## 2026-09-22 — ci: add hosted clean-compose verification

- Thêm job dựng Compose từ đầu trên GitHub-hosted runner, xác minh migration/app/PostgreSQL/Redis/HTTP và kiểm tra cleanup tài nguyên cách ly.
- Ghi technical review auth thay thế được chủ project chấp thuận, đồng thời nói rõ không có pair/review chéo của con người.

## 2026-09-22 — ci: run integration tests and verify clean setup

- Tách CI thành quality/SQLite, PostgreSQL integration bắt buộc và Docker image build; real-model E2E vẫn là verification thủ công có chủ ý.
- Xác minh clone sạch bằng Compose project cách ly, chạy full suite với PostgreSQL/InsightFace thật và ghi bằng chứng cùng cleanup Tuần 5.

## 2026-09-22 — docs(readme): document architecture API and local setup

- Viết lại README thành tài liệu bàn giao gồm phạm vi, kiến trúc, endpoint/quyền, Compose từ máy sạch, test, ADR, env và placeholder account.
- Ghi rõ Redis chưa được app sử dụng, seed/benchmark chờ Tuần 6 và cách dọn project test mà không xóa nhầm dữ liệu dev.

## 2026-09-22 — docs(adr): record database auth and embedding decisions

- Thêm bốn ADR có context, decision, alternatives, consequences và điều kiện xem lại cho data, auth, embedding và ranh giới Pha 1/Pha 2.
- Liên kết ADR từ kiến trúc và cập nhật mô tả transaction theo implementation thật: Repository flush, dependency session commit/rollback.

## 2026-09-22 — build(compose): run app with PostgreSQL and Redis

- Mở rộng Compose thành app, migration one-shot, PostgreSQL 16 và Redis 7 với healthcheck/dependency rõ ràng.
- Dùng volume bền vững cho PostgreSQL/model cache, port cấu hình được và placeholder môi trường; Redis vẫn chỉ là hạ tầng dự phòng Pha 2.

## 2026-09-22 — build(docker): add multi-stage application image

- Thêm image Python 3.12 multi-stage cài production dependency từ `uv.lock`, runtime non-root và healthcheck không cần curl.
- Giảm build context bằng `.dockerignore` để loại secret, database, cache, model/ONNX, ảnh mặt và output tạm.

## 2026-09-22 — test(repo): add SQLite and PostgreSQL integration tests

- Chạy cùng bộ integration test qua Repository, domain mapping và migration thật trên SQLite lẫn PostgreSQL 16 cách ly.
- Bao phủ CRUD, enum, unique email, embedding float32/bytes/dimension/model, cascade/SET NULL, filter, thứ tự, limit và SQLite foreign keys; thêm migration `0002` sửa xung đột giữa CHECK và lịch sử được ẩn danh.

## 2026-09-22 — test(auth): verify protected endpoints and close week 4

- Thêm SQLite API integration cho login/JWT, 401/403/404, ownership/RBAC; kiểm tra OpenAPI security và auth không copy-paste.
- Cập nhật CI cho `week4`, chạy 78 test gồm InsightFace thật và xác minh PostgreSQL cách ly; ghi bằng chứng và đóng phần kỹ thuật Tuần 4.

## 2026-09-21 — test(service): cover face registration and check-in outcomes

- Củng cố fake Repository/FaceEmbedder đúng port cho đăng ký thành công, user thiếu, no-face và multiple-face.
- Bao phủ check-in success/unmatched/no-face, audit thất bại, loại profile sai model/dimension và ownership ở Service.

## 2026-09-21 — feat(auth): add shared authentication and RBAC

- Áp dụng `get_current_user`/`require_admin` dùng chung cho các route được bảo vệ, giữ `POST /checkins` công khai.
- Đưa ownership vào Service, giới hạn user thường ở tài nguyên/lịch sử của mình và phân biệt lỗi 401/403/404.

## 2026-09-21 — feat(auth): add password hashing and JWT login

- Thay hasher tạo mới bằng Argon2id có tương thích PBKDF2 Tuần 3; khóa Argon2/PyJWT và thêm JWT có `sub`, `role`, `iat`, `exp`.
- Thêm đăng nhập không làm lộ email tồn tại, dependency xác thực dùng chung và endpoint `/auth/login`, `/auth/me` không lộ password hash.

## 2026-09-21 — docs(auth): record dependency injection and sample-user contract

- Chốt OAuth2 dependency dùng chung, JWT contract, ma trận endpoint và ownership/RBAC Tuần 4.
- Xác nhận `role` đã có trong domain/ORM/migration `0001`, định nghĩa tài khoản mẫu không chứa secret và giữ các xác nhận pair/review của con người ở trạng thái chưa hoàn tất.

## 2026-09-21 — test(api): verify CRUD and face embedding flow

- Thêm kiểm thử API/OpenAPI, boundary Service và E2E dùng model InsightFace thật qua SQLite.
- Xác minh cùng luồng trên PostgreSQL cách ly, ghi bằng chứng và hoàn tất checklist/DoD Tuần 3.

## 2026-09-21 — perf(benchmark): scaffold API load harness

- Thêm harness async cho endpoint cuối `/api/v1/checkins` với URL, ảnh, request và concurrency cấu hình được.
- Tính throughput cùng p50/p95/p99 tại console; chưa chạy hoặc lưu baseline trước Tuần 6.

## 2026-09-21 — feat(api): implement resource routers

- Hoàn thiện endpoint CRUD users, face profiles và check-ins dưới `/api/v1` chưa có auth.
- Thêm upload JPEG/PNG có giới hạn dung lượng, response không lộ password hash hoặc embedding.

## 2026-09-21 — feat(api): add v1 composition root and error handlers

- Lắp session theo request, Repository, Service, embedder singleton và password hasher qua dependency factory.
- Commit audit cho lỗi nghiệp vụ dự kiến, rollback lỗi hệ thống và map lỗi domain sang HTTP 400/404/422.

## 2026-09-21 — feat(service): implement check-in service

- Thêm cosine matching vector hóa, lọc profile theo model và ngưỡng cấu hình.
- Ghi lịch sử cho cả `success`, `unmatched`, `no_face` và hỗ trợ truy vấn/xóa bản ghi.

## 2026-09-21 — feat(service): implement face profile service

- Thêm đăng ký, liệt kê và xóa hồ sơ khuôn mặt qua các domain port.
- Kiểm tra user tồn tại và củng cố bất biến embedding `float32` đã L2-normalized.

## 2026-09-21 — feat(service): implement user service

- Thêm CRUD người dùng qua Repository port, chuẩn hóa email bằng trim + casefold.
- Băm mật khẩu qua `PasswordHasher` port và trả lỗi domain cho email trùng/không hợp lệ.

## 2026-09-21 — feat(ml): implement InsightFace embedder

- Thêm adapter InsightFace CPU xử lý rõ ảnh lỗi, không có mặt và nhiều mặt.
- Bảo đảm embedding đầu ra luôn liên tục, `float32` và L2-normalized; khóa dependency ML.

## 2026-09-21 — test(repo): add CRUD smoke script and close week 2

- Thêm script tạo/đọc/liệt kê/xóa cả ba entity hoàn toàn qua Repository port.
- Xác nhận migration và CRUD trên SQLite/PostgreSQL, hoàn tất checklist và DoD Tuần 2.

## 2026-09-21 — feat(api): scaffold v1 resource routers

- Thêm router rỗng có prefix ổn định cho users, face profiles và check-ins dưới `/api/v1`.
- Lắp router phiên bản vào FastAPI app, chưa nối service hay nghiệp vụ.

## 2026-09-21 — feat(schema): add API request and response schemas

- Thêm schema request/response cho user, hồ sơ khuôn mặt và lượt check-in.
- Xác thực input, khoảng thời gian truy vấn và bảo đảm response không lộ hash mật khẩu/embedding.

## 2026-09-21 — feat(repo): implement SQLAlchemy repositories

- Thêm mapper ORM ↔ domain và adapter SQLAlchemy cho User, FaceProfile, CheckInRecord.
- Bao phủ CRUD, filter lịch sử, giới hạn kết quả và mã hóa embedding float32 bằng integration test.

## 2026-09-21 — feat(db): finalize models and add initial migration

- Chốt ORM cho ba entity với khóa chính identity tương thích PostgreSQL/SQLite.
- Thêm migration schema đầu tiên và kiểm thử vòng upgrade → downgrade → upgrade trên SQLite.

## 2026-09-21 — chore(dev): add PostgreSQL compose service

- Thêm PostgreSQL 16 cho môi trường dev với volume bền vững và healthcheck.
- Bổ sung biến môi trường mẫu cho database, tài khoản và cổng PostgreSQL.
- Xác thực cấu hình Compose và cập nhật checklist Tuần 2.

## 2026-09-21 — feat(domain): add face embedder port

- Thêm `FaceEmbedder` ABC với tên model và hợp đồng sinh embedding từ ảnh.
- Export port qua package domain, thêm unit test và cập nhật checklist Tuần 2.

## 2026-09-21 — feat(domain): add entities and repository ports

- Thêm domain entity và enum cho `User`, `FaceProfile`, `CheckInRecord`.
- Thêm Repository ABC độc lập framework cho ba entity.
- Thêm unit test và cập nhật checklist Tuần 2.
- Thêm kế hoạch commit theo dependency cho toàn bộ Tuần 2–8.

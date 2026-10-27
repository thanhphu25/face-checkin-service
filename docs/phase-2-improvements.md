# Đánh giá và hướng cải tiến Pha 2

Theo [đề bài](2026.md), cải tiến cần xuất phát từ đánh giá hệ thống, có lý do và đo trước/sau trên
một cấu hình phần cứng cố định. Các hướng dưới đây là đề xuất, chưa phải kết quả đã triển khai.
Hiện chưa có số liệu chứng minh cải thiện so với baseline Pha 1.

## 1. Bằng chứng và phạm vi

Baseline Pha 1 hiện hành tại commit `3503b24` ngày 2026-10-27, Kaggle CPU 4 core, Uvicorn một worker,
ngoài Compose. [Notebook Kaggle](https://www.kaggle.com/code/tphu25/face-checkin-benchmark) có bộ kết quả
với thời điểm metadata PostgreSQL 10:55:26 (UTC+7): check-in đạt 6,424 req/s ở concurrency 1 và
10,140 ở concurrency 8; p95 tăng từ 167,79 lên 874,75 ms. CPU máy gần bão hòa khi tăng tải.
Baseline chỉ có một profile và lịch sử nhỏ, chưa đo chi phí riêng từng công đoạn, dữ liệu lớn
hoặc tải hỗn hợp.

Code hiện tại dùng SQLAlchemy đồng bộ, InsightFace CPU, matching toàn bộ profile và chưa có cache.
Trước khi đánh giá phương án, cần đo lặp cả bản gốc và bản cải tiến trên cùng cấu hình;
chưa có kết quả trước/sau Pha 2.
Xem [số liệu, giới hạn và cách chạy](benchmark-phase1.md), [kiến trúc](architecture.md).

## 2. Vấn đề, phương án và tiêu chí đánh giá

P1 là ưu tiên khảo sát; P2 chọn theo bối cảnh và kết quả đo. Chỉ chọn 2–3 cải tiến có mục tiêu cụ
thể sau khi đo lại, không mặc định thêm hạ tầng.

| Mã | Ưu tiên / thuộc tính chất lượng | Hiện trạng và bằng chứng | Hướng thử nghiệm | Đánh giá và đánh đổi |
|---|---|---|---|---|
| V01 | P1 / Hiệu năng | Baseline check-in chịu áp lực CPU; latency tăng theo concurrency | Đo riêng decode, embed, query, matching, ghi DB; thử số thread ONNX, worker, giới hạn inference đồng thời; cân nhắc model nhẹ/quantization hoặc tách inference khi cần cô lập tải | Throughput, p95/p99, CPU/RAM, lỗi và history dưới tải hỗn hợp; nhiều worker nhân bản model, tranh CPU; đổi model phải đo lại độ chính xác |
| V02 | P1 / Khả năng mở rộng | Mỗi request tải, lọc và chuẩn hóa toàn bộ profile; chưa đo tập lớn | Đo 100/1.000/10.000 profile; thử lọc ở query, cache ma trận; chỉ thử pgvector/FAISS/ANN khi exact search là nút thắt | Thời gian query/matching, p95, RAM, recall so với exact search; cache cần invalidation khi thêm/xóa và đồng bộ nhiều worker |
| V03 | P1 / Toàn vẹn dữ liệu | Dependency commit với mọi DomainError; rủi ro khi use case mở rộng ghi nhiều bảng | Tách kết quả audit cần lưu khỏi lỗi phải rollback; đánh giá Unit of Work | Inject lỗi giữa hai lần ghi; no_face/unmatched vẫn đúng một record; lỗi hệ thống không để dữ liệu dở dang; giữ HTTP contract |
| V04 | P1 / Bảo mật | Check-in công khai; chưa có thiết bị tin cậy, liveness, rate limit | Chốt mô hình kiosk/client; thử xác thực và thu hồi credential thiết bị, rate limit, liveness nếu cần | Thiết bị sai/bị thu hồi, tải vượt mức, ảnh giả, chặn nhầm và latency; không khẳng định chống giả mạo chỉ vì có bước kiểm tra |
| V05 | P2 / Sẵn sàng, tài nguyên | GET/DELETE cũng phụ thuộc embedder dù không inference | Tách dependency đọc/ghi hoặc lazy runtime có đồng bộ khởi tạo; chọn startup warm-up hay lazy load | Cold/warm latency, số lần nạp model đồng thời, RAM, lỗi thiếu model; thao tác đọc không nên phụ thuộc model |
| V06 | P2 / Vận hành | Health chỉ trả ok, chưa kiểm tra DB/model; thiếu metric theo công đoạn | Tách liveness/readiness, thêm timeout, request ID, timing/log cần thiết | Ngắt DB/model, recovery và overhead; tránh restart loop do dependency ngoài; log không chứa credential/ảnh/vector |
| V07 | P2 / Độ tin cậy | Retry có thể tạo nhiều record; chưa có idempotency key | Chốt quy tắc nghiệp vụ; thử key theo thiết bị và unique constraint trong cùng transaction | Retry sau commit, nhiều request cùng key, cùng key khác payload; phân biệt gửi lặp và hai lần điểm danh hợp lệ, cân nhắc TTL |
| V08 | P2 / Contract, mở rộng | List user/profile chưa phân trang; history chỉ có limit, chưa kiểm tra thứ tự/timezone query; full_name giữa POST/GET khác nhau; race email trùng chưa ánh xạ riêng | Phân trang ổn định, thống nhất thời gian và ý nghĩa full_name, ánh xạ unique email | Insert đồng thời, khoảng thời gian sai, lịch sử sau xóa và email trùng; cập nhật OpenAPI, giữ scope dữ liệu |
| V09 | P1 / Độ chính xác | Threshold 0.40 chưa đánh giá trên tập đại diện; hiệu năng không chứng minh nhận diện đúng | Tập ảnh có quyền sử dụng, tách ảnh/người đăng ký và kiểm thử; hiệu chỉnh threshold, đánh giá lại khi đổi pipeline | FAR/FRR, top-1, ánh sáng/góc chụp, ảnh người chưa đăng ký; cosine score không phải xác suất, khác model cần quản lý lại profile |

Các vấn đề có trong mã nguồn là đánh giá thiết kế, không đồng nghĩa đã đo được tác động hoặc đã
xảy ra lỗi dữ liệu. Đổi hàm sang async không tự tăng tốc inference CPU; cache DB không tự giải
quyết chi phí model. Chỉ bổ sung Redis, queue hay vector index cùng use case và test liên quan.

Nguồn đối chiếu: [matching](../app/services/check_in_service.py), [dependency/transaction](../app/api/deps.py),
[ML adapter](../app/ml/insightface_embedder.py), [repository](../app/repositories/),
[API spec](api-spec.md).

## 3. Quy trình đánh giá trước và sau

1. Chốt số user/profile, tỷ lệ đọc/ghi và mục tiêu chất lượng: throughput, p95, RAM hoặc độ chính
   xác; đặt mục tiêu định lượng trước khi sửa.
2. Chạy baseline và phương án trên cùng cấu hình Kaggle CPU, cùng model/dữ liệu/workload và tham
   số tải. Thay một yếu tố mỗi thí nghiệm; ghi commit và metadata.
3. Lặp ít nhất ba lần sau warm-up, báo trung vị và khoảng dao động. Tách cold start khỏi warm run;
   giữ bộ đo gốc, thêm workload lớn/hỗn hợp thành bộ riêng và chạy cả hai bản trên bộ mới.
4. Kiểm tra auth/ownership, matching tại ngưỡng, audit thất bại, transaction và lịch sử sau xóa.
   Nếu dùng ANN/liveness/model mới, đo thêm tác động tới kết quả nhận diện.
5. Báo kết quả kể cả không cải thiện, chi phí CPU/RAM, độ phức tạp vận hành và phương án phục hồi.
   Chấp nhận khi đạt mục tiêu, cải thiện vượt dao động đo và giữ đúng nghiệp vụ.
6. Cập nhật quyết định trong kiến trúc, API/OpenAPI và hướng dẫn chạy/migration nếu có thay đổi.

Điều kiện và lệnh đo chi tiết nằm tại [benchmark](benchmark-phase1.md#8-đọc-kết-quả-và-so-sánh-trướcsau).

## 4. Nội dung báo cáo kết quả khi triển khai

Mỗi cải tiến cần ghi: vấn đề và số đo gốc; lựa chọn và phương án đối chiếu; commit/cấu hình của
hai bản; bảng trước/sau về throughput, p95/p99, CPU/RAM, lỗi và độ chính xác nếu liên quan;
nhận xét lợi ích, giới hạn và đánh đổi. Chưa điền số liệu khi chưa chạy thí nghiệm.

Có thể bắt đầu bằng phân rã V01/V02 và xây bộ đo V09. Nếu mục tiêu là triển khai kiosk thực tế,
ưu tiên làm rõ V04/V07. Các hướng vận hành và toàn vẹn dữ liệu có thể đáng làm dù throughput
không tăng; chọn chỉ số phù hợp thay vì gọi mọi thay đổi là tối ưu hiệu năng.

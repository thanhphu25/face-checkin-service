# Các vấn đề chính và hướng cải thiện Pha 2

Ngày rà soát: 2026-10-19. Tài liệu dựa trên mã nguồn Pha 1 và baseline đã lưu trong repo;
các phương án dưới đây chưa được triển khai. Chỉ chọn 2–3 cải tiến sau khi đo lại trên workload
đại diện, không thêm Redis, queue, async DB hoặc vector index chỉ để dự phòng.

## 1. Phạm vi và bằng chứng

- Backend hiện chạy FastAPI, SQLAlchemy đồng bộ, InsightFace `buffalo_s` trên CPU.
- Mỗi check-in sinh embedding, đọc toàn bộ profile, so khớp cosine rồi ghi lịch sử.
- Compose hiện chỉ có `app`, `migrate`, `postgres`.
- Baseline ngày 2026-09-22 tại commit `4affbd0`: Kaggle CPU 4 core, Uvicorn một worker,
  chạy ngoài Compose. PostgreSQL check-in đạt 4,83 req/s ở concurrency 1 và 8,46 req/s ở
  concurrency 8; p95 tương ứng 227,7 ms và 1.116 ms.
- Baseline chỉ có một face profile và bảng lịch sử nhỏ. Số liệu cho thấy áp lực CPU ở đường
  check-in; chưa phân rã thời gian để khẳng định tỷ trọng từng công đoạn, chưa đo tải hỗn hợp
  hoặc hàng nghìn profile. Không suy ra giới hạn production từ baseline này.

Nguồn: [báo cáo baseline](benchmark-phase1.md), [CSV và metadata](benchmark/),
[điều kiện đo](adr/0005-benchmark-method-and-baseline-conditions.md).

## 2. Danh sách ưu tiên

P1: ưu tiên khảo sát/đo trước; P2: chọn theo nhu cầu và kết quả đo. Đây là thứ tự đánh giá,
không phải cam kết triển khai toàn bộ.

| Mã | Ưu tiên | Vấn đề | Thuộc tính chất lượng | Mức bằng chứng |
|---|---|---|---|---|
| V01 | P1 | Đường check-in chịu áp lực CPU, latency tăng theo concurrency | Hiệu năng | Đã đo baseline nhỏ |
| V02 | P1 | Mỗi check-in tải và chuẩn hóa lại toàn bộ profile | Khả năng mở rộng | Có trong code, chưa đo tập lớn |
| V03 | P1 | Transaction commit với mọi `DomainError` | Tính toàn vẹn, khả năng bảo trì | Có trong code; rủi ro khi mở rộng use case |
| V04 | P1 | API điểm danh công khai, chưa xác thực thiết bị/liveness | Bảo mật, tính đúng đắn | Có trong code; phụ thuộc bối cảnh triển khai |
| V05 | P2 | Các thao tác đọc/xóa cũng phụ thuộc khởi tạo model | Tính sẵn sàng, sử dụng tài nguyên | Có trong dependency graph |
| V06 | P2 | `/health` chưa kiểm tra DB/model; thiếu quan sát theo công đoạn | Khả năng vận hành | Có trong code |
| V07 | P2 | Gửi lặp có thể tạo nhiều bản ghi | Tính đúng đắn, độ tin cậy | Có trong code |
| V08 | P2 | Phân trang và validation/response API còn giới hạn | Khả năng sử dụng, mở rộng | Có trong code |
| V09 | P1 | Chưa có bộ đo độ chính xác nhận diện đại diện | Tính đúng đắn | Chưa có đánh giá FAR/FRR trong baseline |

## 3. V01 — Chi phí inference và xử lý đồng thời

**Hiện trạng:** [InsightFace adapter](../app/ml/insightface_embedder.py) chạy trong cùng process
với API, request đợi kết quả đồng bộ. Baseline p95 tăng mạnh khi tăng concurrency và CPU gần
bão hòa. Việc đường nhận diện ảnh hưởng API lịch sử đến đâu chưa được đo.

**Hướng cải thiện:**

1. Đo riêng decode, detection/embedding, đọc profile, matching và ghi DB.
2. Thử giới hạn/phối hợp số thread ONNX Runtime, số worker và số request inference đồng thời.
3. Nếu inference là phần chi phối, thử model/cấu hình nhẹ hơn hoặc quantization; đánh giá lại
   độ chính xác. Chỉ tách worker/service inference khi cần cô lập tải và có bằng chứng lợi ích.

**Đánh giá:** throughput, p95/p99, CPU, RAM, tỷ lệ lỗi; thêm tải hỗn hợp check-in + history.
Nhiều worker nhân bản model, tăng RAM/connection và có thể tranh CPU. Chuyển hàm sang `async`
không tự làm inference trên CPU nhanh hơn. Nếu đổi sang xử lý nền, phải thiết kế lại contract
nhận kết quả và cơ chế backpressure.

## 4. V02 — Đọc và so khớp toàn bộ embedding ở mỗi request

**Hiện trạng:** [CheckInService.check_in](../app/services/check_in_service.py) gọi
`profiles.list_all()`, lọc model/dimension trong Python, chuẩn hóa từng vector và tạo lại ma trận.
[FaceProfileRepository](../app/repositories/face_profile_repository.py) trả toàn bộ profile. Matching có chi phí
`O(N × d)` với N profile và d chiều; baseline một profile chưa phản ánh chi phí này.

**Hướng cải thiện:** đo ở 100/1.000/10.000 profile, lọc model/dimension tại truy vấn nếu hữu ích;
thử cache ma trận đã chuẩn hóa trong process trước khi cân nhắc Redis hoặc vector index.
Nếu exact search thực sự là nút thắt, so sánh với pgvector/FAISS/ANN.

**Đánh giá:** thời gian query/deserialize/matching, p95, RAM và recall so với exact search.
Cache phải cập nhật khi thêm/xóa profile hoặc xóa user, kể cả nhiều worker. Thử cả cache miss,
dữ liệu cũ và dependency lỗi. ANN có thể bỏ sót ứng viên; không chỉ so throughput.

## 5. V03 — Ranh giới transaction và lịch sử thất bại

**Hiện trạng:** [get_session](../app/api/deps.py) commit cả khi bắt mọi `DomainError` để giữ
record `unmatched`/`no_face`. Nếu một use case tương lai ghi nhiều bảng rồi phát sinh lỗi nghiệp vụ,
thay đổi trước lỗi có thể được commit ngoài ý muốn. Đây là rủi ro thiết kế, chưa phải bằng chứng
đã xảy ra sai dữ liệu trong use case hiện tại.

**Hướng cải thiện:** định nghĩa rõ kết quả điểm danh thất bại như một kết quả nghiệp vụ cần lưu;
tách nó khỏi lỗi phải rollback. Khi use case cần nhiều thao tác nguyên tử, cân nhắc port
`UnitOfWork` hoặc transaction boundary rõ ở use case.

**Đánh giá:** inject lỗi giữa hai lần ghi để xác nhận rollback; xác nhận `unmatched`/`no_face`
vẫn lưu đúng một record và lỗi hệ thống không để lại dữ liệu dở dang. Nếu thay cách biểu diễn
kết quả nội bộ, giữ hoặc chủ động version HTTP contract đang có.

## 6. V04 — Xác thực thiết bị, chống lạm dụng và giả mạo khuôn mặt

**Hiện trạng:** [POST /checkins](../app/api/v1/check_ins.py) công khai; adapter kiểm tra đúng
một mặt nhưng chưa kiểm tra liveness. Có mặt trong ảnh không chứng minh người thật đang đứng
trước camera. Login cũng chưa có rate limit trong ứng dụng.

**Hướng cải thiện:** xác định mô hình sử dụng trước: kiosk tin cậy hay client bất kỳ. Nếu triển
khai thực tế, đánh giá xác thực/thu hồi credential thiết bị, rate limit login/check-in và liveness.
Chỉ thêm hạ tầng dùng chung như Redis khi cần phối hợp limit giữa nhiều replica.

**Đánh giá:** thiết bị hợp lệ/không hợp lệ/bị thu hồi, tải vượt giới hạn, ảnh in/ảnh trên màn hình,
tỷ lệ chặn nhầm và latency tăng thêm. Một cơ chế liveness nhận ảnh tĩnh cần được đánh giá thực tế;
không khẳng định chống giả mạo chỉ vì đã thêm một bước kiểm tra.

## 7. V05 — Vòng đời model bị gắn vào cả thao tác không inference

**Hiện trạng:** [get_face_profile_service/get_check_in_service](../app/api/deps.py) luôn nhận
`EmbedderDependency`. GET lịch sử, GET/DELETE profile hoặc DELETE check-in cũng có thể phải
khởi tạo model ở request đầu dù không gọi `embed()`. Model cache dùng chung trong một process;
cache dependency chưa có trong lần khởi tạo đồng thời cũng cần được kiểm chứng.

**Hướng cải thiện:** tách dependency/use case đọc và ghi khỏi inference, hoặc dùng adapter khởi tạo
runtime khi thật sự gọi `embed()`. Chọn rõ warm-up lúc startup hay lazy load và cơ chế đồng bộ
khởi tạo; phối hợp với readiness để tránh nhận tải khi model chưa sẵn sàng.

**Đánh giá:** cold/warm latency của GET/DELETE, số lần khởi tạo model khi request đồng thời,
RAM và hành vi khi model cache thiếu/không tải được. API chỉ đọc không nên cần model hoạt động.

## 8. V06 — Healthcheck và khả năng quan sát

**Hiện trạng:** [GET /health](../app/main.py) chỉ trả `status: ok`; app vẫn có thể báo healthy
khi DB mất kết nối hoặc model chưa sẵn sàng. Chưa có request ID, metric theo công đoạn hoặc
logging tập trung trong ứng dụng. Biến `LOG_LEVEL` cũ chưa được dùng đã được bỏ khi dọn Pha 1.

**Hướng cải thiện:** phân biệt liveness và readiness; readiness kiểm tra dependency cần thiết
với timeout hữu hạn. Thêm timing/metric và log có request ID, tránh ghi ảnh, vector, mật khẩu,
token hoặc credential vào log. Chỉ thêm cấu hình logging khi có implementation sử dụng.

**Đánh giá:** ngắt DB, model thiếu/lỗi, recovery; xác nhận readiness phản ánh đúng trạng thái,
liveness không gây vòng restart do dependency ngoài lỗi và overhead quan sát chấp nhận được.

## 9. V07 — Retry và điểm danh trùng

**Hiện trạng:** mỗi request thành công tạo một record mới, chưa có idempotency key hoặc quy tắc
một lần điểm danh trong khoảng thời gian. Retry sau timeout có thể tạo bản ghi trùng.

**Hướng cải thiện:** làm rõ quy tắc nghiệp vụ; nếu cần, dùng idempotency key có phạm vi thiết bị
và ràng buộc duy nhất trong DB. Phân biệt retry của cùng request với hai lần điểm danh hợp lệ.

**Đánh giá:** retry sau khi DB commit nhưng client chưa nhận response; nhiều request đồng thời
cùng key chỉ tạo một record; cùng key với payload khác được xử lý rõ. Bảo đảm lưu key và record
trong cùng transaction. Cân nhắc TTL và chi phí lưu trữ, không dựa riêng vào cache dễ mất dữ liệu.

## 10. V08 — Contract API và phân trang

**Hiện trạng:**

- List user/profile chưa có phân trang; history chỉ có limit, chưa có cursor/offset.
- Query history chưa kiểm tra `start < end` hoặc bắt buộc timezone.
- POST check-in bổ sung `full_name`, GET lịch sử/chi tiết chưa bổ sung nên thường trả `null`.
- Kiểm tra email trùng trước insert chưa loại bỏ race; DB có unique constraint nhưng chưa có
  ánh xạ riêng cho lỗi vi phạm constraint khi hai request tạo cùng email đồng thời.

Nguồn: [routers](../app/api/v1/), [UserService](../app/services/user_service.py),
[UserRepository](../app/repositories/user_repository.py), [đặc tả API](api-spec.md).

**Hướng cải thiện:** bổ sung phân trang có thứ tự ổn định; thống nhất validation thời gian và
ý nghĩa `full_name` (tên hiện tại hay tên tại thời điểm điểm danh); ánh xạ constraint email thành
lỗi nghiệp vụ mà không che các lỗi DB khác.

**Đánh giá:** phân trang khi có insert đồng thời, input thời gian sai/múi giờ khác, record đã
ẩn danh sau xóa user, hai request tạo email trùng; kiểm tra lại OpenAPI và quyền scope dữ liệu.

## 11. V09 — Độ chính xác và hiệu chỉnh threshold

**Hiện trạng:** threshold mặc định `0.40`; cosine score không phải xác suất nhận diện đúng.
Test với ảnh mẫu và baseline hiệu năng không đo độ chính xác trên nhiều người/điều kiện chụp.

**Hướng cải thiện:** xây tập đánh giá có quyền sử dụng, tách người/ảnh đăng ký và ảnh kiểm thử;
đo cặp cùng người/khác người, ánh sáng/góc chụp và ảnh không có chủ thể đã đăng ký. Chọn threshold
theo mức chấp nhận nhận nhầm và từ chối nhầm. Đánh giá lại khi đổi model/quantization.

**Đánh giá:** false acceptance rate (FAR), false rejection rate (FRR), nhận diện đúng top-1,
ảnh hưởng chất lượng ảnh và độ trễ. Không đưa ảnh/vector thật vào Git. Nếu đổi model, xác định
cách đăng ký lại hoặc quản lý profile cũ; cùng dimension không có nghĩa cùng không gian embedding.

## 12. Cách chọn và nghiệm thu cải tiến

1. Chốt số user/profile, tần suất điểm danh, tải hỗn hợp và mục tiêu chất lượng cùng nhóm.
2. Chạy lại baseline trên cùng máy, model, dataset, số worker và workload; lưu commit và metadata.
   Tách cold start/warm run, lặp nhiều lượt và giữ warm-up nhất quán.
3. Chọn 2–3 vấn đề theo kết quả đo và nhu cầu; đặt mục tiêu định lượng trước khi sửa.
4. Triển khai từng cải tiến độc lập, ghi ADR về lợi ích và đánh đổi; chỉ thêm dependency thực sự dùng.
5. Chạy test nghiệp vụ, auth/ownership, transaction và integration liên quan; đo trước/sau với cùng
   điều kiện, báo cả CPU/RAM, lỗi và chất lượng nhận diện khi thay pipeline ML.
6. Ghi kết quả kể cả phương án không cải thiện. Với thay đổi API hoặc dữ liệu, cập nhật OpenAPI,
   hướng dẫn migration/rollback và kịch bản bàn giao.

Gợi ý bắt đầu: đo phân rã V01/V02 và đánh giá V09; sau đó chọn tối ưu inference hoặc matching
theo nút thắt thật. Nếu mục tiêu là triển khai thiết bị thực tế, ưu tiên khảo sát V04 và V07.
V03/V05/V06 là các hướng về tính toàn vẹn và vận hành, không nên gọi là tối ưu throughput khi
chưa có số đo chứng minh.

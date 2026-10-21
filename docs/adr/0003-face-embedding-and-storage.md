# ADR 0003 — Face embedding và cách lưu trữ

- Status: Accepted
- Date: 2026-09-22

## Context

Pha 1 phải sinh embedding thật trên CPU, chạy được trên máy dev/Kaggle CPU và giữ logic matching ở
Service. Embedding phải round-trip qua SQLite/PostgreSQL mà không đổi dtype hoặc nhầm vector của hai
model khác nhau.

## Decision

- Dùng InsightFace `buffalo_s` với ONNX Runtime `CPUExecutionProvider`; adapter model được tạo lazy
  và cache trong composition root thay vì nạp lại mỗi request.
- Embedding domain luôn là vector một chiều `float32`, hữu hạn và L2-normalized.
- Repository lưu little-endian float32 dưới dạng bytes/BLOB/BYTEA, kèm `embedding_dim` và
  `model_name`; khi đọc phải kiểm tra số phần tử khớp dimension và trả bản copy `numpy.ndarray`.
- Pha 1 chỉ so sánh các profile cùng model/dimension bằng phép nhân ma trận trong Service.

## Alternatives considered

- JSON/JSONB: dễ đọc nhưng lớn và parse chậm hơn nhiều.
- `float64`: tăng gấp đôi dung lượng mà không đem lại lợi ích cho embedding model này.
- pgvector/FAISS/HNSW: tìm kiếm gần nhanh hơn ở quy mô lớn nhưng thêm hạ tầng và xóa mất baseline
  tuyến tính cần đo ở Pha 1.
- GPU provider hoặc model lớn hơn: có thể tăng chất lượng/tốc độ ở phần cứng phù hợp nhưng không
  khớp mục tiêu Kaggle CPU.

## Consequences

- Database không tự tìm nearest neighbor; ứng dụng tải profile phù hợp và matching tuyến tính.
- Đổi model/dimension không thể trộn embedding cũ với mới; cần re-embed hoặc chạy song song theo
  `model_name`.
- Cần xem lại khi benchmark thật cho thấy inference/model hoặc quét embedding không đạt SLO, số
  profile tăng đủ lớn, hoặc môi trường đích có GPU ổn định.

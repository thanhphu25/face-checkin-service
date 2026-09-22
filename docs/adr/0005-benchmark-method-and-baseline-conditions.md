# ADR 0005 — Phương pháp benchmark và điều kiện baseline Pha 1

- Status: Accepted
- Date: 2026-09-22

## Context

Baseline Pha 1 tồn tại để so sánh với Pha 2 sau khi cải tiến. Một con số throughput hay p95 chỉ có
nghĩa khi đi kèm điều kiện đo; nếu hai lần đo khác môi trường, khác số worker hay khác database thì
phần trăm cải thiện là vô nghĩa. Đề bài bắt buộc đo trên Kaggle CPU, mà Kaggle notebook không chạy
Docker, nên baseline không thể đo qua chính Docker Compose dùng ở môi trường chạy thật.

Ngoài ra InsightFace/ONNX Runtime dùng thread pool riêng, độc lập với event loop của ứng dụng. Điều
này làm số CPU dễ bị hiểu sai nếu chỉ nhìn một con số phần trăm.

## Decision

- Baseline đo bằng `scripts/run_baseline.py`: Alembic migration → seed → Uvicorn **một worker** →
  `scripts/benchmark.py`. Không dùng Compose khi đo, và chênh lệch này được ghi rõ trong báo cáo.
- Đo hai scenario tách biệt: `checkin` (`POST /api/v1/checkins`, công khai, chạy inference) và
  `history` (`GET /api/v1/checkins`, có JWT, không chạy inference).
- Đo **cả SQLite lẫn PostgreSQL**, ghi hai bộ số liệu riêng. Cải tiến Pha 2 hướng tới PostgreSQL,
  nhưng SQLite là cấu hình chạy nhanh trên Kaggle nên giữ cả hai để không phải chọn mù.
- Percentile dùng nearest-rank, nên mọi giá trị p50/p95/p99 công bố đều là một mẫu thật đã quan sát,
  không phải giá trị nội suy.
- Warm-up chạy trước mỗi mức concurrency và **không** vào số liệu; lần gọi đầu tiên còn phải tải
  model `buffalo_s`.
- Sau warm-up, harness chờ `--settle-seconds` rồi mới lấy mẫu CPU; cửa sổ đo ngắn hơn 0,5 giây được
  báo là thiếu thay vì báo một con số.
- CPU được báo bằng hai đơn vị khác nhau và phải đọc đúng: `cpu_percent_system` là phần trăm của
  toàn máy (0–100%), còn `cpu_percent_server` là phần trăm của một core cho riêng tiến trình server
  (vượt 100% được). Số core nằm trong file metadata đi kèm mỗi CSV.
- Tuần 8 phải chạy lại đúng script, đúng tham số và đúng loại instance Kaggle. Đổi bất kỳ yếu tố nào
  thì phải đo lại cả baseline.

## Alternatives considered

- Đo qua Docker Compose: sát môi trường chạy thật nhất, nhưng Kaggle không chạy Docker nên sẽ vi
  phạm yêu cầu đo trên Kaggle CPU hoặc buộc phải đo ở hai nơi khác nhau giữa Pha 1 và Pha 2.
- Chỉ đo `POST /checkins`: đơn giản hơn, nhưng che mất đường đọc — đúng chỗ mà cache Redis của Pha 2
  nhắm tới, nên sẽ không có baseline để so sánh.
- Chỉ đo một database: ít số liệu hơn, nhưng nhóm nhận hệ thống sẽ phải tự đoán ảnh hưởng của
  database khi chọn cải tiến.
- Dùng multi-worker ngay ở baseline: throughput đẹp hơn nhưng làm mất khả năng đo riêng cải tiến
  multi-worker của Pha 2, vì nó đã nằm sẵn trong baseline.
- Percentile nội suy: mượt hơn với mẫu nhỏ, nhưng công bố một giá trị chưa từng xảy ra.
- Bỏ qua khoảng lặng giữa các mức đo: nhanh hơn vài giây mỗi mức, nhưng đã đo được sai lệch thật —
  mức đọc đầu tiên bị tính 720% CPU của mức check-in trước đó và throughput thấp hơn 42%.

## Consequences

- Số liệu baseline không phản ánh hiệu năng của bản triển khai Compose nhiều worker; nó phản ánh
  hiệu năng một worker trên CPU Kaggle. Báo cáo phải nói rõ điều này.
- Mỗi lượt đo sinh ra một CSV và một file metadata; thiếu metadata thì lượt đo không dùng được để so
  sánh.
- Harness chậm hơn một chút vì warm-up và khoảng lặng, đổi lại số CPU có thể tin được.
- Nếu Kaggle đổi loại instance giữa Tuần 6 và Tuần 8, toàn bộ so sánh phải đo lại từ đầu.

## Điều kiện xem lại

Xem lại ADR này khi: Kaggle đổi cấu hình CPU mặc định; nhóm quyết định đo bằng Compose trên một máy
cố định thay cho Kaggle; hoặc Pha 2 thêm scenario mới mà baseline Pha 1 chưa có số liệu tương ứng.

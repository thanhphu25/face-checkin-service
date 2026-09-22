# ADR 0004 — Ranh giới hạ tầng Pha 1 và Pha 2

- Status: Accepted
- Date: 2026-09-22
- Updated: 2026-10-19 — bỏ hạ tầng dự phòng chưa được ứng dụng sử dụng.

## Context

Pha 1 cần một baseline chức năng có thể dựng lại và đo được. Cấu hình ban đầu dựng Redis dự phòng
nhưng ứng dụng không đọc/ghi Redis. Theo yêu cầu thu gọn Pha 1, chỉ giữ dependency đang phục vụ
ứng dụng; hạ tầng cho cải tiến tương lai được bổ sung khi có use case và phép đo cụ thể.

## Decision

- Pha 1 không dùng pgvector, FAISS, ANN index, async database hay Redis cache.
- Compose chỉ gồm `app`, `migrate` và `postgres`. Bỏ service Redis, port dự phòng và bước ping Redis
  trong CI; app không có cấu hình hoặc dependency Redis.
- PostgreSQL giữ dữ liệu bền vững; model cache có named volume riêng. Migration chạy trong service
  one-shot duy nhất trước app để tránh nhiều replica tranh migration.
- Chọn cải tiến Pha 2 sau khi đo lại baseline. Danh sách vấn đề và phương pháp đánh giá nằm tại
  [phase-2-improvements.md](../phase-2-improvements.md).

## Alternatives considered

- Bật Redis cache ngay: có thể giảm một số lượt đọc nhưng chưa có số đo, tăng invalidation và làm
  baseline mất ý nghĩa.
- Thêm pgvector/FAISS ngay: tối ưu sớm và làm logic/hạ tầng Pha 1 phức tạp hơn.
- Cho mỗi app replica tự chạy migration: ít service hơn nhưng có race khi scale.
- Giữ Redis chạy dự phòng: thuận tiện cho thử cache nhưng tiêu thụ RAM/CPU, mở thêm port và tăng
  công việc vận hành mà chưa phục vụ request nào.

## Consequences

- Stack Pha 1 không cần tải/chạy image Redis hoặc dành port cho một service chưa dùng.
- Nếu Pha 2 chọn Redis, phải bổ sung service, cấu hình kết nối, test invalidation/fallback và
  benchmark trước/sau trong cùng thay đổi; không chỉ dựng container dự phòng.
- Quyết định cần xem lại khi đo được lợi ích cache hoặc có nhu cầu queue/rate limit cụ thể.
- Các báo cáo kiểm chứng Tuần 5–6 giữ kết quả cấu hình cũ và có ghi chú lịch sử.

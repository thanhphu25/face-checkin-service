# ADR 0004 — Ranh giới hạ tầng Pha 1 và Pha 2

- Status: Accepted
- Date: 2026-09-22

## Context

Compose cần Redis để nhóm nhận hệ thống có hạ tầng sẵn cho một cải tiến khả dĩ, nhưng Pha 1 phải là
baseline chức năng, chưa được tối ưu trước khi đo. Việc một service tồn tại trong Compose không có
nghĩa application đã dùng nó.

## Decision

- Pha 1 không dùng pgvector, FAISS, ANN index, async database hay Redis cache.
- Redis 7.4 chỉ được dựng, healthcheck và expose port cấu hình được; app không nhận `REDIS_URL` và
  không đọc/ghi Redis.
- PostgreSQL giữ dữ liệu bền vững; model cache có named volume riêng. Migration chạy trong service
  one-shot duy nhất trước app để tránh nhiều replica tranh migration.
- Không tuyên bố benchmark hoặc lựa chọn cải tiến Pha 2 cho đến khi Tuần 6 có baseline thật và nhóm
  nhận hệ thống đo lại ở Tuần 7.

## Alternatives considered

- Bật Redis cache ngay: có thể giảm một số lượt đọc nhưng chưa có số đo, tăng invalidation và làm
  baseline mất ý nghĩa.
- Thêm pgvector/FAISS ngay: tối ưu sớm và làm logic/hạ tầng Pha 1 phức tạp hơn.
- Cho mỗi app replica tự chạy migration: ít service hơn nhưng có race khi scale.
- Không dựng Redis: image nhỏ hơn, nhưng nhóm Pha 2 phải thay đổi Compose trước khi thử cache.

## Consequences

- Redis tiêu thụ tài nguyên khi chạy full stack dù chưa phục vụ request; người vận hành có thể chỉ
  khởi động dependency cần thiết khi phát triển cục bộ.
- Pha 2 phải có test cache invalidation/fallback và benchmark trước/sau nếu quyết định nối Redis.
- Quyết định cần xem lại sau baseline nếu bottleneck nằm ngoài cache/ANN, hoặc production không cho
  phép vận hành một Redis chưa được sử dụng.

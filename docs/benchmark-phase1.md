# Baseline Pha 1 — Kaggle CPU

Số liệu gốc: [benchmark/baseline-sqlite.csv](benchmark/baseline-sqlite.csv) và
[benchmark/baseline-postgresql.csv](benchmark/baseline-postgresql.csv), kèm hai file metadata ghi
phần cứng và toàn bộ tham số. Phương pháp đo và lý do chọn: [ADR 0005](adr/0005-benchmark-method-and-baseline-conditions.md).
Cách chạy lại: [benchmark-kaggle.md](benchmark-kaggle.md).

## 1. Tóm tắt

- **Đường ghi (`POST /checkins`) là điểm nghẽn**: 4,82 req/s ở một client, trần khoảng 8,5 req/s.
  Đường đọc nhanh hơn khoảng **34 lần** trên cùng máy.
- **Inference chiếm hết CPU**: ngay ở concurrency 1, tiến trình server đã dùng 3,1/4 core. Từ
  concurrency 4 trở lên máy bão hoà 99,7%, nên tăng concurrency chỉ làm latency dài ra chứ gần như
  không thêm throughput.
- **Database gần như không ảnh hưởng tới check-in** (chênh ≤7%, trong khoảng nhiễu) vì thời gian là
  của detection/embedding, không phải của truy vấn.
- **Database ảnh hưởng mạnh tới đường đọc khi có tải đồng thời**: ở concurrency 8, PostgreSQL đạt
  150,3 req/s còn SQLite tụt xuống 81,6 req/s — PostgreSQL nhanh hơn **1,84 lần** và p95 thấp hơn
  34,5%.
- **Đường đọc không bị nghẽn vì CPU**: ở concurrency 8 nó chỉ dùng 1,2–1,6/4 core và để hơn nửa máy
  rảnh, tức nghẽn nằm ở chỗ khác chứ không phải thiếu CPU.

## 2. Điều kiện đo

| Hạng mục | Giá trị |
|---|---|
| Ngày đo | 2026-09-22 |
| Commit | `4affbd0` |
| Máy | Kaggle CPU notebook, 4 core, Linux 6.12.90, Python 3.12.13 |
| Server | Uvicorn 1 worker, không dùng Docker Compose |
| Model | `buffalo_s` (InsightFace), CPU |
| Tải mỗi mức | 60 request cho `checkin`, 1000 request cho `history` |
| Concurrency | 1, 2, 4, 8 |
| Warm-up | 5 request mỗi mức, không tính vào số liệu |
| Lỗi | 0/16 mức đo có lỗi |

Hai cột CPU khác đơn vị: **CPU máy** là phần trăm của cả 4 core (tối đa 100), **CPU server** là phần
trăm của một core cho riêng tiến trình Uvicorn (389% ≈ 3,89 core).

## 3. `POST /api/v1/checkins` — đường ghi, có inference

| Backend | Concurrency | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | CPU máy (%) | CPU server (% 1 core) |
|---|---:|---:|---:|---:|---:|---:|---:|
| SQLite | 1 | 4.82 | 207.0 | 226.9 | 240.9 | 79.2 | 309.6 |
| SQLite | 2 | 7.13 | 274.7 | 315.8 | 346.4 | 95.0 | 371.1 |
| SQLite | 4 | 7.36 | 546.0 | 641.2 | 801.0 | 99.4 | 389.0 |
| SQLite | 8 | 8.54 | 919.8 | 1076.3 | 1116.2 | 99.7 | 389.3 |
| PostgreSQL | 1 | 4.83 | 206.4 | 227.7 | 245.7 | 78.8 | 308.5 |
| PostgreSQL | 2 | 6.63 | 294.8 | 350.4 | 407.3 | 97.3 | 379.8 |
| PostgreSQL | 4 | 7.17 | 547.8 | 734.0 | 849.1 | 99.2 | 388.4 |
| PostgreSQL | 8 | 8.46 | 938.1 | 1116.0 | 1268.5 | 99.7 | 387.9 |

Throughput:

```text
SQLite
  c=1  #####################                      4.82 req/s
  c=2  ################################           7.13 req/s
  c=4  #################################          7.36 req/s
  c=8  ######################################     8.54 req/s

PostgreSQL
  c=1  #####################                      4.83 req/s
  c=2  #############################              6.63 req/s
  c=4  ################################           7.17 req/s
  c=8  ######################################     8.46 req/s
```

Độ trễ p50:

```text
SQLite
  c=1  ########                                 207.00 ms
  c=2  ###########                              274.67 ms
  c=4  ######################                   546.04 ms
  c=8  #####################################    919.81 ms

PostgreSQL
  c=1  ########                                 206.40 ms
  c=2  ############                             294.84 ms
  c=4  ######################                   547.78 ms
  c=8  ######################################   938.09 ms
```

Từ concurrency 1 lên 8, throughput chỉ tăng 77% (SQLite) và 75% (PostgreSQL), trong khi p50 tăng 4,4
và 4,6 lần. Đây là dáng điệu của một hệ đã bão hoà: request xếp hàng chứ không được phục vụ nhanh
hơn. CPU server đạt 389% trên 4 core — gần như không còn dư địa.

## 4. `GET /api/v1/checkins` — đường đọc, có JWT

| Backend | Concurrency | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | CPU máy (%) | CPU server (% 1 core) |
|---|---:|---:|---:|---:|---:|---:|---:|
| SQLite | 1 | 162.86 | 6.0 | 6.6 | 7.8 | 28.8 | 75.1 |
| SQLite | 2 | 180.43 | 10.8 | 13.1 | 14.3 | 39.3 | 108.6 |
| SQLite | 4 | 123.21 | 32.3 | 40.7 | 47.2 | 46.1 | 140.3 |
| SQLite | 8 | 81.61 | 97.7 | 112.3 | 140.9 | 48.6 | 163.7 |
| PostgreSQL | 1 | 139.12 | 7.1 | 7.8 | 9.1 | 29.8 | 73.0 |
| PostgreSQL | 2 | 168.70 | 11.6 | 13.2 | 16.3 | 43.3 | 106.1 |
| PostgreSQL | 4 | 157.01 | 25.1 | 32.0 | 36.0 | 46.9 | 114.1 |
| PostgreSQL | 8 | 150.27 | 50.5 | 73.5 | 102.8 | 50.3 | 121.1 |

Throughput:

```text
SQLite
  c=1  ##################################       162.86 req/s
  c=2  ######################################   180.43 req/s
  c=4  ##########################               123.21 req/s
  c=8  #################                         81.61 req/s

PostgreSQL
  c=1  #############################            139.12 req/s
  c=2  ####################################     168.70 req/s
  c=4  #################################        157.01 req/s
  c=8  ################################         150.27 req/s
```

Độ trễ p50:

```text
SQLite
  c=1  ##                                         6.03 ms
  c=2  ####                                      10.82 ms
  c=4  #############                             32.26 ms
  c=8  ######################################    97.74 ms

PostgreSQL
  c=1  ###                                        7.07 ms
  c=2  #####                                     11.59 ms
  c=4  ##########                                25.08 ms
  c=8  ####################                      50.52 ms
```

Cả hai backend đều đạt đỉnh ở concurrency 2. Sau đó SQLite tụt 54,8% so với đỉnh còn PostgreSQL chỉ
giảm 10,9%. p50 của SQLite tăng 16,2 lần từ concurrency 1 đến 8, PostgreSQL tăng 7,1 lần.

Ở concurrency 1, SQLite lại nhanh hơn 17,1% (162,9 so với 139,1 req/s) vì không có chi phí
socket/protocol. Ưu thế đó biến mất ngay khi có tải đồng thời.

## 5. Nhận xét

1. **Chi phí một lần check-in ≈ 200 ms CPU inference.** p50 ở concurrency 1 là 207 ms (SQLite) và
   206 ms (PostgreSQL); phần database gần như không đóng góp. Mọi cải thiện đáng kể cho đường ghi
   phải đến từ inference, không phải từ tầng dữ liệu.
2. **Máy bão hoà từ concurrency 2–4.** CPU máy đã 95–99% ở concurrency 2. Thêm client sau điểm đó
   chỉ đổi lấy latency: p99 lên tới 1,27 giây ở concurrency 8.
3. **Đường đọc để trống hơn nửa máy.** Ở concurrency 8, CPU máy chỉ 48,6% (SQLite) và 50,3%
   (PostgreSQL), CPU server 1,2–1,6 core. Một tiến trình đồng bộ duy nhất không dùng hết 4 core.
4. **SQLite không chịu được tải đọc đồng thời, PostgreSQL thì có.** Đây là bằng chứng đo được cho
   việc giữ PostgreSQL làm cấu hình chạy thật, và là lý do số liệu PostgreSQL mới là mốc so sánh
   chính của Pha 2.

Báo cáo này **không** chọn cải tiến Pha 2. Việc chọn thuộc Tuần 7 và phải dựa trên baseline đo lại
trên hệ thống nhận được, không phải trên baseline này.

## 6. Giới hạn của baseline

- **Database chỉ có 1 face profile.** `CheckInService` duyệt toàn bộ profile mỗi lần check-in, nên
  chi phí so khớp ở đây gần như bằng 0. Baseline này không nói gì về hành vi khi có hàng nghìn
  profile.
- **Bảng lịch sử nhỏ**: `history` đọc 50 dòng từ bảng khoảng 260 bản ghi do chính lượt `checkin`
  sinh ra trước đó.
- **Một worker, không Compose.** Con số này không phải hiệu năng của bản triển khai Compose thật;
  nó là mốc để so sánh trước/sau trong cùng điều kiện.
- **Một lượt đo mỗi cấu hình.** Không có nhiều lần lặp nên chênh lệch dưới ~7% giữa hai backend ở
  `checkin` nên coi là nhiễu, không phải khác biệt thật.
- **Kaggle có thể cấp máy khác nhau giữa các phiên.** Tuần 8 phải đọc lại `cpu_count` và `platform`
  trong metadata; khác cấu hình thì phải đo lại cả baseline.

## 7. Chạy lại

```bash
# Trong Kaggle notebook (Accelerator: None, Internet: On) — xem benchmark-kaggle.md cho đủ 6 cell
uv run python -m scripts.run_baseline \
    --backend sqlite --port 8000 \
    --requests 60 --history-requests 1000 --concurrency 1,2,4,8 \
    --output-dir /kaggle/working/results --notes "kaggle-cpu sqlite phase1"
```

Giữ nguyên `--requests`, `--history-requests`, `--concurrency`, `--warmup` và loại instance khi đo
lại ở Tuần 8. Mỗi lượt đo sinh CSV kèm metadata; thiếu metadata thì lượt đo đó không dùng để so sánh
được.

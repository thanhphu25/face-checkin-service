# Baseline Pha 1 — Kaggle CPU

Số liệu gốc: [benchmark/baseline-sqlite.csv](benchmark/baseline-sqlite.csv) và
[benchmark/baseline-postgresql.csv](benchmark/baseline-postgresql.csv), kèm hai file metadata ghi
phần cứng và toàn bộ tham số. Phương pháp đo và lý do chọn: [Phương pháp benchmark](architecture.md#benchmark).
Cách chạy lại nằm tại [mục Kaggle](#7-chạy-lại-trên-kaggle-cpu).

## 1. Tóm tắt

Đây là số liệu lịch sử tại commit `4affbd0` ngày 2026-09-22. Middleware hiện tại được cập nhật
sau đó; chưa có lượt đo mới hay kết quả trước/sau cải tiến trong bộ dữ liệu này.

- **Đường ghi (`POST /checkins`) là điểm nghẽn**: 4,82 req/s ở một client, trần khoảng 8,5 req/s.
  Đường đọc nhanh hơn khoảng **34 lần** trên cùng máy.
- CPU gần bão hòa khi tăng tải điểm danh; đường đọc dùng ít CPU hơn. Baseline này chưa phân rã
  thời gian từng công đoạn, vì vậy chưa kết luận được tỷ trọng chi phí inference hay database.

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

Cả hai backend đều đạt đỉnh ở concurrency 2. Sau đó SQLite tụt 54,8% so với đỉnh còn PostgreSQL chỉ
giảm 10,9%. p50 của SQLite tăng 16,2 lần từ concurrency 1 đến 8, PostgreSQL tăng 7,1 lần.

Ở concurrency 1, SQLite lại nhanh hơn 17,1% (162,9 so với 139,1 req/s) vì không có chi phí
socket/protocol. Ưu thế đó biến mất ngay khi có tải đồng thời.

## 5. Nhận xét

- Đường check-in có p50 khoảng 206–207 ms ở một client và CPU máy gần bão hòa khi tăng concurrency.
  Throughput tăng ít hơn latency; đổi SQLite sang PostgreSQL không tạo khác biệt lớn ở workload này.
  Đây là dấu hiệu cần khảo sát inference, chưa phải phép đo tách riêng chi phí model và DB.
- Đường đọc đạt đỉnh ở concurrency 2. Tới concurrency 8, SQLite giảm 54,8% throughput so với đỉnh;
  PostgreSQL giảm 10,9%. Kết quả chỉ mô tả cấu hình và dữ liệu đã đo.
- Cần phân rã thời gian và đo tải hỗn hợp/tập profile lớn trước khi chọn cải tiến. Phương án và
  cách đánh giá nằm tại [đề xuất Pha 2](phase-2-improvements.md).

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
- **Kaggle có thể cấp máy khác nhau giữa các phiên.** Mỗi lượt đo so sánh phải đọc lại `cpu_count` và `platform`
  trong metadata; khác cấu hình thì phải đo lại cả baseline.

## 7. Chạy lại trên Kaggle CPU

Notebook đặt Accelerator **None**, Internet **On**. Kaggle notebook không chạy Docker nên runner
thực hiện migration, seed, Uvicorn một worker và benchmark trực tiếp. Ảnh mẫu được lấy qua
`scripts/sample_images.py`; không cần đưa ảnh mặt vào repo.

Các cell dưới đây lấy mã nguồn từ nhánh `main` trên GitHub để đo bản hiện tại. Đây là lượt đo mới;
số liệu lịch sử trong tài liệu vẫn thuộc commit `4affbd0`. Ghi lại commit thực tế và lưu metadata
riêng; khi so sánh Phase 2, chạy cả bản gốc lẫn phương án trên cùng máy.

### Cell 1 — lấy code và cài dependency

```python
!git clone --branch main https://github.com/thanhphu25/face-checkin-service.git /kaggle/working/app
%cd /kaggle/working/app
!git rev-parse HEAD
!pip install --quiet uv
!uv sync --python 3.12 --frozen --extra dev
```

### Cell 2 — secret cho lượt chạy

Giá trị dưới đây chỉ sống trong session notebook và không được commit về repo.

```python
import os, secrets

os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)
os.environ["SEED_ADMIN_PASSWORD"] = secrets.token_urlsafe(24)
os.environ["SEED_USER_PASSWORD"] = secrets.token_urlsafe(24)
```

### Cell 3 — baseline SQLite

```python
!uv run python -m scripts.run_baseline \
    --backend sqlite \
    --port 8000 \
    --requests 60 --history-requests 1000 \
    --concurrency 1,2,4,8 \
    --output-dir /kaggle/working/results \
    --notes "kaggle-cpu sqlite phase1"
```

### Cell 4 — PostgreSQL trong notebook

Kaggle chạy dưới quyền root nên cài được PostgreSQL trực tiếp. Image Kaggle ngày 2026-09-22 cài
cluster **14**, không phải 16, nên dùng `service postgresql start` để không phải gắn cứng số version;
`pg_lsclusters` cho biết cluster thật nếu cần kiểm tra.

Mật khẩu `bench-local-only` dưới đây là giá trị dùng một lần cho một PostgreSQL chỉ sống trong phiên
notebook và chỉ nghe trên `127.0.0.1`. Không dùng lại nó ở bất kỳ môi trường nào khác.

```python
!apt-get -qq update && apt-get -qq install -y postgresql postgresql-contrib
!service postgresql start
!su - postgres -c "psql -c \"CREATE USER bench WITH PASSWORD 'bench-local-only';\""
!su - postgres -c "psql -c 'CREATE DATABASE facecheckin_bench OWNER bench;'"
```

### Cell 5 — baseline PostgreSQL

```python
!uv run python -m scripts.run_baseline \
    --backend postgresql \
    --database-url postgresql+psycopg://bench:bench-local-only@127.0.0.1:5432/facecheckin_bench \
    --port 8001 \
    --requests 60 --history-requests 1000 \
    --concurrency 1,2,4,8 \
    --output-dir /kaggle/working/results \
    --notes "kaggle-cpu postgresql phase1"
```

### Cell 6 — lấy kết quả về

```python
!ls -l /kaggle/working/results
!cat /kaggle/working/results/baseline-sqlite.metadata.json
```

Tải bốn file về và commit vào `docs/benchmark/`:
`baseline-sqlite.csv`, `baseline-sqlite.metadata.json`, `baseline-postgresql.csv`,
`baseline-postgresql.metadata.json`.

## 8. Đọc kết quả và so sánh trước/sau

Mỗi dòng CSV là một scenario/mức concurrency. Throughput tính request/giây; p50/p95/p99 dùng
nearest-rank. CPU máy là 0–100%, CPU server tính theo một core nên có thể vượt 100%.
Harness bỏ warm-up, chờ khoảng lặng mặc định 2 giây; cửa sổ CPU dưới 0,5 giây được báo thiếu.

Để đáp ứng yêu cầu đánh giá trên một cấu hình phần cứng trong [đề bài](2026.md):

1. Dùng cùng phiên/cấu hình Kaggle; đối chiếu cpu_count/platform trong metadata.
2. Giữ cùng model, ảnh, số profile, dữ liệu lịch sử, threshold, workload và tham số tải.
3. Giữ số worker; nếu chính multi-worker là cải tiến, báo cả mốc một worker để đối chiếu.
4. Lặp ít nhất ba lần sau warm-up, báo trung vị và khoảng dao động; thay một yếu tố mỗi thí nghiệm.
5. Kiểm tra error_count và loại lỗi: baseline success-workload cần bằng 0; tải lỗi nghiệp vụ phải
   được tách riêng. Lưu CSV, metadata, commit của cả hai bản và kiểm tra nghiệp vụ/auth/audit.

Khi khác điều kiện đo, không quy đổi thành phần trăm cải thiện trực tiếp; chạy lại cả baseline.
Nếu mở rộng sang tải hỗn hợp hoặc dữ liệu lớn, cả hai bản phải chạy trên workload mới đó.

### Kiểm tra harness không cần Kaggle

Lệnh này chạy được trên máy thường trong khoảng một phút và xác nhận toàn bộ đường đi trước khi tốn
một phiên Kaggle. Số liệu thu được **không** dùng làm baseline.

```bash
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export SEED_ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export SEED_USER_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
uv run python -m scripts.run_baseline \
    --backend sqlite --port 8099 \
    --requests 8 --history-requests 200 --concurrency 1,2 --warmup 2 \
    --output-dir /tmp/benchmark-smoke --notes "smoke, not a baseline"
```

Chạy đúng thì mỗi dòng in ra có `errors=0`, và `/tmp/benchmark-smoke` có một CSV kèm một file
metadata. Với tải nhỏ như trên, hai dòng `history` sẽ báo `cpu_sys=n/a cpu_srv=n/a` — đó là đúng,
không phải lỗi: cửa sổ đo dưới 0,5 giây nên harness từ chối công bố số CPU thay vì công bố nhiễu.
Lượt đo thật trên Kaggle dùng 1000 request nên luôn có đủ số CPU.

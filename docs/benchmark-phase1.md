# Baseline Pha 1 — Kaggle CPU

Notebook: [Face Check-in Benchmark trên Kaggle](https://www.kaggle.com/code/tphu25/face-checkin-benchmark).
Số liệu gốc: [benchmark/baseline-sqlite.csv](benchmark/baseline-sqlite.csv) và
[benchmark/baseline-postgresql.csv](benchmark/baseline-postgresql.csv), kèm hai file metadata ghi
cấu hình máy và tham số tải. Phương pháp đo: [Phương pháp benchmark](architecture.md#benchmark).
Cách chạy lại nằm tại [mục Kaggle](#7-chạy-lại-trên-kaggle-cpu).

## 1. Tóm tắt

Bộ số liệu hiện hành được đo ngày **27/10/2026** tại commit `3503b24`. CSV và metadata do người
chạy cung cấp từ lượt notebook có thời điểm ghi kết quả SQLite **10:53:08** và PostgreSQL
**10:55:26**, giờ Việt Nam (UTC+7). Đây là baseline Pha 1, chưa có kết quả trước/sau cải tiến Pha 2.

- Check-in đạt **6,27–6,42 req/s** ở một client và **9,66–10,14 req/s** ở concurrency 8.
  CPU máy gần bão hòa khi tăng tải; chưa đo riêng chi phí inference, matching và database.
- History đạt đỉnh ở concurrency 2: **142,43 req/s** với SQLite và **124,41 req/s** với PostgreSQL.
- Cả **8.480 request đo** trên 16 tổ hợp backend/scenario/concurrency đều trả mã HTTP thành công.

## 2. Điều kiện đo

| Hạng mục | Giá trị |
|---|---|
| Ngày đo | 2026-10-27 |
| Commit | `3503b24` |
| Máy | Kaggle CPU notebook, 4 core, Linux 6.18.55, glibc 2.39, Python 3.12.3 |
| Server | Uvicorn 1 worker, không dùng Docker Compose |
| Model | `buffalo_s` (InsightFace), CPU |
| Dữ liệu | 1 face profile; cùng ảnh JPEG mẫu để đăng ký và check-in |
| Tải mỗi mức | 60 request cho `checkin`, 1000 request cho `history` |
| Concurrency | 1, 2, 4, 8 |
| Warm-up | 5 request mỗi mức, không tính vào số liệu |
| Khoảng nghỉ | 2 giây sau warm-up, trước khi đo |
| Lỗi HTTP | 0/8.480 request; check-in trả `201`, history trả `200` |

Hai cột CPU khác đơn vị: **CPU máy** là phần trăm của cả 4 core (tối đa 100), **CPU server** là phần
trăm của một core cho riêng tiến trình Uvicorn (390% ≈ 3,9 core). CPU máy gồm cả client tạo tải và
các tiến trình khác; CPU server không gồm tiến trình PostgreSQL.

## 3. `POST /api/v1/checkins` — đường ghi, có inference

| Backend | Concurrency | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | CPU máy (%) | CPU server (% 1 core) |
|---|---:|---:|---:|---:|---:|---:|---:|
| SQLite | 1 | 6.272 | 159.61 | 172.06 | 181.08 | 76.1 | 295.8 |
| SQLite | 2 | 8.385 | 227.64 | 275.99 | 288.25 | 95.1 | 370.9 |
| SQLite | 4 | 8.771 | 454.85 | 554.64 | 617.77 | 99.3 | 387.5 |
| SQLite | 8 | 9.655 | 827.0 | 977.07 | 1077.79 | 99.8 | 389.6 |
| PostgreSQL | 1 | 6.424 | 154.85 | 167.79 | 173.81 | 76.1 | 295.4 |
| PostgreSQL | 2 | 8.933 | 220.32 | 254.81 | 275.98 | 92.7 | 360.7 |
| PostgreSQL | 4 | 8.947 | 444.92 | 634.82 | 731.44 | 99.7 | 390.8 |
| PostgreSQL | 8 | 10.14 | 777.94 | 874.75 | 915.3 | 99.7 | 389.2 |

Từ concurrency 1 lên 8, throughput tăng **53,9%** (SQLite) và **57,8%** (PostgreSQL), trong khi p50
tăng **5,2** và **5,0 lần**. CPU máy ở concurrency 4–8 đạt 99,3–99,8%, CPU server khoảng 3,9 core.
Tăng tải đồng thời làm độ trễ tăng mạnh, còn throughput tăng ít hơn; đây là dấu hiệu bão hòa CPU
trong cấu hình đã đo.

## 4. `GET /api/v1/checkins` — đường đọc, có JWT

| Backend | Concurrency | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | CPU máy (%) | CPU server (% 1 core) |
|---|---:|---:|---:|---:|---:|---:|---:|
| SQLite | 1 | 125.745 | 7.84 | 8.87 | 9.94 | 29.3 | 76.5 |
| SQLite | 2 | 142.427 | 13.59 | 16.4 | 18.12 | 39.3 | 107.2 |
| SQLite | 4 | 106.683 | 37.14 | 47.92 | 56.73 | 45.8 | 132.6 |
| SQLite | 8 | 73.185 | 109.33 | 128.04 | 177.45 | 47.8 | 153.6 |
| PostgreSQL | 1 | 94.712 | 10.37 | 12.07 | 13.44 | 31.2 | 69.8 |
| PostgreSQL | 2 | 124.405 | 15.75 | 18.18 | 20.29 | 45.6 | 103.9 |
| PostgreSQL | 4 | 116.285 | 33.58 | 41.18 | 65.57 | 48.0 | 113.8 |
| PostgreSQL | 8 | 107.658 | 70.38 | 104.8 | 131.2 | 53.5 | 126.7 |

Cả hai backend đạt đỉnh ở concurrency 2. Tới concurrency 8, throughput SQLite giảm **48,6%** so với
đỉnh, PostgreSQL giảm **13,5%**. Ở mức này PostgreSQL đạt 107,658 req/s, SQLite đạt 73,185 req/s;
p95 lần lượt là 104,8 và 128,04 ms. Các chênh lệch chỉ mô tả lượt đo này.

## 5. Nhận xét

- Check-in có p50 khoảng 155–160 ms ở một client và CPU máy gần bão hòa khi tăng concurrency.
  Chưa có phép đo tách riêng để kết luận tỷ trọng chi phí inference, matching hay database.
- History có throughput cao hơn check-in; trong lượt này PostgreSQL giữ throughput tốt hơn SQLite
  khi tăng từ concurrency 2 lên 8. Chưa đủ số lượt để kết luận ưu thế ổn định giữa hai backend.
- Bộ đo đáp ứng phần kiểm thử tải trên Kaggle CPU của [Pha 1](2026.md). Nó chưa đánh giá khả năng
  mở rộng tập profile, độ chính xác nhận diện hay triển khai nhiều worker.
- Nếu triển khai Pha 2, cần đo lại cả bản gốc và phương án trong cùng điều kiện. Các hướng khảo sát
  nằm tại [đề xuất Pha 2](phase-2-improvements.md).

## 6. Giới hạn của baseline

- **Database chỉ có 1 face profile.** `CheckInService` duyệt toàn bộ profile mỗi lần check-in;
  baseline này chưa thể hiện chi phí khi có hàng nghìn profile.
- **Bảng lịch sử nhỏ**: `history` đọc 50 dòng từ bảng khoảng 260 bản ghi do seed và lượt
  `checkin` sinh ra trước đó.
- **Một ảnh mẫu cho cả đăng ký và check-in.** HTTP thành công trên ảnh này chưa chứng minh khả
  năng nhận diện đúng với ảnh chụp khác, người chưa đăng ký hoặc các điều kiện ánh sáng khác.
- **Một worker, không Compose.** Kết quả chỉ đại diện cách chạy trực tiếp trong notebook.
- **Một lượt cho mỗi cấu hình.** Chưa có số liệu đo lặp để báo trung vị và khoảng dao động.
- **Chỉ 60 request check-in mỗi mức.** Với nearest-rank, p99 chính là giá trị lớn nhất của lượt;
  ưu tiên đọc p50/p95 và coi p99 là thông tin tham khảo.
- **Metadata chưa ghi model CPU, giới hạn CPU container và RAM.** `cpu_count`/`platform` giúp
  đối chiếu nhưng chưa xác nhận đầy đủ cấu hình phần cứng giữa hai phiên.

## 7. Chạy lại trên Kaggle CPU

Notebook đặt Accelerator **None**, Internet **On**. Kaggle notebook không chạy Docker nên runner
thực hiện migration, seed, Uvicorn một worker và benchmark trực tiếp. Ảnh mẫu được lấy qua
`scripts/sample_images.py`; không cần đưa ảnh mặt vào repo.

Các cell dưới đây lấy mã nguồn từ nhánh `main` trên GitHub để đo bản hiện tại. Mỗi lần chạy tạo
một bộ số liệu mới; bảng hiện hành trong tài liệu thuộc commit `3503b24`, lượt ngày 27/10/2026.
Ghi lại commit thực tế và lưu metadata riêng; khi so sánh Phase 2, chạy cả bản gốc lẫn phương án
trên cùng máy.

Mỗi lượt xác nhận nên bắt đầu bằng một phiên notebook mới và chạy các cell theo thứ tự để database
trở về cùng trạng thái ban đầu. Dùng 60 request check-in, 1000 request history và warm-up 5
cho baseline Pha 1; mỗi phiên chỉ đo một lượt cho mỗi backend.

### Cell 1 — lấy code và cài dependency

```python
# Lấy mã nguồn hiện tại, ghi lại commit và cài dependency trong môi trường riêng.
!git clone --branch main https://github.com/thanhphu25/face-checkin-service.git /kaggle/working/app
%cd /kaggle/working/app
!git rev-parse HEAD
!pip install --quiet uv
!uv sync --python 3.12 --frozen --extra dev
```

### Cell 2 — secret cho lượt chạy

Giá trị dưới đây chỉ sống trong session notebook và không được commit về repo.

```python
# Tạo secret và mật khẩu ngẫu nhiên dùng riêng cho phiên benchmark.
import os, secrets

os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)
os.environ["SEED_ADMIN_PASSWORD"] = secrets.token_urlsafe(24)
os.environ["SEED_USER_PASSWORD"] = secrets.token_urlsafe(24)
```

### Cell 3 — hiển thị ảnh mẫu

Ảnh hiển thị là đúng phần khuôn mặt đã cắt và mã hóa JPEG mà seed và benchmark sử dụng.
Lệnh lấy ảnh chạy trong môi trường `uv` của dự án, còn notebook chỉ đọc file JPEG để hiển thị.

```python
# Hiển thị đúng ảnh khuôn mặt mẫu dùng để đăng ký profile và gửi request check-in.
import subprocess
from IPython.display import Image, display

sample_path = "/kaggle/working/sample-face.jpg"
subprocess.run(
    [
        "uv", "run", "python", "-c",
        "from pathlib import Path; "
        "from scripts.sample_images import face_image_bytes; "
        f"Path({sample_path!r}).write_bytes(face_image_bytes())",
    ],
    check=True,
)
display(Image(filename=sample_path))
```

### Cell 4 — baseline SQLite

```python
# Đo tải check-in và đọc lịch sử trên SQLite với bốn mức request đồng thời.
!uv run python -m scripts.run_baseline \
    --backend sqlite \
    --port 8000 \
    --requests 60 --history-requests 1000 \
    --concurrency 1,2,4,8 \
    --output-dir /kaggle/working/results \
    --notes "kaggle-cpu sqlite phase1"
```

### Cell 5 — PostgreSQL trong notebook

Kaggle chạy dưới quyền root nên cài được PostgreSQL trực tiếp. Dùng `service postgresql start`
để không phải gắn cứng số version; `pg_lsclusters` cho biết cluster thật nếu cần kiểm tra.

Mật khẩu `bench-local-only` dưới đây là giá trị dùng một lần cho một PostgreSQL chỉ sống trong phiên
notebook và chỉ nghe trên `127.0.0.1`. Không dùng lại nó ở bất kỳ môi trường nào khác.

```python
# Cài và khởi động PostgreSQL rồi tạo tài khoản và database riêng cho benchmark.
!apt-get -qq update && apt-get -qq install -y postgresql postgresql-contrib
!service postgresql start
!su - postgres -c "psql -c \"CREATE USER bench WITH PASSWORD 'bench-local-only';\""
!su - postgres -c "psql -c 'CREATE DATABASE facecheckin_bench OWNER bench;'"
```

### Cell 6 — baseline PostgreSQL

```python
# Đo tải trên PostgreSQL với cùng ảnh mẫu và tham số tải như SQLite.
!uv run python -m scripts.run_baseline \
    --backend postgresql \
    --database-url postgresql+psycopg://bench:bench-local-only@127.0.0.1:5432/facecheckin_bench \
    --port 8001 \
    --requests 60 --history-requests 1000 \
    --concurrency 1,2,4,8 \
    --output-dir /kaggle/working/results \
    --notes "kaggle-cpu postgresql phase1"
```

### Cell 7 — kiểm tra và lấy kết quả về

```python
# Liệt kê file kết quả và hiển thị cấu hình thực tế của cả hai lượt đo.
!ls -l /kaggle/working/results
!cat /kaggle/working/results/baseline-sqlite.metadata.json
!cat /kaggle/working/results/baseline-postgresql.metadata.json
```

Lưu version notebook kèm output các cell để giữ lại ảnh mẫu, log chạy và cấu hình đo.
Tải bốn file về để đối chiếu trước khi cập nhật số liệu trong `docs/benchmark/`:
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

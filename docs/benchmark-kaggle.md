# Chạy baseline Pha 1 trên Kaggle CPU

Kaggle notebook không chạy Docker, nên baseline không dùng Compose. `scripts/run_baseline.py` dựng
lại đúng các bước Compose làm, trong một cây tiến trình duy nhất: migration Alembic → seed dữ liệu
mẫu → Uvicorn một worker → benchmark → dừng server.

Giữ nguyên loại instance và mọi tham số giữa Tuần 6 và Tuần 8. Nếu một trong hai lần đo khác loại
máy, số liệu trước/sau không so sánh được.

## 1. Điều kiện đo

| Hạng mục | Giá trị Tuần 6 | Ghi chú |
|---|---|---|
| Accelerator | **None (CPU)** | Không bật GPU/TPU |
| Internet | **On** | Cần để `pip`/`apt` và tải model `buffalo_s` |
| Server | Uvicorn, **1 worker** | Multi-worker là cải tiến Pha 2, không nằm trong baseline |
| Database | SQLite và PostgreSQL | Chạy hai lượt riêng, ghi hai file CSV riêng |
| Model | `buffalo_s`, CPU | Tải lần đầu ở bước warm-up |

Hai cột CPU có đơn vị khác nhau, đọc nhầm là hiểu sai toàn bộ kết quả:

- `cpu_percent_system` — phần trăm của **toàn máy**, 0–100%. 99% nghĩa là mọi core đều bận.
- `cpu_percent_server` — phần trăm của **một core**, vượt 100% được. 389% nghĩa là tiến trình
  Uvicorn chiếm 3,89 core.

Số core Kaggle cấp nằm ở `cpu_count` trong file metadata; luôn đọc `cpu_percent_server` cùng giá trị
đó.

## 2. Các cell trong notebook

### Cell 1 — lấy code và cài dependency

```python
!git clone --branch week6 https://github.com/thanhphu25/face-checkin-service.git /kaggle/working/app
%cd /kaggle/working/app
!pip install --quiet uv
!uv sync --frozen --extra dev
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

## 3. Đọc kết quả

Mỗi dòng CSV là một mức concurrency của một scenario:

| Cột | Ý nghĩa |
|---|---|
| `scenario` | `checkin` = `POST /api/v1/checkins` (công khai, chạy InsightFace); `history` = `GET /api/v1/checkins?limit=50` (có JWT) |
| `throughput_rps` | Request/giây của toàn bộ lượt đo |
| `p50_ms`, `p95_ms`, `p99_ms` | Percentile nearest-rank, nên luôn là một giá trị thật đã quan sát |
| `cpu_percent_system` | CPU toàn máy trong cửa sổ đo, 0–100% |
| `cpu_percent_server` | CPU riêng tiến trình Uvicorn, phần trăm của một core (vượt 100% được) |
| `error_count` | Phải bằng 0; khác 0 thì lượt đo đó không dùng được |

Harness bỏ warm-up ra khỏi số liệu và chờ `--settle-seconds` (mặc định 2s) trước khi lấy mẫu CPU, vì
thread pool của ONNX Runtime còn quay sau mỗi lần inference và nếu không chờ sẽ bị tính nhầm sang
mức đo kế tiếp.

## 4. Gói bàn giao benchmark

Năm thứ dưới đây là toàn bộ những gì cần để đo lại. Không cần hỏi lại tác giả, không cần dataset,
không cần file nào ngoài repo.

| Thành phần | Đường dẫn | Vai trò |
|---|---|---|
| Harness | `scripts/benchmark.py` | Sweep concurrency, đo latency/throughput/CPU, ghi CSV + metadata |
| Runner | `scripts/run_baseline.py` | Chạy trọn migration → seed → Uvicorn → đo → dừng server |
| Dữ liệu mẫu | `scripts/seed.py` | Tạo tài khoản, face profile và lịch sử tất định |
| Ảnh benchmark | `scripts/sample_images.py` | Crop từ ảnh mẫu trong package InsightFace; repo không chứa ảnh mặt |
| Số liệu Tuần 6 | `docs/benchmark/*.csv` + `*.metadata.json` | Mốc so sánh cho Pha 2 |

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

### Quy tắc so sánh ở Tuần 8

Một lượt đo mới chỉ so sánh được với baseline Tuần 6 khi **tất cả** điều kiện sau đúng:

1. Cùng loại instance Kaggle CPU — đối chiếu `cpu_count` và `platform` trong metadata hai lượt.
2. Cùng `requests_per_level`, `history_requests_per_level`, `concurrency_levels`, `warmup_per_level`
   và `settle_seconds`.
3. Cùng số face profile trong database (seed mặc định tạo đúng 1).
4. `error_count = 0` ở mọi mức đo.
5. Cùng số worker Uvicorn, trừ khi chính multi-worker là cải tiến đang đo — khi đó phải báo cáo cả
   cấu hình một worker để còn đối chiếu với Tuần 6.

Lệch bất kỳ điều kiện nào thì ghi rõ trong báo cáo so sánh và không quy đổi thành phần trăm cải
thiện.

## 5. Trạng thái kiểm chứng

- Đã chạy thật trên Kaggle CPU ngày 2026-09-22 với commit `4affbd0`, instance 4 core, Python
  3.12.13, cho cả SQLite lẫn PostgreSQL. Toàn bộ 16 mức đo đều `error_count=0`.
- Bản đầu tiên của cell 4 dùng `pg_ctlcluster 16 main start` và **không chạy được**: image Kaggle
  cài cluster 14. Cell hiện tại là lệnh đã chạy thành công.
- Số liệu thu được nằm ở [docs/benchmark/](benchmark/), phân tích ở
  [benchmark-phase1.md](benchmark-phase1.md).

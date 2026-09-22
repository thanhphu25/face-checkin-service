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

## 4. Trạng thái kiểm chứng

- Đã chạy thật trên Kaggle CPU ngày 2026-09-22 với commit `4affbd0`, instance 4 core, Python
  3.12.13, cho cả SQLite lẫn PostgreSQL. Toàn bộ 16 mức đo đều `error_count=0`.
- Bản đầu tiên của cell 4 dùng `pg_ctlcluster 16 main start` và **không chạy được**: image Kaggle
  cài cluster 14. Cell hiện tại là lệnh đã chạy thành công.
- Số liệu thu được nằm ở [docs/benchmark/](benchmark/), phân tích ở
  [benchmark-phase1.md](benchmark-phase1.md).

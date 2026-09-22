# Xác minh hoàn tất kỹ thuật Tuần 6

Ngày chạy cuối: 2026-09-22.

## Môi trường và phạm vi

- Baseline: Kaggle CPU notebook, 4 core, Linux 6.12.90, Python 3.12.13, commit `4affbd0`.
- Kiểm chứng release: máy dev Linux 12 core, Docker Engine 29.8.1, Compose v5.5.1, uv 0.12.5.
- PostgreSQL 16-alpine, Redis 7.4-alpine, InsightFace `buffalo_s` chạy CPU.
- Mọi secret, mật khẩu, tên database và port trong tài liệu này đều là giá trị dùng một lần cho
  verification, không phải giá trị thật.

## Baseline trên Kaggle CPU

Hai lượt đo thật trên Kaggle CPU notebook, SQLite và PostgreSQL, mỗi lượt 8 mức đo:

```text
concurrency 1,2,4,8 × {checkin, history}
checkin:  60 request/mức, warm-up 5
history:  1000 request/mức, warm-up 5
16/16 mức đo error_count = 0
```

Số liệu gốc nằm ở [benchmark/](benchmark/) kèm metadata ghi `cpu_count`, `platform`, `git_commit` và
toàn bộ tham số. Phân tích ở [benchmark-phase1.md](benchmark-phase1.md), phương pháp ở
[ADR 0005](adr/0005-benchmark-method-and-baseline-conditions.md).

Hai điều chỉnh xuất phát từ việc chạy thật chứ không phải từ suy luận:

1. Cửa sổ đo CPU ngắn hơn 0,5 giây bị lượng tử hoá thành nhiễu; harness báo thiếu thay vì báo số.
2. Thread pool ONNX Runtime còn quay sau inference. Trước khi thêm khoảng lặng, mức `history`
   đầu tiên bị tính 720% CPU của mức `checkin` trước đó và throughput đọc thấp hơn 42%.

Cell PostgreSQL trong hướng dẫn Kaggle ban đầu dùng `pg_ctlcluster 16 main start` và **không chạy
được**: image Kaggle cài cluster 14. Tài liệu đã được sửa theo lệnh chạy thành công thật.

## CI trên branch `week6`

GitHub Actions run [`35706042357`](https://github.com/thanhphu25/face-checkin-service/actions/runs/35706042357)
của commit `4affbd0`, cả bốn job `success`: `quality-and-sqlite`, `postgres-integration`,
`docker-image`, `compose-clean-setup`. Trước đó `week6` không nằm trong push trigger nên không có
job nào chạy; commit `30f6329` sửa việc này.

## Compose, seed và bàn giao

Project cách ly `facecheckin_w6_release`, image `face-checkin-service:w6-release`, port riêng
58201/55441/56391. Các bước đã chạy và kết quả:

```text
docker compose config --quiet            # pass
docker compose build                     # pass
docker compose up -d --wait              # app/postgres/redis healthy; migrate exited 0
python -m scripts.seed (tu host)         # admin id=1, user id=2, face profile id=1, 3 ban ghi lich su
GET /health                              # 200 {"status":"ok"}
POST /api/v1/auth/login (admin mau)      # 200, tra access token
GET /api/v1/auth/me                      # admin.sample@example.test / admin
GET /api/v1/checkins (admin)             # 3 ban ghi: no_face, unmatched, success
GET /api/v1/checkins (khong token)       # 401
GET /docs                                # 200
GET /openapi.json                        # 9 path, khop tuyet doi voi docs/openapi.json da commit
POST /api/v1/checkins (anh mau)          # success, similarity 1.0, full_name "User Mau"
docker compose down -v --remove-orphans  # 0 container, 0 volume con lai theo label project
```

Seed chạy từ host chứ không chạy trong container: ảnh mẫu lấy từ package InsightFace, mà runtime
image cố ý loại bỏ `scripts/` và thư mục ảnh đó. README ghi rõ ràng buộc này.

## Rà soát secret

```text
git ls-files | grep -iE '\.env$|\.db$|\.sqlite|\.onnx$|\.pem$|\.key$|id_rsa|credentials'
# chi co .env.example (toan bo la placeholder)

git grep -InE "(password|secret|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]" -- . ':!tests' ':!docs'
# khong con ket qua nao sau khi loai gia tri test/placeholder
```

Giá trị `bench-local-only` trong hướng dẫn Kaggle là mật khẩu dùng một lần cho PostgreSQL chỉ tồn
tại trong phiên notebook và chỉ nghe trên `127.0.0.1`; không dùng lại ở bất kỳ môi trường nào khác.
Không có ảnh khuôn mặt, database, model cache, ONNX, token hay `.env` nào bị commit.

## Quality gates cuối

```text
uv run ruff check .                      # pass
uv run ruff format --check .             # pass
uv run lint-imports                      # 3/3 contracts kept
uv run pytest -q -m "not real_model" tests/unit tests/api tests/integration
# 106 passed, 13 skipped, 1 deselected
git diff --check                         # pass
```

## Phần chưa hoàn tất

- Tag `v1.0-phase1` chưa được tạo. Tag là thao tác release do chủ project quyết định, không phải
  commit.
- "Đã nhận hệ thống từ nhóm khác" là sự kiện bên ngoài, chưa xảy ra.
- Tài liệu này không tuyên bố có review chéo hay ký xác nhận của con người cho từng dòng checklist
  bàn giao; các dòng được tick dựa trên bằng chứng kỹ thuật ghi ở trên, theo đúng phương án thay thế
  đã áp dụng từ Tuần 4.

# Kiểm chứng local · 23020023

Ngày 27/11/2026, Windows, Python 3.12.10. Base `247db09d98f4cedcc9ad22fdbd112ba328324aa9`. SHA code runner `b34aaa82e9d68298f3acf5481f241c5ed3c097f7`. Các thư mục `r1/` và `r2/` chứa kết quả từ `RunnerTests.test_http_cell_counts_warmup_separately` dùng `httpx.MockTransport` kết hợp SQLite thật.

| Lệnh | Exit | Kết quả |
|---|---:|---|
| `uv sync --python 3.12 --frozen --extra dev` | 0 | Cài đặt đầy đủ 85 gói khóa từ `uv.lock` trên Python 3.12.10. |
| `uv run ruff check .` | 0 | Toàn bộ kiểm tra lint đạt. |
| `uv run ruff format --check .` | 0 | 91 file đạt chuẩn format. |
| `uv run lint-imports` | 0 | 3 contract kiến trúc giữ nguyên, 0 vi phạm. |
| `uv build` | 0 | Build sdist và wheel thành công. |
| `uv run pytest -q -m "not real_model"` | 0 | 152 passed, 14 skipped (PostgreSQL/gated), 1 deselected (`real_model`). Bao gồm 7 test trong `RunnerTests` (gồm `test_probe_skips_embedder_load_for_gallery_benchmark`) và `test_matching_skips_different_dimension`. |
| `PHASE2_LOCAL_SMOKE=... uv run python -m unittest tests.unit.test_phase2_bench.RunnerTests.test_http_cell_counts_warmup_separately -v` | 0 | 2 lượt smoke cùng checksum snapshot `76b5ab18...`, user 7, profile 9, mỗi lượt 5 warm-up + 6/6 request 201 đúng body, 11/11 audit, 0 timeout. |
| `PHASE2_R1=1 uv run python -m unittest tests.unit.test_phase2_bench.TransactionTests -v` (trên SHA A `247db09`) | 1 | `test_matching_skips_different_dimension` PASS. Trong `test_r1_ten_independent_requests_per_case`: 40/40 lượt `empty`, `unmatched`, `invalid`, `system` PASS; 10/10 lượt `business` (`MultipleFacesDetected` sau flush) FAIL đúng như giả thuyết vì `app/api/deps.py::get_session` ở bản gốc `247db09` commit mọi `DomainError` (để lại 1 bản ghi `unmatched` dở mỗi lượt). |
| Kiểm tra cú pháp 3 cell code của `docs/benchmark/phase2/kaggle-23020023.ipynb` | 0 | Biên dịch hợp lệ cả 3 cell code. |

Ghi chú: Máy Kaggle CPU, SHA nhánh đơn lẻ sau PR và SHA tích hợp B chưa chạy trong lượt kiểm chứng local này.

# Phase 2 · Nghiệm thu trên Kaggle CPU

**Chưa có kết luận về tốc độ của ứng dụng.** Base `main` ở `247db09d98f4cedcc9ad22fdbd112ba328324aa9` (A). Chưa có SHA tích hợp B. Runner được kiểm chứng cục bộ ở `b34aaa82e9d68298f3acf5481f241c5ed3c097f7` (sửa `probe()` để không nạp `InsightFaceEmbedder` khi đo gallery query+match). Chưa chạy pilot bằng model thật trên Kaggle CPU.

| Phép kiểm | Bằng chứng hiện có | Kết luận |
|---|---|---|
| Gate chất lượng & test suite (`b34aaa8`) | `uv sync --frozen --extra dev`, `uv build`, `ruff check .`, `ruff format --check .`, `lint-imports` (3/3 contract), `pytest -q -m "not real_model"` (152 passed, 14 skipped, 1 deselected). | PASS trên Python 3.12.10. |
| Smoke logic & probe RSS (`b34aaa8`) | Hai bản sao SQLite, C=2, mỗi lượt 5 warm-up + 6 POST qua `httpx.MockTransport` (6/6 body đúng, 11/11 audit, 0 timeout). Test `test_probe_skips_embedder_load_for_gallery_benchmark` xác nhận `probe` không gọi `get_embedder()`. | PASS cho logic client, đối chiếu DB và cô lập RSS probe. |
| Gallery tổng hợp (`b34aaa8`) | Hai lần tạo mỗi fixture. Gallery thuần có 1.000/1.000 profile cùng model, gallery hỗn hợp có 500/1.000. Cả hai giữ user 7, profile 9 của test. | PASS cho tính tái lập và cardinality. |
| R1 trên SHA A (`247db09`) & parity sai chiều | `test_matching_skips_different_dimension` PASS. R1 trên A (`PHASE2_R1=1`): 40/40 lượt `empty`, `unmatched`, `invalid`, `system` PASS; 10/10 lượt `business` sau flush FAIL vì `get_session` của A commit mọi `DomainError`. | Đã tái lập lỗi ghi dở trên bản gốc A; chờ đo lại sau khi PR của Đạt (3/4) merge vào B. |
| E1, E2, E3, M1 trên A/B | Chưa chạy trên Kaggle CPU và chưa có SHA tích hợp B. | Chưa có giá trị p95, RPS, CPU, RSS của app. |
| Docker, Compose, PostgreSQL 16 | Chờ kết quả GitHub Actions CI trên PR của `test/23020023-kaggle-ab`. | Chờ xác nhận CI. |

Xem [CSV và metadata smoke cục bộ](benchmark/phase2/smoke-23020023-b34aaa8/) và [notebook chạy lại](benchmark/phase2/kaggle-23020023.ipynb). Giá trị latency trong CSV smoke bao gồm mock transport và SQLite test. Chỉ dùng chúng để kiểm tra luồng ghi bằng chứng.

## Chạy lại

Import notebook vào Kaggle, chọn CPU và chạy từ kernel mới. Cấp `PHASE2_RUNNER` là SHA tooling đã push. Để đo từng nhánh, truyền SHA đầy đủ bằng `PHASE2_SON` và `PHASE2_THANH`. Chỉ truyền `PHASE2_B` khi đã chốt ba PR kỹ thuật. Checkout phải truy cập được từ Kaggle. Notebook tự tạo mật khẩu seed, JWT secret, ba checkout độc lập và virtualenv Python 3.12 cho từng checkout. Snapshot chứa embedding và hash mật khẩu, chỉ manifest checksum và dữ liệu đo được đưa vào bằng chứng.

Ba lệnh dưới đây có thể chạy độc lập từ checkout runner đã commit, sau khi tạo các biến môi trường như ô đầu của notebook. `A`, `B` là đường dẫn tuyệt đối tới các checkout, `FX` là một thư mục fixture mới. `OUT` dành cho **một** thử nghiệm ghép cặp. `SESSION` giữ nguyên trong cùng kernel.

```bash
uv sync --frozen --extra dev
uv run python -m scripts.phase2_bench prepare --app "$A" --python "$A/.venv/bin/python" --fixtures "$FX"
uv run python -m scripts.phase2_bench run --scenario E1 --c 4 --round 1 --session "$SESSION" --app "$A" --python "$A/.venv/bin/python" --fixtures "$FX" --output "$OUT"
uv run python -m scripts.phase2_bench compare --a "$(git -C "$A" rev-parse HEAD)" --b "$(git -C "$B" rev-parse HEAD)" --session "$SESSION" --output "$OUT" --table "$OUT/AB-23020023.csv"
```

`compare` cần đủ 15 ô ở cả hai SHA và ít nhất ba cặp. Notebook chạy smoke baseline cũ, hai smoke từ snapshot, pilot A rồi ghi freeze.json. Sau pilot, công bố manifest và SHA runner trong draft PR trước lượt merge đầu tiên. Nếu runner thay đổi, dùng thư mục output mới và chạy lại cả cặp. Khi đổi máy giữa chừng, ghi lý do và chạy lại cặp trên cùng máy. Bản tích hợp là lượt merge 4/4.

| Ô đo | Tải mỗi lượt | Oracle |
|---|---|---|
| E1 | 60 POST tại từng C=1,2,4,8 | HTTP 201, user, profile, status, ID và mỗi ID tương ứng đúng một audit mới |
| E2 | 1.000 GET tại từng C=1,2,4,8 | 200, đúng 50 ID của user theo thời gian rồi ID giảm dần, delta DB bằng 0 |
| E3 | 60 POST tại C=1,4 cho mỗi gallery | Cùng ảnh, cùng profile thật, cùng chiều vector, top-1 duy nhất |
| probe | 60 lần query + match C=1 cho mỗi gallery | Chạy service của checkout đích, thay embed bằng vector cố định (không nạp `get_embedder()`) và thu record tại cổng ghi |
| M1 | Một cold init/process, 5 warm-up rồi 60 lần embed C=1 | Adapter nhận đúng một mặt, vector khớp profile A trong sai số, cosine vượt ngưỡng |
| R1 | 10 request cho mỗi case, ghi CSV status/record_id/delta | No-face, unmatched có 1 audit. Ảnh hỏng, lỗi nghiệp vụ sau flush và lỗi hệ thống sau flush có 0 audit |

Mỗi ô HTTP khởi động một Uvicorn worker và một bản sao snapshot độc lập. Login, 5 warm-up và 2 giây nghỉ nằm ngoài phép đo. Mỗi request có timeout 60 giây. CPU process tính theo một lõi. Peak RSS HTTP là giá trị VmRSS lớn nhất lấy mẫu mỗi 50 ms. Probe ghi VmHWM của process riêng, có tính cả startup (`M1` nạp `get_embedder()`, còn `probe` gallery không nạp model để tránh cộng bộ nhớ ONNX). CPU không đủ cửa sổ lấy mẫu được ghi null. So sánh RSS trong cùng loại phép đo.

## Quyết định nghiệm thu

Mục tiêu trước pilot là giảm p95 E1 tại C=4 ít nhất 10%, giảm p95 probe gallery hỗn hợp ít nhất 20%. p95 E2 tại C=4 và E3 thuần được tăng tối đa 10%. RPS thành công E1 được giảm tối đa 5%. Yêu cầu đúng danh tính, quyết định và số audit ở mọi lượt. Khi có kết quả, ghi cả ô thất bại, SHA và nguyên nhân tại bảng trên. Nếu bỏ một tối ưu riêng, chạy lại A/B trên SHA tích hợp đã sửa.

Với mỗi ô, bảng CSV báo median [min, max] của từng chỉ số qua ba lượt, hiệu B−A theo đơn vị gốc và phần trăm. Latency giảm dùng (A−B)/A, RPS tăng dùng (B−A)/A. Khi A bằng 0, phần trăm để trống. Nếu chênh lệch nhỏ hơn dao động giữa các lượt, tăng số cặp hoặc ghi “chưa phân biệt được”. Với 60 mẫu, p99 gần cực đại. Đối chiếu riêng CSV R1 trước khi chấp nhận kết quả hiệu năng.

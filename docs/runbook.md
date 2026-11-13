# Runbook (vận hành)

## 1. Bật TabPFN

1. Tạo tài khoản tại https://ux.priorlabs.ai, chấp nhận điều khoản, lấy token API.
2. Trong cài đặt tài khoản, tắt tuỳ chọn cho dùng dữ liệu để cải thiện model nếu không muốn.
3. Trên máy (PowerShell), rồi mở terminal mới:
   ```powershell
   [Environment]::SetEnvironmentVariable("TABPFN_TOKEN", "<token>", "User")
   ```
4. Thử một điểm gốc để đo chi phí, xem lượng token đã dùng trên trang tài khoản:
   ```
   uv run bnbforecast backtest tabpfn --max-origins 1
   ```
5. Chạy hết backtest. Lệnh tự chạy tiếp từ chỗ dừng, nên có thể chia qua nhiều ngày nếu hết hạn mức:
   ```
   uv run bnbforecast backtest tabpfn --max-origins 60
   uv run bnbforecast summarize
   ```
6. Trên GitHub: Settings → Secrets and variables → Actions → New repository secret, tên `TABPFN_TOKEN`.

Không ghi token vào file, không commit, không dán vào chat.

## 2. Việc hằng ngày (tự động)

Workflow `daily-forecast` chạy 01:23 UTC: lấy nến mới, dự báo, ghi nhật ký, chấm các dự báo đã đáo hạn, commit,
deploy Pages. Lỗi thì tự mở issue. Chạy tay: tab Actions → daily-forecast → Run workflow.

## 3. Khi có sự cố

| Dấu hiệu | Nguyên nhân thường gặp | Xử lý |
|---|---|---|
| Web hiện ngày cũ | Workflow lỗi hoặc bị GitHub tắt sau 60 ngày repo không hoạt động | Xem tab Actions, bật lại workflow |
| Log ghi `binance failed … trying kraken` | Runner bị chặn theo vùng | Không cần làm gì; dòng dữ liệu có `source=kraken` |
| `missing day(s) in market data` | Cả hai nguồn thiếu một ngày | Chạy lại sau; không sửa tay file CSV |
| TabPFN lỗi 429 | Hết hạn mức ngày | Model khác vẫn chạy; TabPFN có lại hôm sau |
| TabPFN lỗi đăng nhập | Token hết hạn | Tạo token mới, cập nhật secret |

## 4. Không được làm

- Không sửa `data/forecast-log.csv`. Đây là nhật ký chỉ ghi thêm.
- Không đổi feature, tầm dự báo hay quy tắc giao dịch mà không ghi vào mục 7 của `docs/methodology.md`.

# Hướng dẫn Nghiệm thu Thực tế & Smoke Test (Auto-Chat Agent)

Tài liệu này hướng dẫn cách thực hiện kiểm tra thực địa (smoke test) các thành phần phần cứng và môi trường của Auto-Chat Agent trên máy tính Windows.

---

## 1. Kiểm tra Môi trường Tự động (`autochat-smoke`)

Lệnh `autochat-smoke` cho phép kiểm tra nhanh toàn bộ các giao diện phần cứng và API cục bộ mà **hoàn toàn không làm ảnh hưởng đến dữ liệu đang chạy**:

```bash
uv run autochat-smoke all
```

Kết quả mẫu:
```json
{
  "detector": {
    "check": "detector",
    "status": "passed",
    "iterations": 100,
    "elapsed_seconds": 0.25,
    "microseconds_per_diff": 2500.0
  },
  "capture": {
    "check": "capture",
    "status": "passed",
    "width": 100,
    "height": 50,
    "channels": 4,
    "bytes_size": 20000,
    "non_zero_ratio": 0.99,
    "capture_latency_ms": 4.48
  },
  "clipboard": {
    "check": "clipboard",
    "status": "passed",
    "write_verified": true,
    "read_matched": true,
    "restored_cleanly": true
  },
  "providers": {
    "check": "providers",
    "status": "passed",
    "ollama_available": true,
    "syrin_pool_available": true
  }
}
```

---

## 2. Kiểm tra Chi tiết Từng Thành phần

### A. Chụp màn hình qua Win32 GDI BitBlt
Chụp thử một vùng tọa độ trên màn hình máy thật (đo độ trễ và tỷ lệ pixel thực):
```bash
uv run autochat-smoke capture --x 100 --y 100 --width 200 --height 100
```
- **Độ trễ đo được:** ~4ms.
- **Tương thích:** Các ứng dụng cửa sổ như Notepad, Discord, Zalo, Telegram, Trình duyệt và Game chế độ Borderless / Windowed.

### B. Kiểm tra Tốc độ Lọc Khung hình (`DirtyFrameDetector`)
Đo thời gian so sánh byte giữa các khung hình liên tiếp:
```bash
uv run autochat-smoke detector --iterations 100
```
- Khung hình tĩnh hoặc thay đổi dưới ngưỡng sẽ được bỏ qua trong thời gian cực ngắn (< 3ms cho 10.000 pixel), không gây sụt giảm FPS của game.

### C. Kiểm tra Bảo toàn Clipboard
Đảm bảo cơ chế sao chép - dán không làm mất dữ liệu clipboard của người dùng:
```bash
uv run autochat-smoke clipboard
```
- Hệ thống tự động: Lưu dữ liệu hiện tại $\to$ Ghi chuỗi thử nghiệm $\to$ Xác thực $\to$ Khôi phục lại dữ liệu gốc của bạn $\to$ Kiểm tra tính nguyên vẹn 100%.

### D. Kiểm tra Kết nối Local AI Providers
Kiểm tra tình trạng sẵn sàng của cụm AI cục bộ:
```bash
uv run autochat-smoke providers
```
- **Ollama:** `http://localhost:11434`
- **Syrin Pool:** `http://localhost:9100`

---

## 3. Chạy Vòng lặp Trực tiếp (`autochat-live`)

Chạy thử nghiệm một chu kỳ hoàn chỉnh giả lập:
```bash
uv run autochat-live --mock --once
```

Chạy giám sát liên tục $N$ bước với độ trễ tùy chỉnh:
```bash
uv run autochat-live --mock --max-steps 5 --interval 0.1
```

# Benchmark OCR — phạm vi bằng chứng

`ocr_vi_bench.py` được giữ từ gói thẩm định trước, không phải OCR engine sản phẩm.

## Đầu vào thật

Sau khi chọn app/game, thu ảnh một dòng có consent, tên ảnh và nhãn đúng trong `labels.tsv`:

```text
ten_anh.png<TAB>nội dung đúng có dấu
```

Tách dataset tune/test; ≥ 500 dòng/profile và ≥ 3 cỡ chữ. Cố định seed, engine/model hash, detector, preprocessing, máy và dependency.

Script dùng các package/model bên ngoài; review source/hash/license trước cài. Nó có thể tải weight. Không chạy mặc định trong bài test offline của gói này.

Kết quả synthetic trong audit chỉ minh họa failure mode. **Chưa có kết quả ảnh thật của app người dùng**, không dùng synthetic để mở L3/L4.

CER tổng không đủ: báo lỗi dấu, tên người nói/người nhận, số/giờ, latency và bộ transcript end-to-end. VietOCR recognizer dòng không tự giải bài toán detection/scroll attribution.
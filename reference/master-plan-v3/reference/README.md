# Tài liệu tham chiếu lịch sử

- `THAM_DINH_Auto-Chat-Agent_v2.4.md`: hồ sơ audit trước khi người dùng chốt ba quyết định. Số liệu synthetic/giá/model/link là thông tin lịch sử; không coi là baseline active.
- `decision_gate_jev_unverified.py`: phác thảo SDK từ audit, **chưa gọi API thật**. Không import trong app, không đưa thẳng vào production. SDK/model/response shape phải recheck.
- `traceability.json`: đối chiếu 50 errata với spec V3.

Bản chuẩn để triển khai nằm ở thư mục gốc. Không giữ HTML/config v2.4 như file active trong gói V3.
# Changelog — 2.4 → 3.0

## Outcome

Đổi bản “auto-chat mọi app/game, zero-ban” thành một kế hoạch có thể triển khai và kiểm chứng: **cá nhân trước, profile chọn sau, setting có ràng buộc an toàn**.

## Sửa theo ba câu trả lời

- Tách mốc dùng ổn cá nhân khỏi mốc công khai; bỏ yêu cầu beta 10–20 người trong lịch cá nhân.
- Bỏ danh sách app/game mặc định và câu hỏi top-3 bắt buộc; thêm mock/replay và wizard late-bound.
- Thêm spec setting: low-confidence, autonomy, consent, route/model, budget, privacy và persona.

## Áp dụng khuyến nghị thẩm định

- **A1–A6:** sửa OCR tiếng Việt, bỏ cam kết khử nhiễu/FPS chưa đo, ROI normalized + DPI, overlay defense-in-depth.
- **B1–B7:** Jev là decision gate, fan-out, rule cứng, eval/calibration tiếng Việt; model ID kiểm qua registry.
- **C1–C8:** provider/model có verification, token/thinking theo capability, budget/usage có ngày giá; không gọi context database là provider.
- **D1–D12:** bỏ input evasion; đúng phân biệt injected keyboard flag; hotkey có modifier, presence, permit, conversation binding, clipboard không phá dữ liệu.
- **E1–E4:** loại nguồn bị đánh dấu rủi ro khỏi active dependencies; SDK chính thức/minimal deps, pin/hash/license/SBOM.
- **F1–F8:** thống nhất metrics, autonomy và bảng nghiệm thu; không giữ số liệu tự nhận “đo thực tế”.
- **G1–G5:** schema đủ field, thêm cross-field/semantic validation; plaintext key và config nguy hiểm bị từ chối.

## Nâng cấp thêm khi chuyển thành spec

- Countdown không chèn text trước; permit draft hash/revision, một lần dùng và TTL.
- Ledger `pending/confirmed/unknown` để không gửi lại sau timeout.
- Không gán self chỉ bằng matching text; không mất tin lặp thật bằng hash bucket.
- Config trống an toàn, không bịa contact/name/app, ngân sách hoặc đồng ý cloud.
- Runtime qualification tách khỏi setting mong muốn; unit tests không chứng minh app Windows.
- Snapshot recheck có giới hạn race rõ; không hứa remote cancellation hay exactly-once.

## Trạng thái

“Đã sửa” ở đây nghĩa là **đã áp dụng trong tài liệu/config/code tham chiếu**. OCR/API/Windows/legal readiness vẫn là việc phải triển khai và thử; không tuyên bố các lỗi sản phẩm đã được chữa khi chưa có sản phẩm.

50 errata có đối chiếu vị trí mới ở `reference/traceability.json`.
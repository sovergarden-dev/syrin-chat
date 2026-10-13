# Visual QA — bản cuối

PDF 13 trang đã mở và kiểm tra từng trang. Rebuild cuối giữ nguyên pixel của cả 13 trang.

- PASS 01 — Cover, mục lục đúng số mục và footer không chồng nội dung.
- PASS 02 — Mục tiêu/đầu vào/phạm vi đọc rõ, dấu tiếng Việt đầy đủ.
- PASS 03 — Pipeline nằm trọn trong khung; heading và đoạn văn có khoảng thở.
- PASS 04 — Bảng module và wizard không tràn cột hoặc sát footer.
- PASS 05 — Field protocol dài wrap trong trang; OCR checklist đọc rõ.
- PASS 06 — Đoạn nguồn không bị tách thành từ đơn ở đầu trang; role Jev/LLM rõ.
- PASS 07 — Bảng L0–L4 đầy đủ; điều kiện quyền đọc/gửi không bị cắt.
- PASS 08 — State machine và 7 bước action nằm gọn; không overlap.
- PASS 09 — Bảng privacy và hàng G1 đủ nội dung, header không mồ côi.
- PASS 10 — Header gate lặp đúng; G2–G9 không bị tách hàng, trạng thái pending rõ.
- PASS 11 — Metric/cost formula đọc rõ; target chưa đo được đánh dấu.
- PASS 12 — Roadmap và mốc công khai riêng; chữ trong ô không tràn.
- PASS 13 — Phạm vi bằng chứng và phần chưa triển khai rõ; không trang trắng thừa.

HTML: đã xem toàn trang desktop 1280 px và mobile 390 px, cùng các crop top/gate/end. Đã sửa cột trạng thái quá hẹp; bản cuối không có tràn ngang toàn trang, overlap hay failed resource theo capture helper. Bảng rộng cuộn trong vùng riêng và có hướng dẫn trên mobile.

Tương phản chữ/đường link chính kiểm toán học ≥ 4.5:1. Dark palette kiểm tương phản, không ghi nhận như một dark-mode visual test. Không có ảnh trang trí hoặc ảnh tạo bằng AI trong bản Master Plan.

Đây là QA tài liệu; không chứng minh UI app Windows, OCR, provider API hoặc actuator.

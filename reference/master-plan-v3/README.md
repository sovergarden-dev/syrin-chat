# Auto-Chat Agent — bộ kế hoạch V3.0

**Cá nhân trước · App/game chọn sau · Setting có kiểm soát**

Đây là bộ đặc tả đã sửa, **không phải app đã xây xong**.

## Đọc theo thứ tự

1. `AUTO_CHAT_AGENT_MASTER_PLAN.md` — kế hoạch triển khai chuẩn.
2. `Nghiên cứu Auto-Chat Agent.html` hoặc `Auto-Chat-Agent-Master-Plan-V3.pdf` — bản đọc trực quan của Master Plan.
3. `SETTINGS_SPEC.md` — các lựa chọn autonomy/low-confidence/provider/privacy/budget.
4. `AUDIT_CHECKLIST.md` — gate cá nhân và gate trước công khai.
5. `DECISIONS_AND_ASSUMPTIONS.md`, `CHANGELOG.md` — quyết định, unknown và thay đổi.

## Bắt đầu an toàn

- `config.example.json`: profile rỗng, provider/route tắt, model ID chưa chọn, cloud chưa consent, ngân sách chưa đặt.
- `profile.template.json`: mẫu profile tắt; thay placeholder sau khi chọn app thật.
- `model_registry.example.json`: registry rỗng; phải verify API/model/capability trước enable.
- `profiles.schema.json`: kiểm cấu trúc. `scripts/validate_config.py`: thêm ràng buộc chéo/endpoint/registry.
- `policy_core.py`: logic tham chiếu offline; không đọc màn hình, gọi API hoặc gửi chat.
- `tests/`: mock/fixture, không phải Windows integration test.

## Tự kiểm tra

Python 3.12+; tạo venv riêng và review dependency trước cài:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
python -m pip install -r requirements-docs.txt
python scripts/validate_config.py config.example.json
python -m unittest discover -s tests -v
# Hoặc sinh lại báo cáo QA:
python scripts/run_checks.py
```

`python scripts/validate_config.py config.example.json --readiness` **phải báo chưa sẵn sàng** với config mẫu, vì chưa chọn app/model/consent. JSON hợp lệ không có nghĩa đã dùng được trên Windows.

Sinh lại bảng/schema/config/HTML:

```bash
python scripts/build_documents.py
# PDF tùy chọn, cần Chromium local:
python scripts/build_documents.py --pdf
```

Script build ghi lại file **mẫu**; không trỏ nó vào config cá nhân đang dùng. `project.json` là nguồn level/ngưỡng.

## Bằng chứng và giới hạn

Xem `qa/validation_summary.json` và `qa/test_results.txt` cho kết quả chạy trong sandbox. Những bài test này không chứng minh OCR, provider API, hotkey, clipboard hay actuator Windows.

`bench/` giữ công cụ OCR tham khảo, chưa chạy ảnh thật của app bạn. `reference/` là audit/phác thảo lịch sử, không baseline active; model/giá/link cần recheck.

Mốc cá nhân: ít nhất một profile thật, ≥ 14 ngày sử dụng có hoạt động, gate áp dụng đạt. Không yêu cầu mở L4 hoặc chốt ba game.

## Bản gói

Giữ nguyên tên sáu file lõi của gói cũ nhưng đã thay nội dung V3; thêm setting, quyết định, traceability và code kiểm thử. Không chứa API key, screenshot riêng tư hoặc dữ liệu hội thoại thật.

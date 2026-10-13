# Quyết định và giả định — V3

## Quyết định người dùng, không phải giả định

| ID | Quyết định | Hệ quả |
|---|---|---|
| D-01 | Cá nhân ổn trước, công khai sau | Nghiệm thu cá nhân và readiness công khai tách riêng |
| D-02 | Chưa chọn app/game | Profile late-bound; mock/replay sớm, app thực tế ở P1 |
| D-03 | Có setting | Autonomy, low-confidence, provider/privacy/budget có UI và schema |

## ADR đã chấp nhận cho baseline

- **ADR-001 — App-agnostic core, không universal guarantee.** Một protocol adapter, support record theo từng app/version/capability. Không hardcode Telegram/Discord/WoW làm app ưu tiên.
- **ADR-002 — Human control và earned autonomy.** App mới L0; L2 sau wizard. L3/L4 là setting mong muốn nhưng qualification có quyền cap.
- **ADR-003 — Zero-Evasion.** Không driver, scan-code jitter hoặc trick né anti-cheat. Nguồn/quyền chưa rõ không có hành động tự động.
- **ADR-004 — Jev quyết định, LLM sinh chữ.** Giữ hướng Jev + Gemini; model cụ thể chỉ chọn sau registry/smoke test/eval.
- **ADR-005 — Model/provider late-bound.** Không điền model “mới hơn” chưa chứng minh; không bắt buộc một broker dependency ở MVP.
- **ADR-006 — Countdown trước mutation.** Draft nằm trong trợ lý tới bước recheck/action; không xóa input người dùng để hủy countdown.
- **ADR-007 — Attempt ledger trước, sent ledger sau.** Unknown delivery chặn retry; không hứa exactly-once khi adapter không hỗ trợ.
- **ADR-008 — Local-first không đồng nghĩa zero leak.** Cloud opt-in; storage RAM mặc định; encryption không sẵn thì không persistent.
- **ADR-009 — Một nguồn ngưỡng.** `project.json` sinh config/schema/bảng; HTML/PDF từ Markdown đồng bộ.
- **ADR-010 — Công khai là quyết định sau.** Không xây multi-user backend, marketplace/plugin store hoặc beta tuyển người trong mốc cá nhân.

## Giả định cần kiểm chứng

| ID | Chưa biết | Cách kiểm | Khi cần | Nếu không đạt |
|---|---|---|---|---|
| A-01 | CPU/GPU/memory máy cá nhân | Thông tin máy + perf benchmark | P0/P1 | Giảm Hz/model footprint, giữ L2 |
| A-02 | App lúc test expose UIA/native ID | Spike app người dùng chọn | P1 | Nguồn khác được phép/OCR hoặc unsupported |
| A-03 | Người dùng có đồng ý cloud text | Consent UI theo provider | Trước cloud | Local-only/không generation cloud |
| A-04 | Ngân sách API | Người dùng nhập trần ngày/tháng | Trước cloud | Cloud tắt, không đặt ngân sách hộ |
| A-05 | Model ID và capability thực sự truy cập được | Official docs + API smoke test | Trước enable route | Không bật route |
| A-06 | Jev phù hợp tiếng Việt/teencode | Eval có nhãn, calibration | Trước decision automation/L4 | Rule/manual fallback, local classifier nếu được đánh giá |
| A-07 | OCR xử lý font/background app thật | Charset + bake-off ≥ 500 dòng | Trước support OCR | L2 có cảnh báo/không hỗ trợ profile |
| A-08 | ToS và protection của app | Review nguồn nền tảng, ngày/version | Trước L3/L4 | Cap L2 |
| A-09 | Input adapter ổn và phép dùng hợp lệ | Windows stress test + ToS | Trước L3/L4 | Không điền/gửi |
| A-10 | Persistent crypto package dùng được trên Windows | Install/license/failure test | Trước bật lưu transcript | RAM only |
| A-11 | Giá/provider data policy còn đúng | Giá/tier/effective date/điều khoản hiện hành | Trước cloud và khi thay đổi | Pause cloud/review lại |
| A-12 | Có muốn học giọng/lưu lịch sử | Người dùng opt-in | Sau MVP nếu cần | Giữ tắt |

Người triển khai sở hữu kiểm chứng kỹ thuật; chủ dự án quyết định nhu cầu/consent. Không dùng giả định để tự mở gate.

## Quy trình thay đổi

Thay đổi model/adapter/source/policy → cập nhật ADR và version → invalidate gate liên quan → replay/red-team → shadow → người dùng mở lại. Thay tone nhẹ không mặc định invalidate mọi gate, nhưng output guard/draft permit vẫn phải chạy lại.
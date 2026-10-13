# Đặc tả setting — V3

## Mục tiêu

Người dùng tùy chỉnh cách trợ lý hỗ trợ mà không phải sửa code. Setting không được biến một profile chưa rõ quyền/độ an toàn thành một profile được tự gửi.

## Quy tắc ưu tiên

`hard policy > quyền nền tảng/nguồn > qualification > profile override > global default`.

UI hiển thị song song **Mức bạn chọn** và **Mức hiện được phép**, kèm lý do. Không có nút “bỏ qua mọi cảnh báo”. Đổi setting khi có draft/countdown phải cancel bản đang chờ trước khi áp dụng.

## 1. Mức tự động hóa

| Setting | Mặc định | Phạm vi | Hiệu ứng |
|---|---|---|---|
| Profile bật/tắt | Tắt | Profile | App mới ở L0; không tự đọc khi chỉ phát hiện process |
| `requested_level` | L0 cho profile mới | Profile | L0/L1/L2/L3/L4; effective level bị policy cap |
| Default sau wizard | L2, người dùng xác nhận | Global | Chỉ là đề nghị của wizard; không thay consent |
| Countdown | 4 s; tối thiểu 3 s | Profile | Chỉ ở L4; chưa điền ô nhập trong lúc đếm |
| Presence required | Bật, không bypass | Global | Idle quá ngưỡng thì không autosend |
| Cancel on user input | Bật | Global | Input không phải duyệt/hủy hợp lệ hủy countdown |
| Recipient allowlist | Rỗng | Profile | Dùng stable ID + source binding, không chỉ display name |
| Quiet hours | Tắt đến khi người dùng chọn | Global/profile | Có timezone; pause autosend, gợi ý vẫn theo setting |

L3/L4 không được auto-resume sau startup. Muốn dùng lại phải có session arming và gate report còn hiệu lực. L4 trên API/bot chính thức vẫn theo phạm vi supervised của app này; bot unattended là sản phẩm/luồng riêng.

## 2. Độ tin cậy thấp

`on_low_confidence` áp dụng khi kết quả chưa đủ chắc nhưng không vi phạm hard rule.

| Giá trị | UI | Hành vi | Tự gửi? |
|---|---|---|---|
| `suggest_only` | “Chỉ gợi ý” | Hiện draft đã qua guard + nhãn cần xem lại | Không |
| `skip` | “Bỏ qua lượt này” | Không sinh/gửi thêm; ghi reason code | Không |
| `ask_confirmation` | “Yêu cầu xác nhận” | Người dùng xem/sửa; duyệt chỉ tiếp tục nếu hard gate vẫn đạt | Không gửi chỉ vì im lặng |
| `retry_stronger` | “Thử model mạnh hơn” | Tối đa một lần mặc định; dùng route được chọn/consent, còn budget | Chỉ nếu kết quả mới đủ chuẩn và các gate L4 vẫn đạt |

`on_timeout` và `on_error` mặc định `suggest_only`: nếu chưa có draft đủ guard thì hiện trạng thái lỗi, không bịa một gợi ý. Không tự dùng câu cũ đã hết revision.

Điểm model phải được hiệu chỉnh theo tiếng Việt/profile. UI giải thích điểm đó thuộc tín hiệu nào; không hiển thị “90% chắc chắn” từ một score chưa calibration.

**Không áp dụng setting để bypass:** source/recipient không rõ; PII/OTP; cam kết tài chính/quyết định; ToS/protection chưa rõ hoặc cấm; input không rõ; kill switch; permit hết hạn; kết quả gửi không rõ.

## 3. Provider, model và route

- Có official TypeSafe/Jev, official Gemini, custom compatible endpoint và local service.
- Mỗi provider: enable, `credential_ref`, endpoint nếu cần, data policy review, cloud consent, health/status.
- Mỗi route: enable, provider ID, model ID đã verify trong registry, output limit, thinking theo capability, timeout.
- Fast/complex/local route chọn độc lập. Đổi provider không tự chuyển transcript sang một bên chưa consent.
- `retry_stronger` chọn explicit fallback route; không âm thầm gọi “bất kỳ model nào rẻ”.
- Cấu hình mẫu provider tắt, `model_id: null`, registry rỗng. Tên candidate trong audit không là model đã được kích hoạt.
- Không nhập key vào chat hoặc JSON. UX dùng credential store của Windows; chỉ tham chiếu credential trong config.

Registry lưu provider/model ID, ngày verify, access scope, capability/params, context/output limit, giá/tier/effective date, data policy, smoke-test report và revision. Validator không thể tự chứng minh một record này là thật; runtime chỉ tin record đã được review.

## 4. Quyền riêng tư

| Setting | Mặc định | Điều kiện |
|---|---|---|
| Network/cloud | Tắt | Consent + provider policy + model registry + budget |
| Transcript persistent | Tắt; RAM | Mã hóa đã kiểm thử, retention và nút xóa |
| Screenshot runtime | Không lưu | Không có tùy chọn lưu luôn trong config vận hành |
| Diagnostic recorder | Tắt | Luồng riêng opt-in, thời hạn, mã hóa, dữ liệu kiểm thử không upload |
| Log nội dung/SDK debug | Tắt | Log vận hành chỉ metadata |
| Học giọng từ lịch sử | Tắt | Chỉ lịch sử có quyền sử dụng, có review/xóa |
| AI disclosure | Bật ở L4 | Tắt thì effective level ≤ L3 |

App nhạy cảm mặc định deny. Denylist process/title chỉ là defense-in-depth; quyền allowlist theo cửa sổ/profile vẫn bắt buộc.

## 5. Giới hạn và ngân sách

- User tự chọn trần USD/ngày và tháng; config mẫu để `null`, cloud chưa thể bật.
- Ratelimit cá nhân mặc định tối đa 3 tin/10 phút/hội thoại, 2 lượt agent liên tiếp, cách ≥ 15 s.
- Người dùng có thể chọn giới hạn chặt hơn. Thay đổi trần an toàn cần policy review/ADR, không chỉ kéo slider.
- Hết budget: pause cloud, báo trạng thái; local route chỉ dùng nếu đã thiết lập/consent và không thay đổi phạm vi dữ liệu.
- Countdown/hotkey/idle threshold chỉnh được trong miền hợp lệ. Hotkey có modifier và không trùng; đăng ký lỗi phải báo.

## 6. Nguồn, persona và ngoại lệ profile

- Chọn nguồn và thứ tự fallback theo capability; có review quyền đọc riêng, không tự đọc thêm log hay notification để “bù”. Quyền đọc chưa rõ/cấm thì L0; quyền gửi chưa rõ/cấm nhưng đọc được phép thì tối đa L2.
- ROI bằng client-normalized coordinate; calibration mất hiệu lực khi layout/DPI thay đổi.
- Self ID/name phải do người dùng xác nhận; không dùng tên mẫu của tác giả.
- Persona: xưng hô, tone, độ dài, ngôn ngữ; mặc định ngắn và không bịa.
- Game/protected profile không có phím “send workaround”. Khi chỉ L2, app chỉ hiển thị; người dùng tự thao tác app đích.

## 7. UX bắt buộc

Trạng thái rõ: Off / Reading / Suggesting / Needs review / Counting down / Cancelled / Delivery unknown / Budget paused. Mỗi fallback có reason code và câu giải thích ngắn.

Import config: validate trước, hiển thị diff, không nhập secret, không tự arm L3/L4. Config sai: dừng hành động, giữ bản last-known-good chỉ cho đọc/gợi ý khi còn consent; không silent ignore field lạ.

Đổi model/adapter/policy/contact binding: invalidation gate report phù hợp. Đổi draft: output guard lại, hash lại và cấp permit mới. Đóng app: hủy mọi pending action, không gửi ở nền lúc shutdown.
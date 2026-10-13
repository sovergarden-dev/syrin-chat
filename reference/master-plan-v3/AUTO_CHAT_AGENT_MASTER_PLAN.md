# Auto-Chat Agent — Master Plan V3

**Mã:** SPEC-AUTO-CHAT-V3 · **Phiên bản:** 3.0 · **Ngày:** 13/10/2026  
**Định vị:** Trợ lý chat AI đa ứng dụng trên Windows, ưu tiên dùng cá nhân.  
**Trạng thái:** Đặc tả đã sửa; chưa phải sản phẩm đã triển khai hoặc chứng nhận an toàn.

## 0. Quyết định đã chốt

1. Làm bản **dùng cá nhân ổn trước**. Chỉ cân nhắc công khai sau mốc nghiệm thu cá nhân và một quyết định phát hành riêng.
2. **Chưa chốt app/game.** Lõi, giao thức adapter và test harness không phụ thuộc tên app. Khi có prototype dùng được, thêm profile cho ứng dụng đang dùng lúc đó.
3. **Có setting** cho mức tự động hóa, xử lý độ tin cậy thấp, provider/model, persona, quyền riêng tư và ngân sách.

Không cần người dùng chọn ba app ngay. Nhưng không được đợi đến cuối mới kiểm thử: dùng mock/replay từ đầu, rồi kiểm thử tích hợp thực tế trước khi tuyên bố hỗ trợ một profile.

## 1. Mục tiêu · Đầu vào · Phạm vi · Đầu ra · Xong khi · Ràng buộc

### Mục tiêu

Giảm thao tác đọc và trả lời chat khi người dùng bận, vẫn giữ quyền kiểm soát. Hệ thống hiểu hội thoại tiếng Việt, đề xuất câu trả lời phù hợp và chỉ thao tác app khi người dùng đã cho phép, tích hợp đã được kiểm chứng.

### Đầu vào

- Windows 11, tài khoản và ứng dụng người dùng được quyền sử dụng.
- Profile chọn cửa sổ, nguồn đọc, vùng chat/ô nhập nếu cần OCR, danh tính của mình và contact/nhóm cho phép.
- Tin nhắn đọc được qua nguồn hợp lệ; persona và setting do người dùng chọn.
- Credential qua kho bí mật của Windows nếu dùng API; cloud chỉ bật sau consent và cấu hình ngân sách.
- Cấu hình máy, app thực tế và ngân sách: **chưa được cung cấp**, không tự đoán.

### Phạm vi

**MVP cá nhân:** thiết lập profile, đọc hội thoại, dựng transcript, Jev decision gate, LLM sinh câu, gợi ý L1/L2, hủy, telemetry tối thiểu và shadow mode.  
**Sau MVP:** OCR theo profile, L3 điền bản đã duyệt; L4 đếm ngược chỉ ở tích hợp đủ điều kiện.  
**Sau khi dùng ổn:** hardening và quyết định công khai. Không gộp phát hành rộng vào tiêu chí MVP.

### Đầu ra

- App desktop có màn hình trạng thái và lý do không gửi; bộ profile có thể thêm về sau.
- `MessageEvent`, `Draft`, `SendPermit` và sổ lần gửi có cấu trúc.
- Báo cáo đo kiểm theo từng profile, không phải một điểm số “universal” chung.
- Bộ cài cá nhân khi đủ điều kiện; tài liệu/quyền/SBOM phù hợp phạm vi phát hành.

### Xong khi

Người dùng sử dụng được trên ít nhất một ứng dụng thực tế được chọn về sau; ≥ 14 ngày sử dụng có hoạt động, không có sự cố nghiêm trọng chưa xử lý; các gate áp dụng cho tính năng được bật đều đạt. Nếu chỉ dùng L2 thì không phải mở L4 để coi là đạt mốc cá nhân.

### Ràng buộc

- Không hứa hỗ trợ mọi app/game, “zero-ban”, “zero-data-leak”, “100% chính xác” hoặc độ trễ chưa đo.
- Không né anti-cheat, không driver giả lập phần cứng, không micro-jitter để che dấu tự động hóa.
- Không spam/broadcast, không tự cam kết tiền/hẹn/quyết định, không tự trả lời khi không giám sát.
- Không mặc định đọc app mới, lưu ảnh thật hay gửi hội thoại lên cloud.
- Người dùng chọn **mức mong muốn**; mức thực thi còn bị giới hạn bởi quyền nền tảng và bằng chứng kiểm thử.

## 2. Nguyên tắc và yêu cầu sản phẩm

**Human-in-control:** app mới ở L0; sau wizard có thể dùng L1/L2. Không âm thầm bật lại L3/L4 sau restart, lỗi cấu hình hoặc thay đổi adapter/model quan trọng.

**Fail-closed:** không rõ người nói, hội thoại, target, trạng thái input hoặc kết quả gửi thì không gửi. UI phải cho biết lý do, không treo im lặng.

**Zero-Evasion:** chỉ dùng giao diện/API được phép. Suggest-only không tự động làm một nền tảng cấm bot trở thành nền tảng cho phép automation.

**Local-first:** mặc định network tắt, transcript ở RAM, log không có nội dung chat, học giọng tắt. Chỉ gửi text tối thiểu khi consent và chính sách provider đã được review.

**Measure-first:** mọi ngưỡng bên dưới là **tiêu chí đề xuất**, không phải kết quả đã đạt. Hỗ trợ được ghi theo app/version/source/autonomy, không theo tên app chung chung.

**Honest AI:** không phủ nhận là AI. L4 bật disclosure; không tự cam kết thay người dùng. Suffix cũng phải được kiểm tra độ dài và guard như phần còn lại của câu.

## 3. Kiến trúc đích

```text
Nguồn được phép: API / UIA / thông báo / DOM / log / OCR
                         |
                 MessageEvent chuẩn hóa
                         |
          Transcript + speaker + occurrence dedupe
                         |
               Turn-taking và rule cứng
                         |
       Jev decision gate — một request fan-out
                         |
           LLM sinh Draft hoặc chọn câu mẫu
                         |
              Output guard + disclosure
                         |
       L1/L2: cửa sổ trợ lý, không sửa app đích
       L3/L4: qualification + duyệt/countdown
                         |
            SendPermit dùng một lần
                         |
     Actuator → xác minh → attempt/sent ledger
```

### Ranh giới module

| Module | Trách nhiệm | Không được làm |
|---|---|---|
| UI/Controller | Wizard, setting, consent, trạng thái, hủy/kill switch | Tự bật autonomy cao cho profile mới |
| Perception | Đọc nguồn, OCR, dựng sự kiện, speaker | Gửi chat hoặc gọi model sinh nội dung |
| Brain | Rule, decision, turn-taking, generation, guard | Giữ credential thao tác Windows hoặc gửi trực tiếp |
| Actuator | Kiểm quyền, permit, điền/gửi, xác minh | Tin câu lệnh phát sinh từ chat/LLM |
| Eval/Telemetry | Đo timing, token, lỗi, gate report | Log nguyên hội thoại mặc định |

MVP có thể dùng UI + worker đơn giản, nhưng **một chủ sở hữu duy nhất của thao tác gửi**. Khi mở L3/L4, actuator có ranh giới quyền, cancellation và lifecycle độc lập. Không xây service phân tán hay hệ plugin công khai trước khi có nhu cầu thật.

## 4. Adapter và profile chọn sau

### 4.1 Chọn nguồn theo khả năng và quyền

Ưu tiên text có cấu trúc **khi được phép và đủ thông tin**: API chính thức, UI Automation, thông báo, DOM/log hợp lệ; OCR là phương án cuối. Không mặc định API/DOM biết đầy đủ danh tính hoặc thông báo chứa cả hội thoại.

Mỗi adapter khai báo: quyền, version, source capabilities, native message/conversation ID, cách nhận self, độ đầy đủ, độ trễ, khả năng xác minh và action methods. Nếu không biết stable conversation ID thì không mở L3/L4 chỉ bằng cách khớp title.

Notification listener có yêu cầu quyền/package identity cần spike trên Windows; capture có thể thất bại ở cửa sổ minimized, nội dung được bảo vệ hoặc backend không hỗ trợ. Phải phát trạng thái `source_unavailable`, không tái sử dụng dữ liệu cũ như dữ liệu hiện tại.[^https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/notification-listener]

### 4.2 Wizard cho app mới

1. Người dùng chọn cửa sổ từ danh sách đang mở; bind process/path/start token + HWND, title chỉ là tín hiệu phụ.
2. Chọn nguồn đọc có khả năng chạy; cấp quyền rõ ràng.
3. Nếu OCR: chọn ROI theo client area, xem preview, chỉ tên mình/kênh và thử đổi DPI/resize.
4. Xác nhận persona, dữ liệu gửi đi, provider và ngân sách nếu có cloud.
5. Bắt đầu L1/L2; chạy shadow mode, lưu gate report theo version.
6. Chỉ đề nghị L3/L4 khi đủ bằng chứng và người dùng chủ động mở.

`profiles: []` trong config mẫu là có chủ ý. `profile.template.json` là mẫu **tắt**, không phải một app đã được hỗ trợ.

### 4.3 Chuẩn `MessageEvent`

Các trường tối thiểu: `event_id`, `source_epoch`, `profile_id`, `conversation_id`, `conversation_revision`, `native_message_id?`, `occurrence_id`, `sender_id?`, `sender_display`, `speaker_state` (self/other/unknown), `speaker_evidence`, `text_nfc`, `observed_at_utc`, `observed_monotonic`, `capture_quality`, `source_complete`.

- Dùng native message ID nếu có. Không lấy hash text + bucket thời gian làm ID duy nhất: hai tin “ok” thật có thể giống nhau.
- Với OCR, tạo occurrence qua line track + scroll alignment + source epoch. Tắt/mở nguồn hoặc đổi kênh phải đổi epoch.
- Nội dung “[YOU]” hay tên mình **trong phần text** không phải bằng chứng người nói.
- Sent-ledger hỗ trợ đối chiếu; không tự gán self chỉ vì người khác copy đúng câu mình vừa gửi.
- Text lỗi/không hoàn chỉnh được đánh dấu; không âm thầm sửa tên, số tiền, OTP hoặc giờ hẹn.

## 5. OCR và dựng transcript

### Mục tiêu

Đọc được tiếng Việt có dấu trên nguồn được chọn, với chỉ số đo riêng cho profile. Không khóa engine bằng tên runtime.

### Thiết kế

- Ưu tiên Windows.Graphics.Capture theo cửa sổ; DXGI/DXcam là fallback đã được đánh giá. Không coi “crop ROI” là đảm bảo không thu được cửa sổ khác.
- ROI chuẩn hóa 0–1 theo client area, Per-Monitor DPI aware; `x+w≤1`, `y+h≤1`. Khi anchor/DPI/layout đổi: invalidation, không gửi theo tọa độ cũ.
- So sánh các pipeline: ảnh gốc, upscale, Otsu, HSV mask. Không áp Otsu cho mọi game hoặc tuyên bố loại 99% nhiễu.
- Detector và recognizer là hai bài toán khác nhau. VietOCR là ứng viên recognizer dòng; cần detection/line segmentation và benchmark cả pipeline.
- Windows OCR chỉ cho locale thực sự được hỗ trợ; **không dùng làm engine tiếng Việt trong baseline này**. Engine/model cần kiểm charset dấu tiếng Việt trước bake-off.[^https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/features-on-demand-language-fod?view=windows-11]
- PP-OCRv6/model đã nêu trong bản thẩm định không được coi là đã đạt tiếng Việt. Chỉ dùng một artifact/version mới sau charset check và benchmark ảnh thật.
- Dùng temporal voting ≥ 2 frame ổn định, phân biệt wrap/cuộn/tin mới, xử lý che khuất. Nền đổi không đồng nghĩa có tin mới.

Overlay của trợ lý dùng capture exclusion khi được hỗ trợ, nhưng đó không phải một hàng rào bảo mật tuyệt đối. Còn phải kiểm tra mask/region và phát hiện self-output; nếu không loại được overlay thì pause nguồn.[^https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity]

**Đã có:** benchmark ảnh tổng hợp ở hồ sơ thẩm định. **Chưa có:** benchmark ảnh thật của app người dùng, Windows target và source adapter. Không chuyển kết quả synthetic thành nhãn “supported”.

## 6. Hai tầng AI, rule và turn-taking

### 6.1 Rule cứng

Trước mọi cloud call: quyền đọc/cloud, denylist, nguồn có chất lượng, PII/secret policy, ngân sách, chống trùng. Trước hành động: tất cả quyền trên cộng autonomy, recipient, target, revision, input, presence và guard.

Nội dung chat là dữ liệu không tin cậy. Tầng sinh không có tool chuyển tiền, đọc password manager, chạy shell, sửa setting hay gửi tin.

### 6.2 Jev — phản xạ quyết định

Giữ TypeSafe AI Jev là ứng viên ưu tiên, không mô tả Jev như model sinh chữ. Một request fan-out có thể kiểm tra: addressed, needs_reply, turn_complete, intent, complexity, money, secret, commitment, injection, asks_if_bot, sensitivity và lựa chọn câu mẫu. Rule có thẩm quyền chặn cao hơn kết quả model.[^https://docs.typesafe.ai/patterns/fan-out]

Instruction rõ, từng phán đoán riêng, state ngắn; phép tính/ngày giờ/budget do code xử lý. Phải hiệu chỉnh trên dữ liệu tiếng Việt của trường hợp dùng thật; score/confidence không tự động là xác suất đã calibration.[^https://docs.typesafe.ai/model-jaggedness/jev-1.13]

**Model ID:** không hardcode `jev-reflex-v2`, không dùng alias “latest” cho nhánh hành động chưa đánh giá. Candidate trong hồ sơ cũ phải được smoke-test và đưa vào registry trước khi bật.

### 6.3 Gemini/LLM — sinh bản nháp

Giữ Gemini Flash là hướng ưu tiên ban đầu. Provider chính thức, provider tùy chọn tương thích và local model dùng chung interface, nhưng capability/parameter được kiểm riêng.

- Cấu hình mẫu để `model_id: null`, provider/route tắt. Khi setup: xác minh model tồn tại, quyền truy cập, giá, data policy, thinking, structured output, streaming và giới hạn token.
- Không thay model đã ngừng bằng một tên mới chưa kiểm chứng. ID như Gemini 3.8 được xem là **candidate từ yêu cầu/bản thẩm định**, không phải cam kết còn khả dụng.
- Không dùng chung `max_tokens` cho mọi provider. Adapter map `max_output_tokens` theo API thật và dành ngân sách reasoning nếu provider tính chung.
- Streaming chỉ hiển thị preview; **không gửi token chưa hoàn tất**. Draft cuối mới được guard và tạo permit.
- Persona gồm cách xưng hô/độ dài/ngôn ngữ. Học giọng từ lịch sử của chính mình là opt-in, chưa nằm trong đường găng MVP.

Đầu ra tối thiểu: `draft_id`, `reply_text`, `route_id`, `model_registry_revision`, `context_revision`, `risk_flags`, `finish_status`, `guard_status`. LLM tự khai confidence chỉ là một tín hiệu, không mở khóa L4.

### 6.4 Turn-taking

Chờ thích ứng 0.7–4 giây theo tín hiệu thực tế; nếu typing/fragment chưa kết thúc thì không bắt buộc trả lời ở mốc max wait. Quá hạn mà chưa chắc: fallback theo setting, không tự coi turn đã xong.

Có tin mới, đổi kênh, sửa tin nguồn hoặc người dùng can thiệp khi đang sinh/countdown: hủy draft cũ, tăng revision, gộp lại và quyết định lại. Có timeout/lỗi API: không dùng lại câu đã hết hiệu lực.

## 7. Setting và thang tự chủ

Đọc chi tiết ở `SETTINGS_SPEC.md`. Mức mong muốn là setting; mức thực thi là kết quả policy.

<!-- BEGIN:AUTONOMY -->
| Mức | Agent | Người dùng |
| --- | --- | --- |
| L0 — Tắt | Không đọc, không gọi model, không thao tác app. | Chủ động bật profile. |
| L1 — Chỉ đọc | Đọc/tóm tắt khi đã được cấp quyền; không tạo hành động gửi. | Tự trả lời. |
| L2 — Gợi ý | Hiện bản nháp ở cửa sổ trợ lý; không điền vào app đích. | Tự chọn, tự gõ/dán và gửi. |
| L3 — Điền bản nháp | Chỉ điền bản đã duyệt, sau kiểm tra an toàn. | Tự nhấn gửi trong app đích. |
| L4 — Tự gửi có đếm ngược | Chỉ gửi bản hoàn chỉnh sau đếm ngược, trong phạm vi đã mở khóa. | Có mặt, có thể hủy; chọn rõ contact/nhóm được phép. |
<!-- END:AUTONOMY -->

### Mở khóa

- L2: G1 nếu OCR; G2/G3 và nguồn đủ chất lượng. Trong giai đoạn thu thập có thể hiển thị cảnh báo chất lượng, nhưng không tuyên bố đã đạt.
- L3: nguồn/người nói được xác minh, G5/G6 phù hợp, ≥ 200 lượt L2 được review, chấp nhận không sửa ≥ 70%, action adapter được phép.
- L4: tất cả điều kiện L3 + decision calibration, disclosure, presence, recipient stable ID trong allowlist và ≥ 500 shadow trials/profile/contact, 0 would-have-misfired.
- Quyền **gửi** cấm/chưa rõ, protection present/unknown, danh tính/kênh không rõ: **tối đa L2**, không điền/gửi bằng phím, và chỉ khi nguồn đọc vẫn được phép.
- Quyền **đọc** cấm/chưa rõ hoặc nguồn không thuộc phạm vi được cấp: L0; consent của chủ máy không tự thay thế quyền nền tảng/người liên quan.
- App nhạy cảm không được cấp quyền: L0. Tắt disclosure không được giữ L4.

**Độ tin cậy thấp:** setting cho `suggest_only`, `skip`, `ask_confirmation`, `retry_stronger`. Retry có giới hạn, không tự mở khóa autosend. Hard block (PII/secret, app cấm, source/target không rõ, kill switch) không có setting bypass.

Mặc định recommend-only; không tự chọn contact, giờ yên lặng, budget hay tên tài khoản của người dùng.

## 8. State machine và thao tác an toàn

```text
OFF → OBSERVING → COLLECTING → DECIDING → GENERATING → GUARDED_DRAFT
                                          ├─ L2: SUGGESTED
                                          ├─ L3: AWAITING_APPROVAL → FILLING
                                          └─ L4: COUNTDOWN → PERMIT → SENDING
                                                     → VERIFYING → COOLDOWN
Hủy / mất nguồn / revision đổi / kill → CANCELLED hoặc OFF
Kết quả gửi không rõ → DELIVERY_UNKNOWN, không tự thử gửi lại
```

### Send pipeline

1. **Policy/qualification:** tính effective level, kiểm quyền, rate/cost budget, recipient, kết quả guard.
2. **Duyệt/countdown:** hiển thị trong trợ lý, **chưa sửa ô nhập app đích**. Mọi input người dùng khác hành động duyệt/hủy hợp lệ thì hủy countdown.
3. **Permit một lần:** ràng buộc target process/start token/HWND, conversation ID/revision, source epoch, user-input revision, profile-policy revision, draft hash và cancel generation. TTL tối đa 10 giây.
4. **Recheck sát thao tác:** actuator kiểm lại trước điền và trước gửi; input không rỗng/không xác định thì abort. Không giành foreground tự động.
5. **Thao tác:** L3 chỉ điền bản đã duyệt, người dùng tự gửi; L4 mới gọi send. Adapter ưu tiên stable native target. Clipboard fallback chỉ khi đã kiểm toàn bộ format/ownership và phục hồi an toàn.
6. **Xác minh:** ghi attempt `pending` **trước** thao tác; xác minh theo native ID hoặc self-message có bằng chứng. Timeout/crash → `unknown`, khóa retry của attempt đó.
7. **Ledger:** sau xác minh mới ghi `confirmed`/sent-ledger và cooldown. Không có cam kết exactly-once nếu nền tảng không cung cấp idempotency.

**Clipboard:** không xóa clipboard của người dùng. Đặt cờ loại khỏi history/cloud nếu hệ điều hành hỗ trợ; phục hồi chỉ khi sequence/ownership vẫn thuộc lần dán của app. Nếu người dùng đã copy thứ mới thì không ghi đè. Không khôi phục được format an toàn thì không dùng fallback.[^https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-formats]

**Kill switch:** dùng hotkey có modifier qua `RegisterHotKey`; nút UI dự phòng nếu đăng ký thất bại. Invalidate token trước, sau đó stop worker/cancel local request. Không thể thu hồi packet đã gửi hoặc tin đã đến server; không hứa “dừng mọi thứ trong 10 ms”.[^https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey]

**Giới hạn còn lại:** Windows không bảo đảm giao dịch atomic giữa kiểm foreground và input injection. Recheck, một actuator và stress test giảm rủi ro, không chứng minh zero-misfire. Nếu không đạt gate thì giữ L2.

## 9. Bảo mật, dữ liệu và quyền riêng tư

| Đối tượng | Mặc định | Khi bật thêm |
|---|---|---|
| Screenshot | Không lưu; chỉ ROI đang được cấp quyền | Diagnostic opt-in riêng, ngắn hạn, mã hóa, xóa tự động; không cloud |
| Transcript | RAM theo phiên | SQLCipher + khóa DPAPI sau kiểm thử; retention cấu hình, không fallback plaintext |
| API key | Không có trong JSON/log/zip | Windows Credential Manager; JSON chỉ chứa `credential_ref` |
| Cloud text | Tắt | Consent theo provider, text tối thiểu đã lọc; công bố chính sách provider |
| Model/local service | Không tự tải/chạy | Kiểm nguồn, hash, license, cổng loopback và tài nguyên |
| Telemetry | Cục bộ, không nội dung chat | Không analytics từ xa mặc định |
| Memory/persona học từ lịch sử | Tắt | Chỉ dữ liệu được quyền dùng, người dùng xem/xóa được |

Regex che CCCD/điện thoại/OTP chỉ là defense-in-depth, không bảo đảm tìm mọi PII. Có nghi ngờ thì không gửi cloud; che không thành công hoặc bộ lọc lỗi phải fail-closed. Paid tier không tự chứng minh “không training”; phải review điều khoản thực tế.

Không giữ log request/response SDK ở debug. Dữ liệu eval phải có consent riêng, pseudonymize và hạn lưu; không đánh đồng recorder kiểm thử với screenshot logging vận hành.

Chuỗi cung ứng: ưu tiên SDK chính thức; dependency tối thiểu, pin/hash, SBOM/license, review bản cập nhật. Không lấy repo giống tên làm repo chính chủ; không tải artifact từ nguồn đã bị đánh dấu rủi ro trong audit. Không cần LiteLLM ở MVP nếu direct SDK đáp ứng.

Model/adapter/profile/quyền thay đổi phải invalidate bằng chứng liên quan và yêu cầu đánh giá lại. Không có field JSON cho LLM tự chỉnh policy.

## 10. Nghiệm thu theo gate

<!-- BEGIN:GATES -->
| Gate | Tiêu chí đề xuất | Bằng chứng cần có | Trạng thái |
| --- | --- | --- | --- |
| G1 — OCR | CER NFC ≤ 10% cho L2; ≤ 3% (app) / ≤ 6% (game được phép) trước L3+; kiểm riêng tên/người nhận và ký tự quan trọng. | ≥ 500 dòng ảnh thật/profile, ≥ 3 cỡ chữ; tách tập hiệu chỉnh và tập kiểm thử. | Chưa đo |
| G2 — Transcript | Phát hiện tin mới: precision ≥ 99.5%, recall ≥ 98%; phát trùng ≤ 0.1%. | ≥ 2 giờ replay/profile; cuộn, wrap, đổi kênh, popup, lặp lại cùng một câu. | Chưa đo |
| G3 — Người nói | Precision đối phương trên tin kích hoạt trả lời ≥ 99.9%; self-loop quan sát = 0. | ≥ 1,000 tình huống có nhãn, gồm giả mạo tên và copy đúng nội dung tin của mình. | Chưa đo |
| G4 — Decision | F1 needs_reply/addressed ≥ 0.85; ECE ≤ 0.05 sau hiệu chỉnh; P95 decision mục tiêu ≤ 700 ms. | ≥ 1,000 tình huống tiếng Việt có nhãn; có dấu/không dấu/teencode; đo từ mạng dùng thật. | Chưa đo |
| G5 — Generation | Chấp nhận không sửa ≥ 70% trên ≥ 200 lượt L2 trước L3; 0 vi phạm quan sát trên ≥ 200 red-team. | Đánh giá thủ công; riêng cam kết, tiền, OTP, PII, sức khỏe/pháp lý và hỏi có phải AI. | Chưa đo |
| G6 — Action | Misfire quan sát = 0/10,000 test; hủy P99 mục tiêu ≤ 50 ms; xác minh sau gửi ≥ 99%; 0 retry mù. | Windows harness: Alt+Tab, đổi kênh, HWND/PID tái sử dụng, input chen ngang, timeout, crash. | Chưa đo |
| G7 — Tài nguyên | Mục tiêu ban đầu: CPU idle ≤ 3%; RAM core/UI ≤ 500 MB, báo riêng model worker; FPS giảm ≤ 2%. | Máy cá nhân tham chiếu và app/game thực tế được chọn sau; ghi cấu hình, baseline, n và khoảng dao động. | Chưa đo |
| G8 — Bảo mật | 0 key plaintext, 0 nội dung chat trong log vận hành; PII recall mục tiêu ≥ 95%, báo cả precision; dependency có nguồn/hash/license. | Bộ PII Việt Nam + quét build/log; thử lỗi mã hóa, lỗi credential store và cập nhật giả mạo. | Chưa đo |
| G9 — Quyền và tuân thủ | Cấp quyền theo profile; ma trận ToS có ngày review; công bố AI ở L4; không đọc/gửi vượt quyền. | Review từng tích hợp. Trước công khai: thêm review pháp lý, quyền dữ liệu, license và công bố quyền. | Chưa review |
<!-- END:GATES -->

Các ngưỡng là đề xuất để hiệu chỉnh bằng máy và nguồn thực tế. “0 lỗi quan sát” **không** bằng xác suất lỗi bằng 0; báo mẫu, phạm vi, version, failure cases và kết quả ngoài mẫu. Không lấy điểm trung bình tốt để bù một hard gate an toàn không đạt.

Hiện tại chỉ có kiểm thử offline của **cấu hình/policy tham chiếu** trong gói này. Không đánh dấu G1–G9 đạt bằng các bài unittest đó.

## 11. Độ trễ và chi phí

<!-- BEGIN:LATENCY -->
| Chỉ số | Định nghĩa | Target chưa đo |
| --- | --- | --- |
| T_detect — nguồn cấu trúc | Tin trở nên đọc được → MessageEvent ổn định. | P95 ≤ 300 ms |
| T_detect — OCR | Tin hiện trong ROI → MessageEvent ổn định. | P95 ≤ 1.2 s |
| T_suggest | Turn được chốt → bản nháp đầy đủ, đã qua guard. | P95 ≤ 2.5 s |
| T_send | Duyệt/hết countdown → xác minh thấy tin gửi. | P95 ≤ 1 s; đo riêng từng adapter |
| T_cancel | Nhận lệnh hủy → invalidation token và chặn hành động còn chờ. | P99 ≤ 50 ms |
<!-- END:LATENCY -->

**Tất cả target trên chưa đo.** Turn wait và countdown là thời gian chủ động, phải báo riêng. Đo P50/P95/P99, n, warm/cold start, mạng Việt Nam và cấu hình máy. Không cộng các P95 thành một P95 end-to-end.

Chi phí được tính từ usage thật:

```text
cost = Σ (input_tokens × input_price
        + output_and_reasoning_tokens × output_price
        + cache/tool/extra_charges) / đơn vị niêm yết
```

Bao gồm decision fan-out, retry, stronger-route, output guard và cache; không chỉ lần generation cuối. Giá có effective date/currency/tier. Ước tính cũ không dùng làm budget mặc định. Cloud chưa bật cho tới khi người dùng đặt trần ngày/tháng; hết trần thì dừng cloud call, không lén đổi provider. Đặt quota phía provider nếu có vì local estimator không kiểm soát được hóa đơn tuyệt đối.

## 12. Tech stack và lộ trình cá nhân

### Stack dự kiến, chưa khóa bằng benchmark

Python 3.12/3.13 tùy wheel Windows; PySide6 cho UI; WinRT/WGC/UIA wrapper được spike; OpenCV cho pipeline ảnh; detector + recognizer thắng bake-off; official SDK cho Jev/Gemini; SQLite metadata, SQLCipher khi lưu nội dung. C#/.NET chỉ xem xét cho Windows bridge nếu bằng chứng cho thấy cần; không rewrite toàn bộ trước khi có bản dùng được.

### Lộ trình ước lượng

| Phase | Khoảng tuần* | Đầu ra | Xong khi |
|---|---|---|---|
| P0 — Nền tảng kiểm chứng | 1–2 | Mock chat, replay, protocol, config/schema, cancel/policy tests, provider smoke test tùy consent | Có baseline tái lập; unknown rõ ràng; không cần chốt tên app |
| P1 — Prototype cá nhân L1/L2 | 3–6 | UI/wizard, một nguồn khả thi, decision/generation, guard, telemetry, shadow | Chọn app đang dùng tại thời điểm đó; tích hợp thực tế đọc/gợi ý được |
| P2 — Chất lượng nguồn | 7–9 | Transcript/speaker; OCR nếu app chọn cần; DPI/scroll/overlay/replay | Gate nguồn của profile đạt; có support record đúng phạm vi |
| P3 — Hành động nếu cần | 10–12 | L3; L4 chỉ nếu đủ điều kiện; permit, ledger, cancel/verify, red-team | G5/G6 và điều kiện autonomy; không bắt buộc L4 cho app cấm |
| P4 — Dùng ổn cá nhân | 13–16 | Sửa lỗi, recovery, data controls, build cá nhân, nhật ký dùng thực | ≥ 14 ngày hoạt động, gate áp dụng đạt, không sự cố nghiêm trọng mở |
| P5 — Cân nhắc công khai | Sau đó | Quyết định phát hành và checklist riêng | Chủ dự án đồng ý; legal/security/license/installer/support readiness đạt |

*Ước lượng lập kế hoạch, không cam kết tiến độ. P0/P1 có thể dùng structured source trước, OCR sau; nếu app chọn chỉ có OCR thì đổi thứ tự, không cố giữ lịch để bỏ qua kiểm thử. Nghiệm thu quan trọng hơn số tuần.

## 13. Công khai là một mốc riêng

Chỉ bắt đầu khi mốc cá nhân đạt và người dùng muốn phát hành. Bổ sung: ma trận hỗ trợ có version/giới hạn; rà soát quyền dữ liệu và quy định ở thị trường thực tế; license dependency/model; installer/updater có kiểm chữ ký; quyền screen/network/input rõ; vulnerability reporting, rollback và hỗ trợ sự cố.

Không dùng “cá nhân” làm miễn trừ ToS hay quyền riêng tư. Không tự suy ra kết luận pháp lý áp dụng toàn cầu từ một bài viết; review văn bản đang có hiệu lực trước phát hành. Nền tảng cấm self-bot phải được xem là cấm nhánh tự động hóa tài khoản cá nhân, không đổi tên thành “copilot” để vượt giới hạn.[^https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots]

## 14. Bộ bàn giao và việc còn phải chứng minh

**Đã sửa trong đặc tả:** định vị, kiến trúc, OCR, vai trò Jev/LLM, autonomy/setting, input safety, privacy, metrics/cost, roadmap, audit và config/schema. 50 mục errata được đối chiếu ở `reference/traceability.json`.

**Có thể kiểm thử offline:** config/schema, ràng buộc chéo, policy cap, permit, duplicate attempt và state invalidation trong code tham chiếu.

**Chưa triển khai/đo:** app Windows, OCR ảnh thật, Jev/Gemini API, WinRT/UIA, clipboard, actuator thực tế, runtime hotkey, code signing và compliance cho phát hành.

Một cấu hình hợp lệ không chứng minh app tích hợp hợp lệ. Không mở hành động thật từ kết quả unittest thuần Python.

## 15. Nguồn và cách cập nhật

Nguồn nền tảng: Microsoft Learn; TypeSafe docs; tài liệu model/API chính thức của provider; ToS từng app. `reference/THAM_DINH_Auto-Chat-Agent_v2.4.md` là hồ sơ audit lịch sử, **không phải baseline triển khai mới**; link/giá/model trong đó phải recheck khi build.

`project.json` là nguồn chung cho ngưỡng/level; config/schema và các bảng được sinh bởi `scripts/build_documents.py`. HTML/PDF sinh từ Markdown đã đồng bộ. Mọi sửa đổi kỹ thuật quan trọng có ADR và invalidate gate report liên quan.
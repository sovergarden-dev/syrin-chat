# P1 Profile Selection Gate

**Status:** intentionally blocked. No application or game has been selected. No profile is enabled.

P1 starts only when this record is completed for one concrete Windows application. The initial integration is L1/L2 only. It must not fill, paste, focus, send, or work around platform protections.

## Required selection record

| Evidence | Required value |
| --- | --- |
| Product | Exact app name, publisher, version, and target process path. |
| User authority | The user's permitted account and intended personal-use scope. |
| Platform policy | Current source URL, review date, automation status, and action cap. Unknown or prohibited means L2 maximum. |
| Read source | Official API, UI Automation, notification, DOM, log, or OCR. State why it is permitted and what identity/context it lacks. |
| Target binding | Process path, process start token, HWND strategy, stable conversation identity, and self-identity evidence. Title text alone is insufficient. |
| Privacy | Whether text may leave the machine, selected provider, reviewed provider policy, credential reference, daily/monthly budget, and retention decision. |
| Support limits | App/version/source/locale/window state/DPI boundaries. Unsupported conditions must emit `source_unavailable`, not reuse stale data. |

## L1/L2 evidence plan

1. Build fixtures from authorized test conversations or synthetic data. Keep source artifacts out of Git.
2. Verify source binding across resize, DPI 100/125/150/200%, reconnect, channel change, minimized state, and stale window handles.
3. Label at least the relevant transcript and speaker cases before evaluating a decision route.
4. Record latency, duplicate behavior, source loss behavior, and privacy controls in a profile-specific gate report.
5. Keep the integration in shadow/L2 mode until the V3 gates applicable to that profile are independently passed.

## Hard caps

- No active profile without explicit read consent and a reviewed source policy.
- Unknown speaker, recipient, source, identity, or context stays non-actionable.
- Protected, prohibited, or unclear automation status stays at L2 or lower.
- Model/provider setup requires a verified registry record, consent, provider review, and user-set budget. This P1 gate does not set them.
- L3/L4 are outside P1. The V3 evidence requirements remain binding.

## Owner decision needed

Choose the first application only when ready to supply the selection record. No app name is inferred from existing windows, process lists, or past conversations.

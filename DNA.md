## [v4.8.6] Scanner Stability & Flood-Shield - 2026-04-24 18:15 PHT
- **Scanner:** Implemented priority session selection (alphabetical seniority).
- **Rate-Limit:** Added `asyncio.sleep(1.5)` between lookups to prevent FloodWait.
- **Flood Shield:** Automatic catching of `FloodWaitError` with smart-retry.
- **Safety:** Skips accounts that return "Privacy Restricted" during lookup.

---
## [v4.8.5] Sentinel Filter Integration - 2026-04-24
- **Feature:** Deep validation for /add_list.
- **Logic:** GetFullUserRequest implementation for 7-day activity check.
- **Dedupe:** Cross-references Supabase 'message_campaign' before inserting.
- **Normalization:** Automatically handles @mentions and t.me links.

---
## [v4.8.5] Sentinel Filter Protocol
- **Validation:** 7-day Activity Check via GetFullUserRequest.
- **Input:** Supports @username, t.me/links, and plain text.
- **Filters:** Auto-skips Bots, Deleted Accounts, and Duplicates in Supabase.

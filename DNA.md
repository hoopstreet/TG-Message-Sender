## [v5.3.0] Sentinel Elite Protocol - 2026-04-24 19:45 PHT
- **Scheduler:** Implemented Toggle Logic. Clicking /schedule while ON kills active tasks; while OFF starts PHT time-picker.
- **Safety:** Hard 5-msg limit + multi-account deduplication.
- **Filters:** Verified active status (7 days), bot-blocking, and link/mention parsing.
- **Humanization:** Dynamic greeting injection for Bot Detection avoidance.

---
## [v5.2.0] Sentinel Final Protocol - 2026-04-24
- **Schema Mapping:** Fixed `bot_settings` (is_sending_active, current_promo_text) and `message_campaign`.
- **Safety:** Hard-cap of 5 msgs/acc. Anti-duplicate routing (multi-account safe).
- **Filtering:** Deep-scan for @usernames, links, and activity within 7 days.
- **Humanization:** Random Greeting Injection (Hi/Hello/Hey) + 3-6 min tactical delays.

---
## [v5.0.0] Sentinel Master Protocol - 2026-04-24 18:35 PHT
- **Engine:** Automated Account Switching (Routing) with 5-msg cap per account.
- **Safety:** Anti-Duplicate Global Lock (Prevent same user overlap).
- **Humanization:** Dynamic Greeting Injection (Hi/Hello/Hey) + Randomized Tactical Delays.
- **Scheduler:** Daily Cycle Auto-Resume logic + Global Pause Sync.
- **Audit:** Advanced /status with Daily/Total/Accounts/Schedule metrics.
- **Scanner:** Deep Filter (Active < 7 days, Bots, Deleted, Duplicates).

---
## [v5.0.0] Sentinel Master Protocol - 2026-04-24 18:35 PHT
- **Engine:** Automated Account Switching (Routing) with 5-msg cap per account.
- **Safety:** Anti-Duplicate Global Lock (Prevent same user/different account overlap).
- **Humanization:** Dynamic Greeting Injection (Hi/Hello/Hey) + Randomized Tactical Delays.
- **Scheduler:** Daily Cycle Auto-Resume logic + Global Pause Sync.
- **Audit:** Advanced /status with Daily/Total/Accounts/Schedule metrics.
- **Scanner:** Deep Filter (Active < 7 days, Bots, Deleted, Duplicates).

---
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

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

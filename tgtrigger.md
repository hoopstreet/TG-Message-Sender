# 👑 Tacloban HQ v2.3.0: Command Center Trigger Mapping

| Telegram Command | Supabase Column Name | Data Type | Purpose / Action |
| :--- | :--- | :--- | :--- |
| /start | (N/A) | (N/A) | Welcome Menu |
| /send_now | send_now | TEXT | Manual Blast Session |
| /schedule | schedule | TEXT | PHT Time (YYYY-MM-DD HH:MM) |
| /pause_send | status | TEXT | Manual Loop Kill-switch |
| /pause_sched | pause_sched | BOOLEAN | Auto-Task Kill-switch |
| /add_list | username | TEXT | Unique Lead Handle |
| /edit_msg | edit_msg | TEXT | Promo Script Content |
| /add_account | add_account | TEXT | Session Assignment |
| /status | updated_at | TIMESTAMPTZ | PHT Completion Audit |

## ✅ v2.6.0 Sync Confirmation
- All triggers confirmed mapping to `public.message_campaign`.
- Dual-Pause logic verified: `status` (manual) | `pause_sched` (auto).
- Latest push triggered at: 2026-04-24 PHT.
## ✅ v2.8.0 Mapping Verified: Outreach Engine connected to 'status' and 'send_now' columns.
## ✅ v2.8.5 SQL Audit: Updated 'updated_at' trigger for /status command.
## ✅ v2.9.0 Final Mapping: Verified all callback data matches Supabase schema.
## 🏆 v3.0.0 Milestone: Full System integration complete. Service Bridge Active.
## ✅ v3.1.0 UI Update: /start menu now matches professional BotFather style.
## ✅ v3.2.0 Bugfix: Removed duplicate /start handlers for single-response stability.

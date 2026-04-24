# TG Bot Commander Mapping
- /status: Pulls stats from `message_campaign` and `bot_settings`.
- /pause: Updates `bot_settings` (is_sending_active=false).
- /add_list: Filters & inserts into `message_campaign` (status='pending').
- /edit_msg: Updates `current_promo_text` in `bot_settings`.

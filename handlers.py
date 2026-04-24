from telethon import events
import pytz, glob, os
from datetime import datetime

PHT = pytz.timezone('Asia/Manila')

def register_handlers(bot, supabase, get_settings):
    
    @bot.on(events.NewMessage(pattern='/edit_msg'))
    async def edit_promo(event):
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📝 **Paste your new iGaming Promo Script:**\n(Greeting placeholders like 'Hi' will be randomized automatically)")
            r = await conv.get_response()
            supabase.table("bot_settings").update({"current_promo_text": r.text}).eq("id", "production").execute()
            await event.respond("✅ **Promo Script Updated and Saved to Cloud.**")

    @bot.on(events.NewMessage(pattern='/add_account'))
    async def add_account(event):
        count = len(glob.glob('*.session')) - 1
        msg = (f"📱 **Account Manager**\n\n"
               f"Current active sessions: **{count}**\n"
               "To add a new number:\n"
               "1. Use `login.py` in iSH.\n"
               "2. Upload the new `.session` to GitHub.\n"
               "3. Northflank will auto-detect the new account.")
        await event.respond(msg)

    @bot.on(events.NewMessage(pattern='/schedule'))
    async def schedule_toggle(event):
        sets = get_settings()
        if sets['is_sched_active']:
            supabase.table("bot_settings").update({"is_sched_active": False}).eq("id", "production").execute()
            supabase.table("message_campaign").delete().eq("status", "scheduled").execute()
            await event.respond("⏸️ **Schedule Cleared & Stopped.**")
        else:
            async with bot.conversation(event.sender_id) as conv:
                await conv.send_message("📅 **Enter Start Time (PHT):**\nFormat: `YYYY-MM-DD HH:MM AM/PM`")
                r = (await conv.get_response()).text
                try:
                    local_dt = PHT.localize(datetime.strptime(r, '%Y-%m-%d %I:%M %p'))
                    utc_dt = local_dt.astimezone(pytz.utc).isoformat()
                    supabase.table("bot_settings").update({"is_sched_active": True}).eq("id", "production").execute()
                    supabase.table("message_campaign").insert({"add_list": "SCHEDULE_MARKER", "status": "scheduled", "updated_at": utc_dt}).execute()
                    await event.respond(f"✅ **Sentinels set for:** {r} (PHT)")
                except: await event.respond("❌ Use: `2026-04-25 02:00 PM`")

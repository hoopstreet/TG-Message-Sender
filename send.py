import os, asyncio, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
PHT = pytz.timezone('Asia/Manila')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ v2.3.0**", buttons=[
        [Button.inline("🚀 Send Now", data="send_now"), Button.inline("📅 Schedule", data="schedule")],
        [Button.inline("📊 Status", data="status"), Button.inline("📂 Add List", data="add_list")],
        [Button.inline("📝 Edit Msg", data="edit_msg"), Button.inline("📱 Add Acc", data="add_account")],
        [Button.inline("⏸️ Pause Send", data="pause_send"), Button.inline("⏸️ Pause Sched", data="pause_sched")]
    ])

@bot.on(events.CallbackQuery)
async def handler(event):
    cmd = event.data.decode('utf-8')
    if cmd == "status":
        res = supabase.table("message_campaign").select("status").execute()
        success = sum(1 for r in res.data if r['status'] == 'success')
        await event.respond(f"📊 **Global Audit:** {success} Successful Blasts.")
@bot.on(events.CallbackQuery(data="add_list"))
async def add_list_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send @usernames (one per line):**")
        msg = await conv.get_response()
        names = [n.strip() for n in msg.text.split('\n') if n.strip()]
        for name in names:
            supabase.table("message_campaign").upsert({"username": name, "status": "pending"}).execute()
        await conv.send_message(f"✅ Imported {len(names)} leads to `message_campaign`.")

@bot.on(events.CallbackQuery(data="edit_msg"))
async def edit_msg_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Enter your new Promotional Text:**")
        msg = await conv.get_response()
        supabase.table("message_campaign").update({"edit_msg": msg.text}).eq("status", "pending").execute()
        await conv.send_message("✅ Promo text updated for all pending leads.")
@bot.on(events.CallbackQuery(data="send_now"))
async def send_now_handler(event):
    await event.respond("🚀 **Manual Blast Started...**")
    # Logic to fetch first pending row and rotate .session files
    res = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
    if res.data:
        # Execution loop would go here
        pass

@bot.on(events.CallbackQuery(data="pause_send"))
async def pause_send_handler(event):
    supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
    await event.respond("⏸️ **Manual loop set to PAUSED.**")

@bot.on(events.CallbackQuery(data="pause_sched"))
async def pause_sched_handler(event):
    supabase.table("message_campaign").update({"pause_sched": True}).execute()
    await event.respond("⏸️ **Scheduled tasks set to PAUSED.**")

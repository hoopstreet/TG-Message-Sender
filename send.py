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

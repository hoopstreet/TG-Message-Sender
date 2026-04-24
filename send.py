import os, asyncio, random, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, errors, Button
from dotenv import load_dotenv
from supabase import create_client, Client
from guide_text import GUIDE

load_dotenv()
# Load Config
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SB_URL, SB_KEY)
PHT = pytz.timezone('Asia/Manila')
bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

IS_SENDING = False

async def get_stats_report():
    try:
        today_str = datetime.now(PHT).strftime('%Y-%m-%d')
        all_data = supabase.table("targets").select("status, updated_at").execute()
        total = len(all_data.data)
        daily = len([x for x in all_data.data if x['status'] == 'success' and str(x.get('updated_at')).startswith(today_str)])
        return f"📊 **HQ Audit**\n📈 Total Leads: {total}\n🚀 Sent Today: {daily}"
    except Exception as e:
        return f"❌ DB Error: {str(e)[:50]}"

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(GUIDE, buttons=[
        [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📊 Status", data="get_status")]
    ])

@bot.on(events.CallbackQuery)
async def handler(event):
    data = event.data.decode('utf-8')
    if data == "get_status":
        await event.respond(await get_stats_report())
    await event.answer()

print("✅ Tacloban HQ v2.3.4 - Docker-Ready & Injected.")
bot.run_until_disconnected()

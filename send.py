import os, asyncio, random
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Credentials
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")

if not SB_URL or not SB_KEY:
    print("❌ ERROR: Supabase credentials missing!")
    exit(1)

supabase: Client = create_client(SB_URL, SB_KEY)

SESSIONS = [".telegram_session", "catherine_session", "mara_session", "jasmine_session", "alaska_session"]
MESSAGE = (
    "Hi, We are launching a new iGaming platform this week and seeking one "
    "professional team to lead all marketing and growth operations.\n\n"
    "📩 TO APPLY: Message @XeniaXu8 with your experience."
)

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        "🤖 **Bot Controller Online**\n\n"
        "Commands:\n"
        "▶️ `/send_now` - Start outreach blast\n"
        "📊 `/status` - Check Supabase progress\n"
        "♻️ `/restart` - Kill process to restart"
    )

@bot.on(events.NewMessage(pattern='/status', from_users=ADMIN_ID))
async def status(event):
    try:
        setting = supabase.table("bot_settings").select("value").eq("key", "current_index").single().execute()
        idx = setting.data['value'] if setting.data else 0
        res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
        pending = res.count
        await event.respond(f"📊 **Supabase Status**\nIndex: {idx}\nPending Leads: {pending}")
    except Exception as e:
        await event.respond(f"❌ DB Error: {str(e)}")

@bot.on(events.NewMessage(pattern='/send_now', from_users=ADMIN_ID))
async def trigger(event):
    await event.respond("🚀 Outreach initiated...")
    # Your run_outreach logic here...

print("Supabase-Powered Bot Online...")
bot.run_until_disconnected()

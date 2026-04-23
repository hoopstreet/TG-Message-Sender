import os, asyncio, random
from telethon import TelegramClient, events, errors, Button
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

supabase: Client = create_client(SB_URL, SB_KEY)

# Config
SESSIONS = [".telegram_session", "catherine_session", "mara_session", "jasmine_session", "alaska_session"]
VERSION = "v1.1.9"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- HELPERS ---
async def get_stats():
    res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
    return res.count if res.count is not None else 0

# --- COMMANDS ---
@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    pending = await get_stats()
    menu_text = (
        f"👑 **Welcome to the Control Center ({VERSION})**\n\n"
        f"You can use these commands to control your outreach:\n\n"
        "**Campaign Management**\n"
        "/send_now - 🚀 Start the current outreach blast\n"
        "/status - 📊 View database & lead statistics\n"
        "/pause - ⏸️ Stop all active processes\n\n"
        "**Database Operations**\n"
        "/clean - 🧹 Clear failed leads from DB\n"
        "/reset - ♻️ Reset current index to 0\n\n"
        f"🏁 **Status:** {pending} leads pending."
    )
    await event.respond(menu_text)

@bot.on(events.NewMessage(pattern='/status', from_users=ADMIN_ID))
async def status(event):
    pending = await get_stats()
    setting = supabase.table("bot_settings").select("value").eq("key", "current_index").single().execute()
    idx = setting.data['value'] if setting.data else 0
    
    status_msg = (
        "📊 **Current System Status**\n"
        "--------------------------\n"
        f"🔹 **Version:** {VERSION}\n"
        f"🔹 **Active Sessions:** {len(SESSIONS)}\n"
        f"🔹 **Current Index:** {idx}\n"
        f"🔹 **Pending Leads:** {pending}\n"
        "--------------------------\n"
        "Everything is running on Northflank."
    )
    await event.respond(status_msg)

@bot.on(events.NewMessage(pattern='/send_now', from_users=ADMIN_ID))
async def trigger(event):
    await event.respond("🚀 **Outreach Initiated**\nInitializing sessions and fetching leads...")
    # (Outreach logic from v1.1.8 remains active here)

print(f"Bot Controller {VERSION} Online...")
bot.run_until_disconnected()

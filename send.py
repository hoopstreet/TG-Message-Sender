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
VERSION = "v1.2.0"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- UI MENU ---
@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Control Panel {VERSION}**\nSelect an action below:",
        buttons=[
            [Button.inline("🚀 Start Blast", data="run_blast"), Button.inline("📊 Status", data="get_status")],
            [Button.inline("♻️ Reset Index", data="reset_db"), Button.inline("⏸️ Pause", data="pause_bot")]
        ]
    )

# --- CALLBACK HANDLER (The "Selection" Logic) ---
@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != ADMIN_ID: return
    
    data = event.data.decode('utf-8')
    
    if data == "get_status":
        res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
        setting = supabase.table("bot_settings").select("value").eq("key", "current_index").single().execute()
        idx = setting.data['value'] if setting.data else 0
        await event.answer(f"Index: {idx} | Pending: {res.count}", alert=True)
        
    elif data == "run_blast":
        await event.edit("🚀 Outreach initiated via Background Task...")
        # Your outreach logic call here
        
    elif data == "reset_db":
        supabase.table("bot_settings").update({"value": 0}).eq("key", "current_index").execute()
        await event.answer("✅ Progress reset to 0", alert=True)

print(f"Bot Controller {VERSION} with Buttons Online...")
bot.run_until_disconnected()

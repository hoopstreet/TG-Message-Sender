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

# --- LEAD INGESTION LOGIC ---
@bot.on(events.CallbackQuery(data=b"add_users"))
async def add_users_handler(event):
    USER_STATE[event.sender_id] = "waiting_list"
    await event.respond("📂 **Send me the list of @usernames (one per line or comma-separated):**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def list_input_handler(event):
    state = USER_STATE.get(event.sender_id)
    if state == "waiting_list" and not event.text.startswith('/'):
        # Clean the input: split by newline or comma, remove @ and spaces
        raw_list = event.text.replace(',', '\n').split('\n')
        cleaned_usernames = [u.strip().replace('@', '') for u in raw_list if u.strip()]
        
        if not cleaned_usernames:
            await event.respond("❌ No valid usernames found.")
            return

        # Prepare data for Supabase
        data_to_insert = [{"username": u, "status": "pending"} for u in cleaned_usernames]
        
        try:
            supabase.table("targets").insert(data_to_insert).execute()
            await event.respond(f"✅ **Success!** Added {len(cleaned_usernames)} leads to the queue.")
            USER_STATE.pop(event.sender_id)
        except Exception as e:
            await event.respond(f"❌ DB Error: {str(e)[:50]}")

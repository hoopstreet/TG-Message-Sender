import os, asyncio, random, glob, pytz, logging, re, base64
from datetime import datetime
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

# Mapping secrets
try:
    API_ID = int(os.getenv("TELEGRAM_API_ID"))
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    token = os.getenv("CONTROL_BOT_TOKEN")
    supabase = create_client(url, key)
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=token)
    print("🚀 Sentinel Online & Connected to Supabase")
except Exception as e:
    print(f"⚠️ Connection Setup Error: {e}")

def restore_sessions():
    try:
        res = supabase.table("saved_sessions").select("*").execute()
        for row in res.data:
            f_path = f"{row['phone_number']}.session"
            if not os.path.exists(f_path):
                with open(f_path, "wb") as f:
                    f.write(base64.b64decode(row['session_data']))
    except: pass

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel Elite v5.8.7**\nOnline and waiting for commands.")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
    leads = supabase.table("message_campaign").select("status").execute().data
    pending = sum(1 for x in leads if x['status'] == 'pending')
    await event.respond(f"📊 **Audit**\nPending: {pending}\nSched Active: {sets['is_sched_active']}")

if __name__ == '__main__':
    restore_sessions()
    bot.run_until_disconnected()

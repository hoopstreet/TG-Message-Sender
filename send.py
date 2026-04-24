import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = TelegramClient('bot', API_ID, API_HASH)

@bot.on(events.NewMessage)
async def debug_all(event):
    # This will print EVERY message the bot sees to Northflank logs
    print(f"📩 Log: Received [{event.text}] from {event.sender_id}")

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("✅ **Sentinel v6.1.1 Online**\nTriggers are active.")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    try:
        res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
        await event.respond(f"📊 **System Connected**\nMode: {'🟢' if res.data['is_sched_active'] else '🔴'}")
    except Exception as e:
        await event.respond(f"❌ Supabase Error: {e}")

async def main():
    print("🚀 BOOTING SYSTEM...")
    await bot.start(bot_token=BOT_TOKEN)
    print(f"✅ CONNECTED AS: @{(await bot.get_me()).username}")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

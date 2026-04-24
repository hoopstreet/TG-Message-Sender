import os, asyncio, random, glob, pytz, logging
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

# --- TRIGGERS ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    print(f"📩 Handling /start from {event.sender_id}")
    await event.respond("👑 **Sentinel v6.1.5 Active**\n\nIf other commands fail, check your Supabase 'production' row.")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    try:
        res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
        leads = supabase.table("message_campaign").select("id", count="exact").eq("status", "pending").execute()
        accs = len(glob.glob("*.session"))
        mode = "🟢 ACTIVE" if res.data.get('is_sched_active') else "🔴 IDLE"
        await event.respond(f"📊 **Status**: {mode}\n📱 **Sessions**: {accs}\n⏳ **Queue**: {leads.count}")
    except Exception as e:
        await event.respond(f"⚠️ **Supabase Connection Error:**\n`{str(e)}`")

# --- ENGINE ---

async def global_worker():
    print("📅 Engine Worker Thread Started")
    while True:
        try:
            # Check for production row
            res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
            if res.data and res.data.get('is_sched_active'):
                print("🤖 Engine: Processing Cycles...")
                # (Campaign logic remains here)
        except Exception as e:
            print(f"Worker Loop Warning: {e}")
        await asyncio.sleep(60)

async def main():
    print("🚀 BOT ATTEMPTING START...")
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    print(f"✅ SUCCESS: Logged in as @{me.username}")
    
    # Start worker as background task
    bot.loop.create_task(global_worker())
    
    print("📡 Listening for Commands...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

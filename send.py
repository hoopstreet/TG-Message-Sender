import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

# Credentials
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = TelegramClient('bot', API_ID, API_HASH)

async def global_worker():
    print("📅 Scheduler Watchdog Started...")
    while True:
        try:
            res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
            if not res.data.get('is_sched_active'):
                await asyncio.sleep(30); continue
            
            sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
            for s_file in sessions:
                s_name = s_file.replace(".session", "")
                today = datetime.now(PHT).strftime('%Y-%m-%d')
                
                count_res = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute()
                if count_res.count >= 5: continue 

                lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
                if not lead_req.data: break
                
                lead = lead_req.data[0]
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Good day"])
                    msg = res.data['current_promo_text'].replace("Hi,", f"{greet},")
                    await client.send_message(lead['add_list'], msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(300, 600))
        except Exception as e:
            print(f"Engine Error: {e}")
        await asyncio.sleep(30)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    print("📩 Received /start")
    await event.respond("👑 **Sentinel v6.1.1**\n\n/status | /schedule | /add_list")

@bot.on(events.NewMessage(pattern='/schedule'))
async def toggle_schedule(event):
    res = supabase.table("bot_settings").select("is_sched_active").eq("id", "production").single().execute()
    new_state = not res.data['is_sched_active']
    supabase.table("bot_settings").update({"is_sched_active": new_state}).eq("id", "production").execute()
    status_text = "🟢 ACTIVE" if new_state else "🔴 STOPPED"
    await event.respond(f"📅 **Schedule Mode:** {status_text}")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
    leads = supabase.table("message_campaign").select("id", count="exact").eq("status", "pending").execute()
    accs = len(glob.glob("*.session")) - 1
    mode = "🟢 ACTIVE" if res.data['is_sched_active'] else "🔴 IDLE"
    await event.respond(f"📊 **Status**: {mode}\n📱 **Accounts**: {accs}\n⏳ **Pending**: {leads.count}")

async def main():
    print("🚀 Starting Sentinel Bot...")
    await bot.start(bot_token=BOT_TOKEN)
    bot.loop.create_task(global_worker())
    print("✅ Bot is Online and Listening.")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

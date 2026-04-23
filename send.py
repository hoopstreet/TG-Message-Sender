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

supabase: Client = create_client(SB_URL, SB_KEY)

# Session files in your repo
SESSIONS = [".telegram_session", "catherine_session", "mara_session", "jasmine_session", "alaska_session"]
MESSAGE = (
    "Hi, We are launching a new iGaming platform this week and seeking one "
    "professional team to lead all marketing and growth operations.\n\n"
    "📩 TO APPLY: Message @XeniaXu8 with your experience."
)

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def run_outreach(event):
    # Fetch progress
    setting = supabase.table("bot_settings").select("value").eq("key", "current_index").single().execute()
    idx = setting.data['value'] if setting.data else 0
    
    # Fetch pending usernames
    res = supabase.table("targets").select("username").eq("status", "pending").order("id").execute()
    targets = [r['username'] for r in res.data]
    
    if not targets:
        await event.respond("✅ No pending targets found in Supabase.")
        return

    await event.respond(f"🚀 Outreach started at index {idx} with {len(targets)} leads.")

    for session in SESSIONS:
        try:
            async with TelegramClient(session, API_ID, API_HASH) as client:
                for username in targets:
                    try:
                        # Clean username
                        target = username.replace("@", "").strip()
                        await client.send_message(target, MESSAGE)
                        
                        # Update DB
                        supabase.table("targets").update({"status": "sent"}).eq("username", username).execute()
                        idx += 1
                        supabase.table("bot_settings").update({"value": idx}).eq("key", "current_index").execute()
                        
                        # Human-like delay
                        await asyncio.sleep(random.randint(120, 240))
                    except errors.PeerFloodError:
                        await event.respond(f"⚠️ {session} is limited (Flood). Switching...")
                        break
                    except Exception as e:
                        supabase.table("targets").update({"status": "failed"}).eq("username", username).execute()
                        continue
        except Exception as e:
            await event.respond(f"❌ Session {session} error: {str(e)}")

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond("🤖 **Bot Controller Online**\nCommands: /send_now, /status")

@bot.on(events.NewMessage(pattern='/status', from_users=ADMIN_ID))
async def status(event):
    res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
    await event.respond(f"📊 **Supabase Status**\nPending Leads: {res.count}")

@bot.on(events.NewMessage(pattern='/send_now', from_users=ADMIN_ID))
async def trigger(event):
    asyncio.create_task(run_outreach(event))

print("Supabase-Powered Bot Online...")
bot.run_until_disconnected()

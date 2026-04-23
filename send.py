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
VERSION = "v1.2.1"

# Outreach Config
SESSIONS = [".telegram_session", "catherine_session", "mara_session", "jasmine_session", "alaska_session"]
MESSAGE = (
    "Hi, We are launching a new iGaming platform this week and seeking one "
    "professional team to lead all marketing and growth operations.\n\n"
    "📩 TO APPLY: Message @XeniaXu8 with your experience."
)

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- OUTREACH ENGINE ---
async def run_outreach():
    res = supabase.table("targets").select("username").eq("status", "pending").order("id").execute()
    targets = [r['username'] for r in res.data]
    if not targets: return

    for session in SESSIONS:
        try:
            async with TelegramClient(session, API_ID, API_HASH) as client:
                for username in targets:
                    try:
                        target = username.replace("@", "").strip()
                        await client.send_message(target, MESSAGE)
                        supabase.table("targets").update({"status": "sent"}).eq("username", username).execute()
                        # Update index
                        setting = supabase.table("bot_settings").select("value").eq("key", "current_index").single().execute()
                        new_idx = (setting.data['value'] if setting.data else 0) + 1
                        supabase.table("bot_settings").update({"value": new_idx}).eq("key", "current_index").execute()
                        await asyncio.sleep(random.randint(120, 240))
                    except errors.PeerFloodError: break
                    except: continue
        except: continue

# --- UI HANDLERS ---
@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Control Panel {VERSION}**",
        buttons=[
            [Button.inline("🚀 Start Blast", data="run_blast"), Button.inline("📊 Status", data="get_status")],
            [Button.inline("♻️ Reset Index", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')
    
    if data == "get_status":
        res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
        await event.answer(f"Pending Leads: {res.count}", alert=True)
        
    elif data == "run_blast":
        await event.edit("🚀 **Outreach Running...**\nCheck logs for progress.")
        asyncio.create_task(run_outreach())
        
    elif data == "reset_db":
        supabase.table("bot_settings").update({"value": 0}).eq("key", "current_index").execute()
        await event.answer("✅ Progress reset to 0", alert=True)

print(f"Bot Controller {VERSION} fully linked and online...")
bot.run_until_disconnected()

import os, asyncio, random, glob
from datetime import datetime
import pytz
from telethon import TelegramClient, events, errors, Button
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SB_URL, SB_KEY)
VERSION = "v1.4.1"
PHT = pytz.timezone('Asia/Manila')

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
USER_STATE = {}

async def run_continuous_outreach(event):
    # Fetch Message & Schedule
    settings = supabase.table("bot_settings").select("*").execute()
    config = {item['key']: item['value'] for item in settings.data}
    
    message_text = config.get("active_message", "No message set.")
    sched_time = config.get("schedule_time") # Format: "HH:MM"

    if sched_time:
        await event.respond(f"⏳ **Schedule Active:** Waiting for {sched_time} PHT...")
        while True:
            now_pht = datetime.now(PHT).strftime("%H:%M")
            if now_pht == sched_time:
                break
            await asyncio.sleep(30) # Check every 30 seconds

    sessions = glob.glob("*.session")
    await event.respond(f"🚀 **Continuous Blast Started (PHT)**")

    while True:
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data:
            await event.respond("✅ **Queue Empty.**")
            break
        
        target = res.data[0]
        username = target['username']
        
        for sess_file in sessions:
            client_name = sess_file.replace('.session', '')
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({"status": "success", "sent_by": client_name}).eq("id", target['id']).execute()
                    await event.respond(f"✅ Success: @{username} via {client_name}")
                    break
            except errors.PeerFloodError:
                continue
            except Exception as e:
                supabase.table("targets").update({"status": f"err: {str(e)[:15]}"}).eq("id", target['id']).execute()
                break 

        await asyncio.sleep(random.randint(120, 300))

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **PHT Scheduled Control v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Start Blast", data="run_blast"), Button.inline("⏰ Set Schedule", data="set_sched")],
            [Button.inline("📝 Msg", data="edit_msg"), Button.inline("📂 Add Users", data="add_users")],
            [Button.inline("📊 Stats", data="get_status"), Button.inline("♻️ Reset", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')
    if data == "set_sched":
        USER_STATE[event.sender_id] = "waiting_time"
        await event.respond("⏰ **Enter PHT Time to start (24h format):**\ne.g., `14:30` for 2:30 PM")
    elif data == "run_blast":
        asyncio.create_task(run_continuous_outreach(event))
    elif data == "add_users":
        USER_STATE[event.sender_id] = "waiting_users"
        await event.respond("📂 **Send list:**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    state = USER_STATE.get(event.sender_id)
    if not state or event.text.startswith('/'): return

    if state == "waiting_time":
        supabase.table("bot_settings").upsert({"key": "schedule_time", "value": event.text.strip()}).execute()
        await event.respond(f"✅ **Schedule Set!** Bot will wait for {event.text} PHT.")
        USER_STATE.pop(event.sender_id)
    elif state == "waiting_users":
        users = [u.strip().replace('@','') for u in event.text.split('\n') if u.strip()]
        data = [{"username": u, "status": "pending"} for u in users]
        supabase.table("targets").insert(data).execute()
        await event.respond(f"✅ Added {len(data)} users.")
        USER_STATE.pop(event.sender_id)

print(f"Bot v{VERSION} PHT Ready...")
bot.run_until_disconnected()

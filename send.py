import os, asyncio, random, glob, pytz, re
from datetime import datetime
from telethon import TelegramClient, events, errors, Button
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
# Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SB_URL, SB_KEY)
VERSION = "2.3.0"
PHT = pytz.timezone('Asia/Manila')
bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

IS_SENDING, USER_STATE = False, {}

async def compact_queue():
    res = supabase.table("targets").select("id, username").eq("status", "pending").execute()
    to_delete = [row['id'] for row in res.data if not row['username'] or row['username'].strip() == ""]
    for i in to_delete: supabase.table("targets").delete().eq("id", i).execute()

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    if IS_SENDING: return
    IS_SENDING = True
    await compact_queue()
    if event: await event.respond(f"⚡ **{mode_name} Engine Active**")
    
    while IS_SENDING:
        msg = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
        text = msg.data['value'] if msg.data else "Hello!"
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data: break
        
        target = res.data[0]
        success = False
        for sess in glob.glob("*.session"):
            if "bot_control" in sess: continue
            name = sess.replace('.session', '')
            try:
                async with TelegramClient(name, API_ID, API_HASH) as client:
                    await client.send_message(target['username'], text)
                    supabase.table("targets").update({"status": "success", "sent_by": name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", target['id']).execute()
                    success = True
                    await asyncio.sleep(random.randint(150, 300))
                    break
            except Exception: continue
        if not success: await asyncio.sleep(900)
    IS_SENDING = False

async def scheduler_loop():
    while True:
        now = datetime.now(PHT).isoformat()
        res = supabase.table("schedules").select("*").eq("status", "waiting").lte("scheduled_for", now).execute()
        for task in res.data:
            supabase.table("schedules").update({"status": "completed"}).eq("id", task['id']).execute()
            asyncio.create_task(shared_outreach_logic(None, "Scheduled Blast"))
        await asyncio.sleep(60)

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond("👑 **Tacloban HQ v2.3.0**", buttons=[
        [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📅 Schedule", data="set_sched")],
        [Button.inline("📊 Status", data="get_status"), Button.inline("⏸️ Stop", data="stop")],
        [Button.inline("📱 Add Acc", data="add_acc"), Button.inline("📝 Edit Msg", data="edit_msg")]
    ])

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.data == b"run_now": asyncio.create_task(shared_outreach_logic(event, "Manual"))
    elif event.data == b"set_sched":
        USER_STATE[event.sender_id] = "waiting_sched"
        await event.respond("📅 **Enter PHT Time:** `YYYY-MM-DD HH:MM`")
    elif event.data == b"stop":
        global IS_SENDING
        IS_SENDING = False
        await event.respond("🛑 Engine Stopping...")

# Start Scheduler
loop = asyncio.get_event_loop()
loop.create_task(scheduler_loop())
bot.run_until_disconnected()

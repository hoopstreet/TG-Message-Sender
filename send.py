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
VERSION = "v1.6.0"
PHT = pytz.timezone('Asia/Manila')

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Control Flags
IS_SENDING = False
USER_STATE = {}

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    IS_SENDING = True
    
    msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
    message_text = msg_data.data['value'] if msg_data.data else "No message set."
    
    await event.respond(f"✨ **{mode_name} Triggered**\nScanning queue...")

    while IS_SENDING:
        sessions = glob.glob("*.session")
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        
        if not res.data:
            await event.respond("✅ **Queue Finished.**")
            IS_SENDING = False
            break
        
        target = res.data[0]
        username = target['username']
        success = False

        for sess_file in sessions:
            if not IS_SENDING: break
            client_name = sess_file.replace('.session', '')
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({"status": "success", "sent_by": client_name}).eq("id", target['id']).execute()
                    await event.respond(f"✅ @{username} | via {client_name}")
                    success = True
                    await asyncio.sleep(random.randint(150, 300))
                    break 
            except errors.FloodWaitError: continue
            except Exception: continue

        if not success and IS_SENDING:
            await asyncio.sleep(600)

async def schedule_watcher(event, target_dt):
    await event.respond(f"📅 **Scheduled for:** {target_dt.strftime('%Y-%m-%d %H:%M')} PHT\nStanding by...")
    while True:
        now_pht = datetime.now(PHT)
        if now_pht >= target_dt:
            await shared_outreach_logic(event, "Scheduled Blast")
            break
        await asyncio.sleep(30)

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Dual-Trigger Control v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), Button.inline("⏸️ Pause Now", data="stop")],
            [Button.inline("📅 Schedule", data="set_sched"), Button.inline("⏸️ Pause Sched", data="stop")],
            [Button.inline("📊 Stats", data="get_status"), Button.inline("♻️ Reset", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    global IS_SENDING
    data = event.data.decode('utf-8')
    if data == "run_now":
        asyncio.create_task(shared_outreach_logic(event, "Send Now"))
    elif data == "set_sched":
        USER_STATE[event.sender_id] = "waiting_full_time"
        await event.respond("🗓️ **Enter Date & Time (PHT):**\nFormat: `YYYY-MM-DD HH:MM`\nExample: `2026-04-25 10:30`")
    elif data == "stop":
        IS_SENDING = False
        await event.edit("⏸️ **All Operations Paused.**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    if event.text.startswith('/'): return
    if USER_STATE.get(event.sender_id) == "waiting_full_time":
        try:
            dt = datetime.strptime(event.text.strip(), '%Y-%m-%d %H:%M')
            dt_pht = PHT.localize(dt)
            asyncio.create_task(schedule_watcher(event, dt_pht))
            USER_STATE.pop(event.sender_id)
        except:
            await event.respond("❌ **Invalid format.** Use: `YYYY-MM-DD HH:MM`")

print(f"Dual-Mode Engine v{VERSION} Online...")
bot.run_until_disconnected()

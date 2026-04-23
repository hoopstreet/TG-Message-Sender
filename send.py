import os, asyncio, random, glob, pytz
from datetime import datetime, timedelta
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
VERSION = "v1.6.1"
PHT = pytz.timezone('Asia/Manila')

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
IS_SENDING = False
USER_STATE = {}

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    IS_SENDING = True
    
    msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
    message_text = msg_data.data['value'] if msg_data.data else "No message set."
    
    await event.respond(f"⚡ **Daily Blast Initiated** ({mode_name})")

    while IS_SENDING:
        sessions = glob.glob("*.session")
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        
        if not res.data:
            await event.respond("✅ **All pending leads finished for today.**")
            break # Exit loop to reschedule for tomorrow
        
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
            await event.respond("🕒 **All accounts limited.** Cooling down for 15 mins...")
            await asyncio.sleep(900)

    # When loop breaks (Queue empty or Pause), if still in "Daily Mode", we stop the task here
    IS_SENDING = False

async def daily_scheduler(event, target_time_str):
    """Loop that triggers every day at the same time"""
    await event.respond(f"📅 **Daily Schedule Set:** {target_time_str} PHT\nBot will trigger every 24h.")
    
    while True:
        now_pht = datetime.now(PHT)
        # Parse user input (HH:MM) and apply to today
        target_h, target_m = map(int, target_time_str.split(':'))
        target_today = now_pht.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        
        # If time passed today, set for tomorrow
        if now_pht > target_today:
            target_trigger = target_today + timedelta(days=1)
        else:
            target_trigger = target_today

        wait_seconds = (target_trigger - now_pht).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        # Wake up and send!
        await shared_outreach_logic(event, "Daily Auto-Trigger")
        await event.respond(f"😴 **Daily task done.** Sleeping until tomorrow {target_time_str} PHT.")

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Daily Auto-Relay v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📅 Daily Sched", data="set_daily")],
            [Button.inline("⏸️ Stop/Pause", data="stop"), Button.inline("📊 Stats", data="get_status")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    global IS_SENDING
    data = event.data.decode('utf-8')
    if data == "run_now":
        asyncio.create_task(shared_outreach_logic(event, "Manual Start"))
    elif data == "set_daily":
        USER_STATE[event.sender_id] = "waiting_daily_time"
        await event.respond("⏰ **Enter Daily Time (PHT):**\nExample: `09:30` (24h format)")
    elif data == "stop":
        IS_SENDING = False
        await event.edit("⏸️ **Paused.** Daily cycles suspended.")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    if event.text.startswith('/'): return
    if USER_STATE.get(event.sender_id) == "waiting_daily_time":
        time_str = event.text.strip()
        try:
            asyncio.create_task(daily_scheduler(event, time_str))
            USER_STATE.pop(event.sender_id)
        except:
            await event.respond("❌ Use `HH:MM` format (e.g. 14:00)")

print("Daily Engine Online...")
bot.run_until_disconnected()

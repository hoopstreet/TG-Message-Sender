import os, asyncio, random, glob, pytz, re
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
VERSION = "v1.8.0"
PHT = pytz.timezone('Asia/Manila')

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
IS_SENDING = False
USER_STATE = {}

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    IS_SENDING = True
    await event.respond(f"⚡ **Blast Engine Active** ({mode_name})")

    while IS_SENDING:
        # REAL-TIME PICKUP: Always fetch latest message before sending
        msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
        message_text = msg_data.data['value'] if msg_data.data else "Default: Hello!"

        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data:
            await event.respond("✅ **Queue Finished.**")
            break
        
        target = res.data[0]
        username = target['username']
        success = False

        for sess_file in glob.glob("*.session"):
            if not IS_SENDING: break
            client_name = sess_file.replace('.session', '')
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({"status": "success", "sent_by": client_name}).eq("id", target['id']).execute()
                    await event.respond(f"✅ @{username} | Sent latest version")
                    success = True
                    await asyncio.sleep(random.randint(150, 300))
                    break 
            except errors.FloodWaitError: continue
            except Exception: continue

        if not success and IS_SENDING:
            await asyncio.sleep(900)
    IS_SENDING = False

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Dynamic Content Engine v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📝 Edit Msg", data="edit_msg")],
            [Button.inline("📂 Add Users", data="add_users"), Button.inline("⏸️ Stop", data="stop")],
            [Button.inline("📊 Stats", data="get_status")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    global IS_SENDING
    data = event.data.decode('utf-8')
    if data == "edit_msg":
        USER_STATE[event.sender_id] = "waiting_new_msg"
        await event.respond("📝 **Send your new message text:**\n(Supports emojis and multiple lines)")
    elif data == "run_now":
        asyncio.create_task(shared_outreach_logic(event, "Manual"))
    elif data == "stop":
        IS_SENDING = False
        await event.edit("⏸️ **Paused.**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    if event.text.startswith('/'): return
    
    if USER_STATE.get(event.sender_id) == "waiting_new_msg":
        new_text = event.text
        supabase.table("bot_settings").upsert({"key": "active_message", "value": new_text}).execute()
        await event.respond(f"✅ **Message Updated!**\nNew content will be picked up on the next send.")
        USER_STATE.pop(event.sender_id)

print(f"Dynamic Engine v{VERSION} Online...")
bot.run_until_disconnected()

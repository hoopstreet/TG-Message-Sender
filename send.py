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
VERSION = "v1.7.0"
PHT = pytz.timezone('Asia/Manila')

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
IS_SENDING = False
USER_STATE = {}

def parse_usernames(text):
    """
    Captures:
    1. @username
    2. username (raw)
    3. https://t.me/username
    """
    # Pattern looks for t.me links, @ symbols, or raw alphanumeric strings
    raw_list = re.findall(r'(?:https?://t\.me/|@|^|[\n])([a-zA-Z0-9_]{5,32})', text)
    # Clean and remove empty strings
    return list(set([u.strip() for u in raw_list if u.strip()]))

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    IS_SENDING = True
    msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
    message_text = msg_data.data['value'] if msg_data.data else "No message set."
    
    await event.respond(f"⚡ **Blast Active** ({mode_name})")

    while IS_SENDING:
        sessions = glob.glob("*.session")
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        
        if not res.data:
            await event.respond("✅ **Queue Empty.**")
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
            await asyncio.sleep(900)
    IS_SENDING = False

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Smart Lead Engine v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📂 Add Users", data="add_users")],
            [Button.inline("📅 Daily Sched", data="set_daily"), Button.inline("⏸️ Stop", data="stop")],
            [Button.inline("📊 Stats", data="get_status")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    global IS_SENDING
    data = event.data.decode('utf-8')
    if data == "add_users":
        USER_STATE[event.sender_id] = "waiting_bulk_users"
        await event.respond("📥 **Paste your list:**\nSupports `@user`, `t.me/user`, or raw names.")
    elif data == "run_now":
        asyncio.create_task(shared_outreach_logic(event, "Manual"))
    elif data == "stop":
        IS_SENDING = False
        await event.edit("⏸️ **Paused.**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    if event.text.startswith('/'): return
    
    if USER_STATE.get(event.sender_id) == "waiting_bulk_users":
        new_names = parse_usernames(event.text)
        
        # 1. Get existing usernames from DB to prevent duplicates
        existing = supabase.table("targets").select("username").execute()
        existing_list = [row['username'] for row in existing.data]
        
        # 2. Filter out duplicates
        to_add = [name for name in new_names if name not in existing_list]
        
        if to_add:
            payload = [{"username": name, "status": "pending"} for name in to_add]
            supabase.table("targets").insert(payload).execute()
            await event.respond(f"✅ **Success!**\nAdded: {len(to_add)}\nDuplicates Ignored: {len(new_names) - len(to_add)}")
        else:
            await event.respond("⚠️ All usernames provided already exist in the database.")
        
        USER_STATE.pop(event.sender_id)

print("Smart Engine Online...")
bot.run_until_disconnected()

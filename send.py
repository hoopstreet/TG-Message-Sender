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
VERSION = "v1.3.0"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- STATE MANAGEMENT ---
USER_STATE = {} # Temporary storage for conversation flow

# --- UI HANDLERS ---
@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"🛠️ **Advanced Control Panel {VERSION}**",
        buttons=[
            [Button.inline("🚀 Start Blast", data="run_blast"), Button.inline("📊 Stats", data="get_status")],
            [Button.inline("📝 Edit Message", data="edit_msg"), Button.inline("📂 Add Usernames", data="add_users")],
            [Button.inline("📱 Add Account", data="add_acc"), Button.inline("⏰ Schedule", data="set_sched")],
            [Button.inline("♻️ Reset Progress", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')
    
    if data == "get_status":
        res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
        await event.answer(f"Pending Leads: {res.count}", alert=True)

    elif data == "edit_msg":
        USER_STATE[event.sender_id] = "waiting_msg"
        await event.respond("📩 **Send the new outreach message text now:**")

    elif data == "add_users":
        USER_STATE[event.sender_id] = "waiting_users"
        await event.respond("📝 **Send the list of usernames (one per line or comma-separated):**")

    elif data == "add_acc":
        await event.respond("🔑 To add a new account, upload the `.session` file to the GitHub repo and add the filename to the `SESSIONS` list in `send.py`.")

    elif data == "run_blast":
        await event.edit("🚀 **Outreach started in background...**")
        # Existing run_outreach logic...

# --- INPUT HANDLER (For Editing/Adding) ---
@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    state = USER_STATE.get(event.sender_id)
    if not state or event.text.startswith('/'): return

    if state == "waiting_msg":
        supabase.table("bot_settings").upsert({"key": "active_message", "value": event.text}).execute()
        await event.respond(f"✅ **Message updated!**\nNew text:\n`{event.text}`")
        USER_STATE.pop(event.sender_id)

    elif state == "waiting_users":
        raw_list = event.text.replace(',', '\n').split('\n')
        clean_list = [{"username": u.strip().replace('@',''), "status": "pending"} for u in raw_list if u.strip()]
        supabase.table("targets").insert(clean_list).execute()
        await event.respond(f"✅ **Added {len(clean_list)} leads to Supabase!**")
        USER_STATE.pop(event.sender_id)

print(f"Bot v{VERSION} Operational...")
bot.run_until_disconnected()

import os, asyncio, random, glob, pytz, re
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
VERSION = "v1.9.1"
PHT = pytz.timezone('Asia/Manila')

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
IS_SENDING = False
USER_STATE = {}
TEMP_CLIENTS = {}

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    IS_SENDING = True
    await event.respond(f"⚡ **Engine Active** ({mode_name})")
    while IS_SENDING:
        msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
        message_text = msg_data.data['value'] if msg_data.data else "Hello!"
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data:
            await event.respond("✅ **Queue Empty.**")
            break
        target = res.data[0]
        username = target['username']
        success = False
        for sess_file in glob.glob("*.session"):
            if not IS_SENDING or "bot_control" in sess_file: continue
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
        if not success and IS_SENDING: await asyncio.sleep(900)
    IS_SENDING = False

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Account Manager v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📱 Add Acc", data="add_acc")],
            [Button.inline("📂 Add Users", data="add_users"), Button.inline("📝 Edit Msg", data="edit_msg")],
            [Button.inline("📊 Stats", data="get_status"), Button.inline("⏸️ Stop", data="stop")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.data == b"add_acc":
        USER_STATE[event.sender_id] = "waiting_phone"
        await event.respond("📱 **Enter Phone Number:**\n(e.g., +639123456789)")
    elif event.data == b"run_now":
        asyncio.create_task(shared_outreach_logic(event, "Manual"))
    elif event.data == b"stop":
        global IS_SENDING
        IS_SENDING = False
        await event.edit("⏸️ **Paused.**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_login(event):
    state = USER_STATE.get(event.sender_id)
    if not state or event.text.startswith('/'): return

    if state == "waiting_phone":
        phone = event.text.strip()
        client = TelegramClient(f"sess_{phone.replace('+', '')}", API_ID, API_HASH)
        await client.connect()
        try:
            hash = await client.send_code_request(phone)
            TEMP_CLIENTS[event.sender_id] = {"client": client, "phone": phone, "hash": hash.phone_code_hash}
            USER_STATE[event.sender_id] = "waiting_otp"
            await event.respond(f"📩 **OTP Sent to {phone}.** Enter the code:")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")

    elif state == "waiting_otp":
        otp = event.text.strip()
        data = TEMP_CLIENTS.get(event.sender_id)
        try:
            await data["client"].sign_in(data["phone"], otp, phone_code_hash=data["hash"])
            await event.respond(f"✅ **Success!** Account {data['phone']} is active.")
            USER_STATE.pop(event.sender_id)
            TEMP_CLIENTS.pop(event.sender_id)
        except errors.SessionPasswordNeededError:
            USER_STATE[event.sender_id] = "waiting_password"
            await event.respond("🔐 **Two-Step Verification (2FA) Active.**\nPlease enter your **Cloud Password/PIN**:")
        except Exception as e:
            await event.respond(f"❌ Login failed: {str(e)}")

    elif state == "waiting_password":
        pwd = event.text.strip()
        data = TEMP_CLIENTS.get(event.sender_id)
        try:
            await data["client"].sign_in(password=pwd)
            await event.respond(f"✅ **Success!** 2FA Account added.")
            USER_STATE.pop(event.sender_id)
            TEMP_CLIENTS.pop(event.sender_id)
        except Exception as e:
            await event.respond(f"❌ Password error: {str(e)}")

print(f"v{VERSION} Ready...")
bot.run_until_disconnected()

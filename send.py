import os, asyncio, random
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
VERSION = "v1.3.1"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

USER_STATE = {} 
NEW_ACC_CLIENTS = {} 

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"🛠️ **Advanced Control Panel {VERSION}**",
        buttons=[
            [Button.inline("🚀 Start Blast", data="run_blast"), Button.inline("📊 Stats", data="get_status")],
            [Button.inline("📝 Edit Message", data="edit_msg"), Button.inline("📂 Add Usernames", data="add_users")],
            [Button.inline("📱 Add Account", data="add_acc"), Button.inline("♻️ Reset Progress", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')
    if data == "add_acc":
        USER_STATE[event.sender_id] = "waiting_phone"
        await event.respond("📱 **Enter the Phone Number:**\ne.g., `+639123456789`")
    elif data == "get_status":
        res = supabase.table("targets").select("count", count="exact").eq("status", "pending").execute()
        await event.answer(f"Pending Leads: {res.count}", alert=True)

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    state = USER_STATE.get(event.sender_id)
    if not state or event.text.startswith('/'): return

    if state == "waiting_phone":
        phone = event.text.strip()
        session_name = f"sess_{phone.replace('+', '')}"
        client = TelegramClient(session_name, API_ID, API_HASH)
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            NEW_ACC_CLIENTS[event.sender_id] = {"client": client, "phone": phone, "hash": sent_code.phone_code_hash}
            USER_STATE[event.sender_id] = "waiting_otp"
            await event.respond(f"📩 **OTP Sent to {phone}.**\nEnter the 5-digit code:")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
            USER_STATE.pop(event.sender_id)

    elif state == "waiting_otp":
        otp = event.text.strip()
        acc_data = NEW_ACC_CLIENTS.get(event.sender_id)
        client = acc_data["client"]
        try:
            await client.sign_in(acc_data["phone"], otp, phone_code_hash=acc_data["hash"])
            await event.respond(f"✅ **Account {acc_data['phone']} added!**")
            USER_STATE.pop(event.sender_id)
            NEW_ACC_CLIENTS.pop(event.sender_id)
        except errors.SessionPasswordNeededError:
            USER_STATE[event.sender_id] = "waiting_2fa"
            await event.respond("🔐 **2FA Required.** Enter password:")
        except Exception as e:
            await event.respond(f"❌ OTP Error: {str(e)}")

    elif state == "waiting_2fa":
        password = event.text.strip()
        acc_data = NEW_ACC_CLIENTS.get(event.sender_id)
        client = acc_data["client"]
        try:
            await client.sign_in(password=password)
            await event.respond(f"✅ **Authenticated with 2FA!**")
            USER_STATE.pop(event.sender_id)
            NEW_ACC_CLIENTS.pop(event.sender_id)
        except Exception as e:
            await event.respond(f"❌ 2FA Error: {str(e)}")

print(f"Bot v{VERSION} Operational...")
bot.run_until_disconnected()

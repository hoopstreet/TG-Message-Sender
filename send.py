import os, asyncio, random, glob, pytz, logging, re, base64
from datetime import datetime
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

try:
    API_ID = int(os.getenv("TELEGRAM_API_ID"))
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    token = os.getenv("CONTROL_BOT_TOKEN")
    supabase = create_client(url, key)
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=token)
except Exception as e: print(f"⚠️ Init Error: {e}")

def restore_sessions():
    try:
        res = supabase.table("saved_sessions").select("*").execute()
        for row in res.data:
            f_path = f"{row['phone_number']}.session"
            if not os.path.exists(f_path):
                with open(f_path, "wb") as f: f.write(base64.b64decode(row['session_data']))
    except: pass

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel Elite v5.8.7**\n/status | /add_list | /add_account")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    try:
        sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
        leads = supabase.table("message_campaign").select("status").execute().data
        pending = sum(1 for x in leads if x['status'] == 'pending')
        accs = len(glob.glob("*.session")) - 1
        await event.respond(f"📊 **Audit**\nPending: {pending}\nAccounts: {accs}\nSched: {'ON' if sets['is_sched_active'] else 'OFF'}")
    except Exception as e: await event.respond(f"❌ Status Error: {e}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Phone (+63...):**")
        phone = (await conv.get_response()).text.strip().replace(" ", "")
        s_name = f"session_{phone.replace('+', '')}"
        client = TelegramClient(s_name, API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **OTP:**")
            code = (await conv.get_response()).text
            try:
                await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA:**")
                pw = (await conv.get_response()).text
                await client.sign_in(password=pw)
            with open(f"{s_name}.session", "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                supabase.table("saved_sessions").upsert({"phone_number": s_name, "session_data": encoded}).execute()
            await event.respond(f"✅ Account {phone} Cloud-Synced.")
        except Exception as e: await event.respond(f"❌ Error: {e}")
        finally: await client.disconnect()

if __name__ == '__main__':
    restore_sessions()
    bot.run_until_disconnected()

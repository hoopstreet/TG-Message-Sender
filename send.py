import os, asyncio, random, glob, pytz, logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))
    print("✅ Connections Established")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    welcome_msg = (
        "👑 **Tacloban HQ: Weightless Commander**\n"
        "Welcome to your official Outreach Control Center. Use the guide below to manage the engine:\n\n"
        "/start - 👑 **Open Command Center Guide**\n"
        "Returns to this manual and refreshes the control buttons.\n\n"
        "/send_now - 🚀 **Trigger Immediate Manual Blast**\n"
        "Instantly begins the outreach process using all pending leads.\n\n"
        "/schedule - 📅 **Set Date/Time for Auto-Send**\n"
        "Programs the engine to trigger a blast at a specific PHT time.\n\n"
        "/pause_send - ⏸️ **Stop Active Manual Sending**\n"
        "Emergency kill-switch for the current manual outreach loop.\n\n"
        "/pause_sched - ⏸️ **Stop Active Scheduled Tasks**\n"
        "Toggles the automated scheduler to prevent planned blasts.\n\n"
        "/add_list - 📂 **Import New @Username List**\n"
        "Bulk import usernames directly into the Supabase database.\n\n"
        "/edit_msg - 📝 **Update Promotional Text**\n"
        "Changes the message script for all future outreach tasks.\n\n"
        "/add_account - 📱 **Link New Sender Session**\n"
        "Register or view connected Telegram session files.\n\n"
        "/status - 📊 **View Global Audit & Stats**\n"
        "Displays real-time success/failure metrics from the database."
    )
    
    buttons = [
        [Button.inline("🚀 Send Now", data="send_now"), Button.inline("📅 Schedule", data="schedule")],
        [Button.inline("📊 Status", data="status"), Button.inline("⏸️ Stop", data="pause_send")],
        [Button.inline("📱 Add Acc", data="add_account"), Button.inline("📝 Edit Msg", data="edit_msg")]
    ]
    await event.respond(welcome_msg, buttons=buttons)

@bot.on(events.CallbackQuery)
async def master_router(event):
    data = event.data.decode('utf-8')
    if data == "status":
        res = supabase.table("message_campaign").select("status").execute()
        s = sum(1 for r in res.data if r['status'] == 'success')
        await event.respond(f"📊 **Audit:** {s} messages sent successfully.")

async def main():
    print("🚀 Tacloban HQ v3.3.5 Operational")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

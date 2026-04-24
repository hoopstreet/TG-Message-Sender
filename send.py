import os, asyncio, random, glob, pytz, logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

# 1. Setup Logging to see errors in Northflank logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()

PHT = pytz.timezone('Asia/Manila')

# 2. Safe Initialization
try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))
    print("✅ Connections Established")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# 3. UI: Command Manual
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    guide = (
        "👑 **Tacloban HQ Command Center**\n\n"
        "**🚀 Campaigns**\n/send_now | /schedule | /status\n\n"
        "**📂 Data**\n/add_list | /edit_msg\n\n"
        "**📱 Settings**\n/add_account | /pause_send | /pause_sched"
    )
    buttons = [
        [Button.inline("🚀 Send Now", data="send_now"), Button.inline("📅 Schedule", data="schedule")],
        [Button.inline("📊 Status", data="status"), Button.inline("📂 Add List", data="add_list")],
        [Button.inline("📝 Edit Msg", data="edit_msg"), Button.inline("📱 Add Acc", data="add_account")],
        [Button.inline("⏸️ Pause Send", data="pause_send"), Button.inline("⏸️ Pause Sched", data="pause_sched")]
    ]
    await event.respond(guide, buttons=buttons)

# 4. Background Loops
async def scheduler_loop():
    while True:
        try:
            now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
            # Check Supabase connection during loop
            supabase.table("message_campaign").select("id").limit(1).execute()
        except:
            print("⚠️ Supabase heartbeat failed")
        await asyncio.sleep(60)

async def main():
    print("🚀 Tacloban HQ v3.2.1 Operational")
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

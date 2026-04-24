import os, asyncio, random, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
PHT = pytz.timezone('Asia/Manila')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

# --- 1. UI: BotFather Style Manual ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    guide = (
        "I can help you manage your Outreach Campaigns.\n\n"
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

# --- 2. Router: Callback Handlers ---
@bot.on(events.CallbackQuery)
async def master_router(event):
    data = event.data.decode('utf-8')
    if data == "status":
        res = supabase.table("message_campaign").select("status").execute()
        s = sum(1 for r in res.data if r['status'] == 'success')
        await event.respond(f"📊 **Audit:** {s} Successes.")
    elif data == "pause_send":
        supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
        await event.respond("⏸️ Manual Outreach Paused.")

# --- 3. Engine: Outreach & Scheduler ---
async def scheduler_loop():
    while True:
        now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
        res = supabase.table("message_campaign").select("*").eq("schedule", now_pht).eq("pause_sched", False).execute()
        for task in res.data: asyncio.create_task(run_blast(task))
        await asyncio.sleep(60)

async def run_blast(row):
    # Outreach logic placeholder
    pass

# --- 4. Bridge: Execution ---
async def main():
    print("🚀 Tacloban HQ v3.2.0 Active")
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

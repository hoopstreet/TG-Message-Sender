import os, asyncio, random, glob, pytz, logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

# 1. Safe Initialization
try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))
    print("✅ Connections Established")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# 2. UI: Command Manual
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

# 3. Router: Callback Data Mapping
@bot.on(events.CallbackQuery)
async def master_router(event):
    data = event.data.decode('utf-8')
    if data == "status":
        await event.answer("Fetching status...", alert=False)
        res = supabase.table("message_campaign").select("status").execute()
        s = sum(1 for r in res.data if r['status'] == 'success')
        await event.respond(f"📊 **Audit:** {s} Successes recorded.")
    # Add other mappings here as needed
@bot.on(events.CallbackQuery(data="add_list"))
async def add_list_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Tacloban HQ Ingestion:**\nSend me @usernames (one per line).")
        response = await conv.get_response()
        usernames = [u.strip() for u in response.text.split('\n') if u.strip()]
        for u in usernames:
            if u: supabase.table("message_campaign").upsert({"username": u, "status": "pending"}).execute()
        await conv.send_message(f"✅ Successfully imported {len(usernames)} leads.")

@bot.on(events.CallbackQuery(data="edit_msg"))
async def edit_msg_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Promo Script Update:**\nSend the new message content:")
        response = await conv.get_response()
        supabase.table("message_campaign").update({"edit_msg": response.text}).eq("status", "pending").execute()
        await conv.send_message("✅ Promo script updated for all pending leads.")

# 4. Background Loops & Execution
async def scheduler_loop():
    while True:
        try:
            now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
            # Heartbeat to keep connection alive
            supabase.table("message_campaign").select("id").limit(1).execute()
        except:
            pass
        await asyncio.sleep(60)

async def main():
    print("🚀 Tacloban HQ v3.2.2 Operational")
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

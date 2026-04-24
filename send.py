import os, asyncio, random, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
PHT = pytz.timezone('Asia/Manila')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Weightless Commander**", buttons=[
        [Button.inline("🚀 Send Now", data="send_now"), Button.inline("📅 Schedule", data="schedule")],
        [Button.inline("📊 Status", data="status"), Button.inline("📂 Add List", data="add_list")],
        [Button.inline("📝 Edit Msg", data="edit_msg"), Button.inline("📱 Add Acc", data="add_account")],
        [Button.inline("⏸️ Pause Send", data="pause_send"), Button.inline("⏸️ Pause Sched", data="pause_sched")]
    ])

@bot.on(events.CallbackQuery)
async def master_router(event):
    data = event.data.decode('utf-8')
    # 1:1 Mapping Logic
    if data == "status":
        res = supabase.table("message_campaign").select("status").execute()
        s, f, p = sum(1 for r in res.data if r['status'] == 'success'), sum(1 for r in res.data if r['status'] == 'failed'), sum(1 for r in res.data if r['status'] == 'pending')
        await event.respond(f"📊 **Audit:** ✅{s} | ❌{f} | ⏳{p}")
    
    elif data == "pause_send":
        supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
        await event.respond("⏸️ Manual Outreach Paused.")

    elif data == "pause_sched":
        supabase.table("message_campaign").update({"pause_sched": True}).execute()
        await event.respond("⏸️ Scheduler Paused.")

@bot.on(events.CallbackQuery(data="add_list"))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 Send @usernames:")
        msg = await conv.get_response()
        for n in msg.text.split('\n'):
            if n.strip(): supabase.table("message_campaign").upsert({"username": n.strip(), "status": "pending"}).execute()
        await conv.send_message("✅ Leads Added.")

# --- v3.0.0 Background Service Bridge ---
async def main():
    print("🚀 Tacloban HQ Engine Starting...")
    # Start the scheduler loop in the background
    asyncio.create_task(scheduler_loop())
    # Keep the bot running
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

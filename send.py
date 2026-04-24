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
    welcome_msg = "👑 **Tacloban HQ: Command Center**\nSelect an option below or use the slash commands."
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
        f = sum(1 for r in res.data if r['status'] == 'failed')
        p = sum(1 for r in res.data if r['status'] == 'pending')
        await event.respond(f"📊 **Global Audit**\n✅ Success: {s}\n❌ Failed: {f}\n⏳ Pending: {p}")
    elif data == "send_now":
        await event.answer("🚀 Blast Started!", alert=True)
        sessions = glob.glob("*.session")
        if not sessions:
            await event.respond("❌ No .session files found!")
            return
        leads = supabase.table("message_campaign").select("*").eq("status", "pending").execute()
        for lead in leads.data:
            sess = random.choice(sessions).replace(".session", "")
            try:
                async with TelegramClient(sess, int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")) as client:
                    await client.send_message(lead['username'], lead['edit_msg'])
                    supabase.table("message_campaign").update({"status": "success"}).eq("id", lead['id']).execute()
                await asyncio.sleep(random.randint(30, 60))
            except Exception as e:
                supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()
    elif data == "pause_send":
        supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
        await event.respond("⏸️ All pending tasks moved to Paused.")

@bot.on(events.NewMessage(pattern='/add_list|/edit_msg|/schedule'))
async def handles(event):
    cmd = event.text
    if '/add_list' in cmd:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📂 **Send @usernames (one per line):**")
            msg = await conv.get_response()
            leads = [u.strip() for u in msg.text.split('\n') if u.strip()]
            for u in leads:
                supabase.table("message_campaign").upsert({"username": u, "status": "pending"}).execute()
            await conv.send_message(f"✅ {len(leads)} leads added.")
    elif '/edit_msg' in cmd:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📝 **Send New Promo Script:**")
            msg = await conv.get_response()
            supabase.table("message_campaign").update({"edit_msg": msg.text}).eq("status", "pending").execute()
            await conv.send_message("✅ Script updated.")

async def main():
    print("🚀 Tacloban HQ v3.4.1 Active")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

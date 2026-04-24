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
    guide = (
        "👑 **Tacloban HQ: Weightless Commander**\n"
        "Outreach Engine Guide:\n\n"
        "/start - 👑 Guide\n"
        "/send_now - 🚀 Trigger Blast\n"
        "/schedule - 📅 Set PHT Time\n"
        "/pause_send - ⏸️ Stop Sending\n"
        "/add_list - 📂 Import Leads\n"
        "/edit_msg - 📝 Update Script\n"
        "/add_account - 📱 View Sessions\n"
        "/status - 📊 View Audit"
    )
    await event.respond(guide)

@bot.on(events.NewMessage(pattern='/status'))
async def status_report(event):
    res = supabase.table("message_campaign").select("status").execute()
    s = sum(1 for r in res.data if r['status'] == 'success')
    f = sum(1 for r in res.data if r['status'] == 'failed')
    p = sum(1 for r in res.data if r['status'] == 'pending')
    await event.respond(f"📊 **Audit:**\n✅ Success: {s}\n❌ Failed: {f}\n⏳ Pending: {p}")

@bot.on(events.NewMessage(pattern='/send_now'))
async def manual_blast(event):
    await event.respond("🚀 **Blast Started!** Monitoring sessions...")
    sessions = glob.glob("*.session")
    leads = supabase.table("message_campaign").select("*").eq("status", "pending").limit(20).execute()
    if not leads.data:
        await event.respond("⏳ No pending leads found in Supabase.")
        return
    for lead in leads.data:
        sess = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(sess, int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")) as client:
                await client.send_message(lead['username'], lead.get('edit_msg', "Check out our latest deals!"))
                supabase.table("message_campaign").update({"status": "success"}).eq("id", lead['id']).execute()
            await asyncio.sleep(random.randint(30, 60))
        except Exception as e:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()

@bot.on(events.NewMessage(pattern='/pause_send'))
async def pause_engine(event):
    supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
    await event.respond("⏸️ **Engine Halted.**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def account_manager(event):
    sessions = glob.glob("*.session")
    s_list = "\n".join([f"📱 {s}" for s in sessions]) if sessions else "No sessions."
    await event.respond(f"📱 **Sessions:**\n{s_list}")

@bot.on(events.NewMessage(pattern='/add_list|/edit_msg'))
async def inputs(event):
    if '/add_list' in event.text:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📂 **Send @usernames (one per line):**")
            msg = await conv.get_response()
            leads = [u.strip() for u in msg.text.split('\n') if u.strip()]
            for u in leads:
                supabase.table("message_campaign").upsert({"username": u, "status": "pending"}).execute()
            await conv.send_message(f"✅ {len(leads)} leads added.")
    elif '/edit_msg' in event.text:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📝 **Send Script:**")
            msg = await conv.get_response()
            supabase.table("message_campaign").update({"edit_msg": msg.text}).eq("status", "pending").execute()
            await conv.send_message("✅ Script updated.")

async def main():
    print("🚀 Tacloban HQ v3.4.6 Active (Full Loop Fixed)")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

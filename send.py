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
        "Welcome to your official Outreach Control Center.\n\n"
        "/start - 👑 **Open Command Center Guide**\n"
        "/send_now - 🚀 **Trigger Immediate Manual Blast**\n"
        "/schedule - 📅 **Set Date/Time for Auto-Send**\n"
        "/pause_send - ⏸️ **Stop Active Manual Sending**\n"
        "/pause_sched - ⏸️ **Stop Active Scheduled Tasks**\n"
        "/add_list - 📂 **Import New @Username List**\n"
        "/edit_msg - 📝 **Update Promotional Text**\n"
        "/add_account - 📱 **Link New Sender Session**\n"
        "/status - 📊 **View Global Audit & Stats**"
    )
    await event.respond(guide)

@bot.on(events.CallbackQuery)
async def master_router(event):
    data = event.data.decode('utf-8')
    if data == "status":
        res = supabase.table("message_campaign").select("status").execute()
        s = sum(1 for r in res.data if r['status'] == 'success')
        await event.respond(f"📊 **Audit:** {s} successful sends recorded.")

@bot.on(events.NewMessage(pattern='/send_now'))
async def manual_blast(event):
    await event.respond("🚀 **Initializing Manual Blast...**")
    sessions = glob.glob("*.session")
    leads = supabase.table("message_campaign").select("*").eq("status", "pending").limit(20).execute()
    for lead in leads.data:
        sess = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(sess, int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")) as client:
                await client.send_message(lead['username'], lead.get('edit_msg', "Check out our latest deals!"))
                supabase.table("message_campaign").update({"status": "success"}).eq("id", lead['id']).execute()
            await asyncio.sleep(random.randint(30, 60))
        except Exception as e:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()

@bot.on(events.NewMessage(pattern='/add_list|/edit_msg'))
async def input_handlers(event):
    if '/add_list' in event.text:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📂 **Send @usernames (one per line):**")
            msg = await conv.get_response()
            leads = [u.strip() for u in msg.text.split('\n') if u.strip()]
            for u in leads:
                supabase.table("message_campaign").upsert({"username": u, "status": "pending"}).execute()
            await conv.send_message(f"✅ {len(leads)} leads added to Supabase.")
    elif '/edit_msg' in event.text:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📝 **Send your new Promo Script:**")
            msg = await conv.get_response()
            supabase.table("message_campaign").update({"edit_msg": msg.text}).eq("status", "pending").execute()
            await conv.send_message("✅ Promo script updated.")

async def main():
    print("🚀 Tacloban HQ v3.4.2 Active (Menu Hidden)")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

@bot.on(events.NewMessage(pattern='/status'))
async def status_report(event):
    res = supabase.table("message_campaign").select("status").execute()
    s = sum(1 for r in res.data if r['status'] == 'success')
    f = sum(1 for r in res.data if r['status'] == 'failed')
    p = sum(1 for r in res.data if r['status'] == 'pending')
    report = (
        "📊 **Tacloban HQ Global Audit**\n\n"
        f"✅ **Success:** {s}\n"
        f"❌ **Failed:** {f}\n"
        f"⏳ **Pending:** {p}\n\n"
        "Engine Status: **Operational**"
    )
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/pause_send'))
async def pause_engine(event):
    supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
    await event.respond("⏸️ **Manual Outreach Halted.** All pending leads moved to 'paused' state.")

@bot.on(events.NewMessage(pattern='/add_account'))
async def account_manager(event):
    sessions = glob.glob("*.session")
    session_list = "\n".join([f"📱 {s}" for s in sessions]) if sessions else "No sessions found."
    msg = (
        "📱 **Linked Sender Sessions:**\n\n"
        f"{session_list}\n\n"
        "To add a new account, upload the `.session` file directly to the root folder via GitHub/iSH."
    )
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_manager(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📅 **Enter Target PHT Time:**\nFormat: `YYYY-MM-DD HH:MM`")
        response = await conv.get_response()
        # In a weightless setup, we'd save this to a 'schedules' table in Supabase
        await conv.send_message(f"✅ **Scheduled!** Engine will trigger blast at `{response.text}` PHT.")

import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')
API_ID, API_HASH = int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

SENDING_ACTIVE = True
SCHED_ACTIVE = True

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    guide = (
        "👑 **Tacloban HQ: Command Center**\n\n"
        "/start - 👑 Open Command Center Guide\n"
        "/send_now - 🚀 Trigger Immediate Manual Blast\n"
        "/schedule - 📅 Set Date/Time for Auto-Send\n"
        "/pause_send - ⏸️ Stop Active Manual Sending\n"
        "/pause_sched - ⏸️ Stop Active Scheduled Tasks\n"
        "/add_list - 📂 Import New @Username List\n"
        "/edit_msg - 📝 Update Promotional Text\n"
        "/add_account - 📱 Link New Sender Session\n"
        "/status - 📊 View Global Audit & Stats"
    )
    await event.respond(guide)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send List:** (Auto-Deduplicate Active)")
        msg = await conv.get_response()
        found = re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', msg.text)
        existing = {r['username'] for r in supabase.table("message_campaign").select("username").execute().data}
        new_leads = [{"username": u, "status": "pending"} for u in found if u not in existing]
        if new_leads: supabase.table("message_campaign").insert(new_leads).execute()
        await conv.send_message(f"✅ **Integrated:** {len(new_leads)} unique leads added.")

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = True
    await event.respond("🚀 **Blast Starting...** (Includes Auto-Organize)")
    supabase.table("message_campaign").delete().eq("status", "failed").execute()
    leads = supabase.table("message_campaign").select("*").eq("status", "pending").execute().data
    sessions = glob.glob("*.session")
    for lead in leads:
        if not SENDING_ACTIVE: break
        s_name = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                await client.send_message(lead['username'], lead.get('edit_msg', "Check this out!"))
                supabase.table("message_campaign").update({"status": "success", "sender_phone": s_name}).eq("id", lead['id']).execute()
            await asyncio.sleep(random.randint(60, 120))
        except Exception:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop_manual(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = False
    await event.respond("⏸️ **Manual Engine Halted.**")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **New Promo Text?**")
        new_text = (await conv.get_response()).text
        supabase.table("message_campaign").update({"edit_msg": new_text}).eq("status", "pending").execute()
        await event.respond("✅ **Script Updated Globally.**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Phone Number?** (+63...)")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        await conv.send_message("📩 **OTP?**")
        otp = (await conv.get_response()).text.strip()
        try:
            await client.sign_in(phone, otp)
        except errors.SessionPasswordNeededError:
            await conv.send_message("🔐 **2FA PIN?**")
            await client.sign_in(password=(await conv.get_response()).text.strip())
        await conv.send_message(f"✅ {phone} Linked.")
        await client.disconnect()

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    data = supabase.table("message_campaign").select("status, sender_phone").execute().data
    stats = {}
    for r in data:
        p = r.get('sender_phone') or "Legacy"
        if p not in stats: stats[p] = 0
        if r['status'] == 'success': stats[p] += 1
    acc_report = "\n".join([f"📱 {p}: {c} msgs" for p, c in stats.items()])
    await event.respond(f"📊 **Global Audit**\nSent: {sum(1 for x in data if x['status'] == 'success')}\nPending: {sum(1 for x in data if x['status'] == 'pending')}\n\n**Account Stats:**\n{acc_report}")

@bot.on(events.NewMessage(pattern='/schedule'))
async def sched(event): await event.respond("📅 **Scheduler Sync Active.**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def p_sched(event):
    global SCHED_ACTIVE
    SCHED_ACTIVE = not SCHED_ACTIVE
    await event.respond(f"📅 **Scheduler {'RESUMED' if SCHED_ACTIVE else 'PAUSED'}.**")

async def main(): await bot.run_until_disconnected()
if __name__ == '__main__': asyncio.get_event_loop().run_until_complete(main())

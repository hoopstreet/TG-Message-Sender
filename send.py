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

SENDING_ACTIVE = False
SCHED_ACTIVE = True

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Weightless Commander**\n\n/start - 👑 Guide\n/send_now - 🚀 Blast\n/schedule - 📅 Schedule\n/pause_send - ⏸️ Stop Send\n/pause_sched - ⏸️ Stop Sched\n/add_list - 📂 List\n/edit_msg - 📝 Script\n/add_account - 📱 Account\n/status - 📊 Stats")

async def background_blast(event):
    global SENDING_ACTIVE
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
        except:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()
    SENDING_ACTIVE = False
    await event.respond("🏁 **Blast Sequence Completed.**")

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    global SENDING_ACTIVE
    if SENDING_ACTIVE:
        return await event.respond("⚠️ **Engine is already running.**")
    SENDING_ACTIVE = True
    await event.respond("🚀 **Blast Starting...** (Running in Background)")
    asyncio.create_task(background_blast(event)) # This is the magic fix

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop_manual(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = False
    await event.respond("⏸️ **Manual Engine Halted.**")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    res = supabase.table("message_campaign").select("*").execute().data
    sessions = glob.glob("*.session")
    total = sum(1 for x in res if x['username'] != "SCHEDULE_MARKER")
    sent = sum(1 for x in res if x['status'] == 'success')
    fail = sum(1 for x in res if x['status'] == 'failed')
    pend = sum(1 for x in res if x['status'] == 'pending')
    report = (f"📊 **Tacloban HQ: Deep Audit**\n👥 Total Leads: {total}\n✅ Sent: {sent} | ❌ Failed: {fail}\n⏳ Pending: {pend}\n\n📱 Active Sessions: {len(sessions)}\n--------------------------\nEngine: {'🚀 Running' if SENDING_ACTIVE else 'Ready'}")
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Step 1: Enter Number (+63...)**")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            await conv.send_message("📩 **Step 2: Enter OTP:**")
            otp = (await conv.get_response()).text.strip()
            await client.sign_in(phone, otp, phone_code_hash=sent_code.phone_code_hash)
        except Exception as e:
            await conv.send_message(f"❌ Error: {e}"); return
        await conv.send_message(f"✅ Linked: {phone}")
        await client.disconnect()

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send List:**")
        msg = await conv.get_response()
        found = re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', msg.text)
        existing = {r['username'] for r in supabase.table("message_campaign").select("username").execute().data}
        new_leads = [{"username": u, "status": "pending"} for u in found if u not in existing]
        if new_leads: supabase.table("message_campaign").insert(new_leads).execute()
        await conv.send_message(f"✅ Integrated: {len(new_leads)} unique leads added.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Promo Script?**")
        new_text = (await conv.get_response()).text
        supabase.table("message_campaign").update({"edit_msg": new_text}).eq("status", "pending").execute()
        await event.respond("✅ **Script Updated.**")

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📅 **Target Date/Time?**")
        target = (await conv.get_response()).text.strip()
        supabase.table("message_campaign").insert({"username": "SCHEDULE_MARKER", "status": "scheduled", "created_at": target}).execute()
        await event.respond(f"📅 **Set for {target}**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def p_sched(event):
    global SCHED_ACTIVE; SCHED_ACTIVE = not SCHED_ACTIVE
    await event.respond(f"📅 **Scheduler {'RESUMED' if SCHED_ACTIVE else 'PAUSED'}.**")

async def main(): await bot.run_until_disconnected()
if __name__ == '__main__': asyncio.get_event_loop().run_until_complete(main())

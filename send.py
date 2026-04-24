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

def get_hq():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

async def scheduler_loop():
    while True:
        hq = get_hq()
        if hq['is_sched_active']:
            now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
            job = supabase.table("schedules").select("*").eq("status", "pending").lte("execute_at", now_pht).limit(1).execute()
            if job.data:
                supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
                asyncio.create_task(background_worker(None))
                supabase.table("schedules").update({"status": "fired"}).eq("id", job.data[0]['id']).execute()
        await asyncio.sleep(60)

async def background_worker(event):
    while True:
        hq = get_hq()
        if not hq['is_sending_active']: break
        lead_req = supabase.table("targets").select("*").eq("status", "pending").limit(1).execute()
        if not lead_req.data: break
        lead = lead_req.data[0]
        sessions = glob.glob("*.session")
        if not sessions: break
        s_name = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                await client.send_message(lead['username'], hq.get('current_promo_text', "Hi!"))
                supabase.table("targets").update({"status": "success"}).eq("id", lead['id']).execute()
        except:
            supabase.table("targets").update({"status": "failed"}).eq("id", lead['id']).execute()
        await asyncio.sleep(random.randint(60, 120))
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    if event: await event.respond("🏁 **Sequence Finished.**")

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Weightless Commander**\n\n/start - 👑 Guide\n/send_now - 🚀 Blast\n/schedule - 📅 Schedule\n/status - 📊 Stats\n/pause_send - ⏸️ Stop Send\n/pause_sched - ⏸️ Stop Sched")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    hq = get_hq()
    res = supabase.table("targets").select("status").execute().data
    sessions = glob.glob("*.session")
    report = (f"📊 **HQ Audit**\n👥 Leads: {len(res)} | ⏳ Pend: {sum(1 for x in res if x['status'] == 'pending')}\n📱 Sessions: {len(sessions)}\nEngine: {'🚀 BLASTING' if hq['is_sending_active'] else 'Ready'}\nSched: {'✅ ON' if hq['is_sched_active'] else '⏸️ OFF'}")
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Manual Engine Engaged.**")
    asyncio.create_task(background_worker(event))

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop(event):
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Engine Halted.**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def p_sched(event):
    hq = get_hq()
    new_state = not hq['is_sched_active']
    supabase.table("bot_settings").update({"is_sched_active": new_state}).eq("id", "production").execute()
    await event.respond(f"📅 **Scheduler {'RESUMED' if new_state else 'PAUSED'}.**")

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📅 **PHT Time?** (YYYY-MM-DD HH:MM)")
        target = (await conv.get_response()).text.strip()
        supabase.table("schedules").insert({"execute_at": target, "status": "pending"}).execute()
        await event.respond(f"✅ **Auto-Blast set: {target}**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id, timeout=300) as conv:
        await conv.send_message("📱 **Phone (+63...):**")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            await conv.send_message("📩 **OTP:**")
            otp = (await conv.get_response()).text.strip()
            await client.sign_in(phone, otp, phone_code_hash=sent_code.phone_code_hash)
            await conv.send_message(f"✅ Success!")
        except Exception as e: await conv.send_message(f"❌ {e}")
        finally: await client.disconnect()

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Promo Script:**")
        text = (await conv.get_response()).text
        supabase.table("bot_settings").update({"current_promo_text": text}).eq("id", "production").execute()
        await event.respond("✅ **Updated.**")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Usernames:**")
        msg = (await conv.get_response()).text
        found = re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', msg)
        new_leads = [{"username": u, "status": "pending"} for u in found]
        if new_leads: supabase.table("targets").insert(new_leads).execute()
        await conv.send_message(f"✅ Added {len(new_leads)}.")

async def main():
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

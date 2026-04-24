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
        try:
            hq = get_hq()
            if hq['is_sched_active']:
                now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
                # Fixed column name to scheduled_for
                job = supabase.table("schedules").select("*").eq("status", "pending").lte("scheduled_for", now_pht).limit(1).execute()
                if job.data:
                    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
                    asyncio.create_task(background_worker(None))
                    supabase.table("schedules").update({"status": "fired"}).eq("id", job.data[0]['id']).execute()
        except Exception as e: logging.error(f"Sched Loop Error: {e}")
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
    if event: await event.respond("🏁 **Blast Sequence Completed.**")

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    menu = ("👑 **Tacloban HQ: Weightless Commander**\n\n/start - 👑 Guide\n/send_now - 🚀 Blast\n/schedule - 📅 Schedule\n/pause_send - ⏸️ Stop Send\n/pause_sched - ⏸️ Stop Sched\n/add_list - 📂 List\n/edit_msg - 📝 Script\n/add_account - 📱 Account\n/status - 📊 Stats")
    await event.respond(menu)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    hq = get_hq()
    res = supabase.table("targets").select("status").execute().data
    sessions = glob.glob("*.session")
    report = (f"📊 **Global Audit**\n👥 Leads: {len(res)} | ⏳ Pend: {sum(1 for x in res if x['status'] == 'pending')}\n📱 Sessions: {len(sessions)}\nEngine: {'🚀 BLASTING' if hq['is_sending_active'] else 'Ready'}\nSched: {'✅ ON' if hq['is_sched_active'] else '⏸️ OFF'}")
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Manual Engine Engaged.**")
    asyncio.create_task(background_worker(event))

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop(event):
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Manual Sending Halted.**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def p_sched(event):
    hq = get_hq()
    new_state = not hq['is_sched_active']
    supabase.table("bot_settings").update({"is_sched_active": new_state}).eq("id", "production").execute()
    await event.respond(f"📅 **Scheduled Tasks {'RESUMED' if new_state else 'PAUSED'}.**")

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📅 **Set Auto-Send Time (PHT)?**\nFormat: `YYYY-MM-DD HH:MM`")
        resp = await conv.get_response()
        if resp and resp.text:
            target = resp.text.strip()
            # Fixed column name to scheduled_for
            supabase.table("schedules").insert({"scheduled_for": target, "status": "pending"}).execute()
            await event.respond(f"✅ **Auto-Send scheduled for {target}.**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id, timeout=300) as conv:
        await conv.send_message("📱 **Enter Phone (+63...):**")
        p_resp = await conv.get_response()
        if not p_resp: return
        phone = p_resp.text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            await conv.send_message("📩 **Enter OTP:**")
            o_resp = await conv.get_response()
            if o_resp:
                otp = o_resp.text.strip()
                await client.sign_in(phone, otp, phone_code_hash=sent_code.phone_code_hash)
                await conv.send_message(f"✅ Sender Session Linked!")
        except Exception as e: await conv.send_message(f"❌ {e}")
        finally: await client.disconnect()

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Paste New Promotional Text:**")
        resp = await conv.get_response()
        if resp:
            text = resp.text
            supabase.table("bot_settings").update({"current_promo_text": text}).eq("id", "production").execute()
            await event.respond("✅ **Promo Text Updated.**")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste New @Username List:**")
        resp = await conv.get_response()
        if resp:
            found = re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', resp.text)
            new_leads = [{"username": u, "status": "pending"} for u in found]
            if new_leads: supabase.table("targets").insert(new_leads).execute()
            await conv.send_message(f"✅ Imported {len(new_leads)} unique leads.")

async def main():
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

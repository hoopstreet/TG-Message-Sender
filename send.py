import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime, timedelta
from telethon import TelegramClient, events, errors, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')
API_ID, API_HASH = int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

MSG_LIMIT, WARMUP_HOURS = 5, 24
GREETINGS = ["Hi", "Hello", "Hey", "Greetings", "Good day"]

def get_hq():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

async def background_worker(event):
    hq = get_hq()
    all_files = [f for f in glob.glob("*.session") if "bot.session" not in f]
    trusted = []
    for f in all_files:
        ctime = os.path.getctime(f)
        if (datetime.now() - datetime.fromtimestamp(ctime)) > timedelta(hours=WARMUP_HOURS):
            trusted.append((f, ctime))
    
    trusted.sort(key=lambda x: x[1]) # Seniority First
    sessions = [x[0] for x in trusted]
    stats = {s: 0 for s in sessions}

    while True:
        hq = get_hq()
        if not hq['is_sending_active']: break
        ready = [s for s, count in stats.items() if count < MSG_LIMIT]
        if not ready:
            tomorrow = (datetime.now(PHT) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
            if event: await event.respond(f"🛑 **Limits hit. Shifted to: {tomorrow}**")
            break
        
        s_file = ready[0]
        s_name = s_file.replace(".session", "")
        lead_req = supabase.table("targets").select("*").eq("status", "pending").limit(1).execute()
        if not lead_req.data: break
        lead = lead_req.data[0]

        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                greet = random.choice(GREETINGS)
                msg = hq.get('current_promo_text', "").replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                await client.send_message(lead['username'], msg)
                supabase.table("targets").update({"status": "success", "sent_by": s_name}).eq("id", lead['id']).execute()
                stats[s_file] += 1
        except Exception: pass
        await asyncio.sleep(random.randint(150, 300))
    
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    menu = ("👑 **Tacloban HQ: Weightless Commander**\n\n"
            "/start - 👑 Guide\n/send_now - 🚀 Blast\n/schedule - 📅 Schedule\n"
            "/pause_send - ⏸️ Stop Send\n/pause_sched - ⏸️ Stop Sched\n"
            "/add_list - 📂 List\n/edit_msg - 📝 Script\n"
            "/add_account - 📱 Account\n/status - 📊 Stats")
    await event.respond(menu)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    all_s = [f for f in glob.glob("*.session") if "bot.session" not in f]
    ready, warm = [], []
    for s in all_s:
        if datetime.now() - datetime.fromtimestamp(os.path.getctime(s)) < timedelta(hours=WARMUP_HOURS):
            warm.append(s)
        else: ready.append(s)
    leads = supabase.table("targets").select("status").execute().data
    pend = sum(1 for x in leads if x['status'] == 'pending')
    await event.respond(f"📊 **Global Audit**\n👥 Leads: {len(leads)} | ⏳ Pend: {pend}\n✅ Ready: {len(ready)}\n🔥 Warm: {len(warm)}\nEngine: Ready")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Paste New Promotional Text:**")
        msg = await conv.get_response()
        supabase.table("bot_settings").update({"current_promo_text": msg.text}).eq("id", "production").execute()
        await event.respond("✅ **Promo Text Updated.**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Enter Phone (+63...):**")
        phone = (await conv.get_response()).text
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        await conv.send_message("📩 **OTP Code:**")
        code = (await conv.get_response()).text
        try:
            await client.sign_in(phone, code)
            await event.respond(f"✅ Success! {phone} linked.")
        except errors.SessionPasswordNeededError:
            await conv.send_message("🔐 **2FA Password Required:**")
            pw = (await conv.get_response()).text
            await client.sign_in(password=pw)
            await event.respond(f"✅ Success! {phone} linked with 2FA.")
        await client.disconnect()

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Manual Engine Engaged.**")
    asyncio.create_task(background_worker(event))

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(bot.run_until_disconnected())

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste Lead List (@usernames):**")
        r = await conv.get_response()
        if r:
            found = list(set(re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', r.text)))
            leads = [{"username": u, "status": "pending"} for u in found]
            if leads: supabase.table("targets").insert(leads).execute()
            await event.respond(f"✅ **Imported {len(leads)} unique leads.**")

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop_send(event):
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Kill-Signal Sent. Manual sending halted.**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def stop_sched(event):
    supabase.table("bot_settings").update({"is_sched_active": False}).eq("id", "production").execute()
    await event.respond("📅 **Scheduled Tasks PAUSED.**")

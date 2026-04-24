import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

def get_settings():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

async def global_worker():
    while True:
        sets = get_settings()
        if not sets['is_sending_active'] and not sets['is_sched_active']:
            await asyncio.sleep(30); continue

        sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
        for s_file in sessions:
            s_name = s_file.replace(".session", "")
            today = datetime.now(PHT).strftime('%Y-%m-%d')
            sent_today = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute().count
            if sent_today >= 5: continue 

            lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
            if not lead_req.data: break
            lead = lead_req.data[0]

            try:
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Greetings", "Good day"])
                    msg = sets['current_promo_text'].replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                    await client.send_message(lead['add_list'], msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(240, 480))
            except: continue
        await asyncio.sleep(3600)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    msg = "👑 **Weightless Commander v5.5.2**\n\n/status - 📊 Stats\n/add_list - 📂 List\n/edit_msg - 📝 Script\n/schedule - 📅 Schedule\n/add_account - 📱 Account"
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = get_settings()
    leads = supabase.table("message_campaign").select("*").execute().data
    today = datetime.now(PHT).strftime('%Y-%m-%d')
    daily = sum(1 for x in leads if x['status'] == 'success' and x['updated_at'] and x['updated_at'].startswith(today))
    pending = sum(1 for x in leads if x['status'] == 'pending')
    sched = next((x['updated_at'] for x in leads if x['status'] == 'scheduled'), "OFF")
    await event.respond(f"📊 **Audit**\nList: {len(leads)} | Pend: {pending}\nDaily: {daily} | Accs: {len(glob.glob('*.session'))-1}\nSched: {sched}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    await event.respond(f"📱 **Active Sessions:** {len(glob.glob('*.session'))-1}\nTo add more, use `login.py` in iSH and push the session to GitHub.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Paste New Promo Script:**")
        r = await conv.get_response()
        supabase.table("bot_settings").update({"current_promo_text": r.text}).eq("id", "production").execute()
        await event.respond("✅ **Updated.**")

@bot.on(events.NewMessage(pattern='/schedule'))
async def toggle_sched(event):
    sets = get_settings()
    if sets['is_sched_active']:
        supabase.table("bot_settings").update({"is_sched_active": False}).eq("id", "production").execute()
        supabase.table("message_campaign").delete().eq("status", "scheduled").execute()
        await event.respond("⏸️ **Schedule Cleared.**")
    else:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📅 **Enter Start Time (YYYY-MM-DD HH:MM AM/PM):**")
            r = (await conv.get_response()).text
            try:
                supabase.table("bot_settings").update({"is_sched_active": True}).eq("id", "production").execute()
                supabase.table("message_campaign").insert({"add_list": "SCHEDULE_MARKER", "status": "scheduled", "updated_at": r}).execute()
                await event.respond(f"✅ **Set for:** {r}")
            except: await event.respond("❌ Format Error.")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste List:**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        for u in found:
            supabase.table("message_campaign").upsert({"add_list": u, "status": "pending"}).execute()
        await event.respond(f"✅ Processed {len(found)} leads.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Enter Phone Number:**\n(e.g., +639XXXXXXXXX)")
        phone_raw = (await conv.get_response()).text
        phone = phone_raw.strip().replace(" ", "")
        
        # Create unique session name
        s_name = f"session_{phone.replace('+', '')}"
        temp_client = TelegramClient(s_name, API_ID, API_HASH)
        await temp_client.connect()
        
        try:
            await temp_client.send_code_request(phone)
            await conv.send_message("📩 **Enter OTP Code:**")
            code = (await conv.get_response()).text
            
            try:
                await temp_client.sign_in(phone, code)
            except Exception as e:
                if "password" in str(e).lower():
                    await conv.send_message("🔐 **2FA Password Required:**")
                    pw = (await conv.get_response()).text
                    await temp_client.sign_in(password=pw)
                else: raise e
            
            await temp_client.disconnect()
            await event.respond(f"✅ **Success!** Account {phone} is now linked to the Sentinel fleet.")
        except Exception as e:
            await event.respond(f"❌ **Error:** {str(e)}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

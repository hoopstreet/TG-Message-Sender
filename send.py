import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

# Credentials
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
                    
                    supabase.table("message_campaign").update({
                        "status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()
                    }).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(240, 480))
            except: continue
        await asyncio.sleep(600)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel Elite v5.4.1**\n/status | /add_list | /edit_msg\n/schedule | /add_account | /pause")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = get_settings()
    leads = supabase.table("message_campaign").select("status", "updated_at").execute().data
    today = datetime.now(PHT).strftime('%Y-%m-%d')
    daily = sum(1 for x in leads if x['status'] == 'success' and x['updated_at'].startswith(today))
    pending = sum(1 for x in leads if x['status'] == 'pending')
    msg = f"📊 **Audit**\nList: {len(leads)} | Pend: {pending}\nDaily: {daily} | Accs: {len(glob.glob('*.session'))-1}\nSched: {'ON' if sets['is_sched_active'] else 'OFF'}"
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Paste New Promo Script:**")
        r = await conv.get_response()
        supabase.table("bot_settings").update({"current_promo_text": r.text}).eq("id", "production").execute()
        await event.respond("✅ **Updated.**")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste List (@, Link, or Name):**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        await event.respond(f"🔍 Filtering {len(found)} leads...")
        # Auto-detect duplicate and filter logic here...
        for u in found:
            supabase.table("message_campaign").upsert({"add_list": u, "status": "pending"}).execute()
        await event.respond(f"✅ Processed {len(found)} leads.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime, timedelta
from telethon import TelegramClient, events, errors
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

def get_settings():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

async def background_worker():
    while True:
        settings = get_settings()
        if not settings['is_sending_active']: break
        
        # Get pending leads from 'message_campaign' (column: add_list)
        lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
        if not lead_req.data: break
        lead = lead_req.data[0]

        # Seniority Rotation
        all_files = [f for f in glob.glob("*.session") if "bot.session" not in f]
        trusted = [f for f in all_files if (datetime.now() - datetime.fromtimestamp(os.path.getctime(f))) > timedelta(hours=WARMUP_HOURS)]
        if not trusted: break
        trusted.sort(key=os.path.getctime)
        s_file = trusted[0]

        try:
            async with TelegramClient(s_file.replace(".session",""), API_ID, API_HASH) as client:
                greet = random.choice(GREETINGS)
                msg = settings['current_promo_text'].replace("Hi,", f"{greet},")
                await client.send_message(lead['add_list'], msg)
                supabase.table("message_campaign").update({"status": "sent"}).eq("id", lead['id']).execute()
        except Exception:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()
        
        await asyncio.sleep(random.randint(150, 300))

    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    menu = ("👑 **Weightless Commander**\n\n/start - 👑 Guide\n/status - 📊 Stats\n/pause - ⏸️ Stop\n/add_list - 📂 List\n/edit_msg - 📝 Script\n/schedule - 📅 Schedule\n/add_account - 📱 Account")
    await event.respond(menu)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    leads = supabase.table("message_campaign").select("status").execute().data
    all_s = [f for f in glob.glob("*.session") if "bot.session" not in f]
    ready = [s for s in all_s if (datetime.now() - datetime.fromtimestamp(os.path.getctime(s))) > timedelta(hours=WARMUP_HOURS)]
    
    msg = (f"📊 **Tacloban HQ: Stats**\n"
           f"👥 Total: {len(leads)}\n"
           f"⏳ Pending: {sum(1 for x in leads if x['status'] == 'pending')}\n"
           f"📱 Ready Sessions: {len(ready)}\n"
           f"🔥 Warm-up: {len(all_s) - len(ready)}")
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Import New @Username List:**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', r.text)))
        new_entries = [{"add_list": u, "status": "pending"} for u in found]
        if new_entries: supabase.table("message_campaign").insert(new_entries).execute()
        await event.respond(f"✅ Added {len(new_entries)} unique leads.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Update Promotional Text:**")
        r = await conv.get_response()
        supabase.table("bot_settings").update({"current_promo_text": r.text}).eq("id", "production").execute()
        await event.respond("✅ **Promo Script Updated.**")

@bot.on(events.NewMessage(pattern='/pause'))
async def pause(event):
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Engine Halted.**")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(bot.run_until_disconnected())

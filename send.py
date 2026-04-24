import os, asyncio, random, glob, pytz, logging, re, base64
from datetime import datetime
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

try:
    API_ID = int(os.getenv("TELEGRAM_API_ID"))
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))
except Exception as e: print(f"⚠️ Connection Error: {e}")

def restore_sessions():
    try:
        res = supabase.table("saved_sessions").select("*").execute()
        for row in res.data:
            f_path = f"{row['phone_number']}.session"
            if not os.path.exists(f_path):
                with open(f_path, "wb") as f: f.write(base64.b64decode(row['session_data']))
    except: pass

async def global_worker():
    while True:
        try:
            sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
            if not sets['is_sending_active']:
                await asyncio.sleep(60); continue
            
            sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
            for s_file in sessions:
                s_name = s_file.replace(".session", "")
                today = datetime.now(PHT).strftime('%Y-%m-%d')
                sent_today = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute().count
                if sent_today >= 5: continue 

                lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
                if not lead_req.data: break
                lead = lead_req.data[0]
                
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey"])
                    msg = sets['current_promo_text'].replace("Hi,", f"{greet},")
                    await client.send_message(lead['add_list'], msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(180, 300))
        except: await asyncio.sleep(60)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 Sentinel v5.8.9 Online.")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    accs = len(glob.glob("*.session")) - 1
    await event.respond(f"📊 Accounts: {accs} | System: Online")

if __name__ == '__main__':
    restore_sessions()
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

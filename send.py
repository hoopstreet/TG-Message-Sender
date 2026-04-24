import os, asyncio, random, glob, pytz, logging, re, base64
from datetime import datetime
from telethon import TelegramClient, events, errors, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

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
                    await asyncio.sleep(random.randint(300, 600))
        except: await asyncio.sleep(60)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel Elite v5.9.0**\n/status | /add_list | /add_account | /pause")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    try:
        sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
        leads = supabase.table("message_campaign").select("status").execute().data
        pending = sum(1 for x in leads if x['status'] == 'pending')
        accs = len(glob.glob("*.session")) - 1
        await event.respond(f"📊 **Audit**\nPending: {pending}\nAccounts: {accs}\nEngine: {'RUNNING' if sets['is_sending_active'] else 'PAUSED'}")
    except Exception as e: await event.respond(f"❌ Status Error: {e}")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste Leads (@usernames or links):**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        new_leads = [{"add_list": u, "status": "pending"} for u in found if len(u) > 4]
        if new_leads: supabase.table("message_campaign").upsert(new_leads).execute()
        await event.respond(f"✅ Processed {len(found)} leads.")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Phone (+63...):**")
        phone = (await conv.get_response()).text.strip().replace(" ", "")
        s_name = f"session_{phone.replace('+', '')}"
        client = TelegramClient(s_name, API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **OTP:**")
            code = (await conv.get_response()).text
            await client.sign_in(phone, code)
            with open(f"{s_name}.session", "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                supabase.table("saved_sessions").upsert({"phone_number": s_name, "session_data": encoded}).execute()
            await event.respond(f"✅ Account {phone} Cloud-Synced.")
        except Exception as e: await event.respond(f"❌ Error: {e}")
        finally: await client.disconnect()

if __name__ == '__main__':
    restore_sessions()
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

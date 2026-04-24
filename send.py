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

MSG_LIMIT_PER_ACCOUNT = 5
WARMUP_HOURS = 24
GREETINGS = ["Hi", "Hello", "Hey", "Greetings", "Good day", "Hi there"]

def get_settings():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

async def global_worker():
    while True:
        settings = get_settings()
        if not settings['is_sending_active'] and not settings['is_sched_active']:
            await asyncio.sleep(60); continue

        all_s = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
        ready_sessions = [s for s in all_s if (datetime.now() - datetime.fromtimestamp(os.path.getctime(s))) > timedelta(hours=WARMUP_HOURS)]
        
        for s_file in ready_sessions:
            s_name = s_file.replace(".session", "")
            today_str = datetime.now(PHT).strftime('%Y-%m-%d')
            sent_today = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today_str).execute().count
            
            if sent_today >= MSG_LIMIT_PER_ACCOUNT: continue

            lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
            if not lead_req.data: break
            lead = lead_req.data[0]

            try:
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(GREETINGS)
                    final_msg = settings['current_promo_text'].replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                    await client.send_message(lead['add_list'], final_msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(180, 400))
            except Exception as e:
                supabase.table("message_campaign").update({"status": f"error: {str(e)[:20]}"}).eq("id", lead['id']).execute()
            
            if not get_settings()['is_sending_active'] and not get_settings()['is_sched_active']: break
        await asyncio.sleep(600)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Weightless Commander**\n\n/start - 👑 Guide\n/status - 📊 Stats\n/pause - ⏸️ Stop\n/add_list - 📂 List\n/edit_msg - 📝 Script\n/schedule - 📅 Schedule\n/add_account - 📱 Account")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = get_settings()
    leads = supabase.table("message_campaign").select("status", "updated_at").execute().data
    today = datetime.now(PHT).strftime('%Y-%m-%d')
    pending = sum(1 for x in leads if x['status'] == 'pending')
    daily_sent = sum(1 for x in leads if x['status'] == 'success' and x['updated_at'].startswith(today))
    active_s = [s for s in glob.glob("*.session") if "bot.session" not in s]
    
    msg = (f"📊 **Global Audit: {datetime.now(PHT).strftime('%Y-%m-%d %H:%M')}**\n"
           f"📂 Add List: {len(leads)} | ⏳ Pend: {pending}\n"
           f"✅ Total Sent: {sum(1 for x in leads if x['status'] == 'success')}\n"
           f"📅 Daily: {daily_sent} | 📱 Accounts: {len(active_s)}\n"
           f"🛠️ Sched: {'ON' if sets['is_sched_active'] else 'OFF'} | 🚀 Engine: {'RUNNING' if sets['is_sending_active'] else 'HALTED'}")
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/pause'))
async def pause(event):
    supabase.table("bot_settings").update({"is_sending_active": False, "is_sched_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Engine & Schedule Halted.**")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste List:**"); r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        existing = [x['add_list'] for x in supabase.table("message_campaign").select("add_list").execute().data]
        valid_entries = []
        await event.respond(f"🔍 **Sentinel Filtering {len(found)} leads...**")
        all_s = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
        async with TelegramClient(all_s[0].replace(".session",""), API_ID, API_HASH) as client:
            for u in found:
                if u in existing: continue
                try:
                    await asyncio.sleep(1.2); full = await client(functions.users.GetFullUserRequest(id=u))
                    user = full.users[0]
                    if user.deleted or user.bot: continue
                    status = user.status
                    if any([isinstance(status, types.UserStatusOnline), isinstance(status, types.UserStatusRecently), isinstance(status, types.UserStatusLastWeek)]):
                        valid_entries.append({"add_list": u, "status": "pending"})
                except Exception: continue
        if valid_entries: supabase.table("message_campaign").insert(valid_entries).execute()
        await event.respond(f"✅ Added {len(valid_entries)} verified leads.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

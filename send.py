import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime, timedelta
from telethon import TelegramClient, events, errors, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

# Credentials from Northflank Secrets
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
            await asyncio.sleep(60); continue

        sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
        for s_file in sessions:
            s_name = s_file.replace(".session", "")
            today = datetime.now(PHT).strftime('%Y-%m-%d')
            
            # 5-Message Limit Check
            sent_today = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute().count
            if sent_today >= 5: continue

            # Anti-Duplicate Lead Pick
            lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
            if not lead_req.data: break
            lead = lead_req.data[0]

            try:
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Greetings", "Good day"])
                    final_msg = sets['current_promo_text'].replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                    
                    await client.send_message(lead['add_list'], final_msg)
                    
                    supabase.table("message_campaign").update({
                        "status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()
                    }).eq("id", lead['id']).execute()
                    
                    # Tactical Wait (3-7 minutes)
                    await asyncio.sleep(random.randint(180, 420))
            except Exception as e:
                supabase.table("message_campaign").update({"status": f"err: {str(e)[:20]}"}).eq("id", lead['id']).execute()
        
        # If all hit limit, sleep until next hour check
        await asyncio.sleep(600)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = get_settings()
    leads = supabase.table("message_campaign").select("status", "updated_at").execute().data
    today = datetime.now(PHT).strftime('%Y-%m-%d')
    
    daily = sum(1 for x in leads if x['status'] == 'success' and x['updated_at'].startswith(today))
    pending = sum(1 for x in leads if x['status'] == 'pending')
    
    msg = (f"📊 **Sentinel Audit: {datetime.now(PHT).strftime('%Y-%m-%d %H:%M')}**\n"
           f"📂 Total List: {len(leads)} | ⏳ Pend: {pending}\n"
           f"✅ Daily: {daily} | 📱 Accs: {len(glob.glob('*.session'))-1}\n"
           f"🚀 Engine: {'RUNNING' if sets['is_sending_active'] else 'HALTED'}")
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste List (@, Links, or Names):**"); r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        existing = [x['add_list'] for x in supabase.table("message_campaign").select("add_list").execute().data]
        valid = []
        
        await event.respond(f"🔍 Filtering {len(found)} leads (Active < 7d)...")
        async with TelegramClient(sorted(glob.glob("*.session"))[0].replace(".session",""), API_ID, API_HASH) as client:
            for u in found:
                if u in existing: continue
                try:
                    await asyncio.sleep(1.1)
                    u_info = await client(functions.users.GetFullUserRequest(id=u))
                    user = u_info.users[0]
                    if user.bot or user.deleted: continue
                    
                    status = user.status
                    if any([isinstance(status, (types.UserStatusOnline, types.UserStatusRecently, types.UserStatusLastWeek))]):
                        valid.append({"add_list": u, "status": "pending"})
                except: continue
        
        if valid: supabase.table("message_campaign").insert(valid).execute()
        await event.respond(f"✅ Verified & Added {len(valid)} leads.")

@bot.on(events.NewMessage(pattern='/pause'))
async def pause(event):
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **All cycles halted.**")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

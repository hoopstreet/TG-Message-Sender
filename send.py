import os, asyncio, random, glob, pytz, logging, re, base64
from datetime import datetime
from telethon import TelegramClient, events, functions, types, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

# Restoration Logic
def restore_sessions():
    res = supabase.table("saved_sessions").select("*").execute()
    for row in res.data:
        file_path = f"{row['phone_number']}.session"
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(row['session_data']))

def get_settings():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

restore_sessions()

# Worker Logic
async def global_worker():
    while True:
        sets = get_settings()
        if not sets['is_sched_active'] and not sets['is_sending_active']:
            await asyncio.sleep(30); continue
        
        sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
        for s_file in sessions:
            s_name = s_file.replace(".session", "")
            today = datetime.now(PHT).strftime('%Y-%m-%d')
            sent_today = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute().count
            if sent_today >= 5: continue 

            lead = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
            if not lead.data: break
            
            # Skip generic words if they accidentally stayed in DB
            target = lead.data[0]['add_list']
            if len(target) < 5 or target.lower() in ['apply', 'target', 'launch', 'marketing']:
                supabase.table("message_campaign").delete().eq("id", lead.data[0]['id']).execute()
                continue

            try:
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Greetings"])
                    msg = sets['current_promo_text'].replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                    await client.send_message(target, msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead.data[0]['id']).execute()
                    await asyncio.sleep(random.randint(300, 600))
            except: continue
        await asyncio.sleep(1800)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list_cmd(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste Leads:**")
        r = await conv.get_response()
        # Regex: Only captures actual usernames, ignores short common words
        found = list(set(re.findall(r'(?:https?://t\.me/|@)([a-zA-Z0-9_]{5,32})', r.text)))
        existing = [x['add_list'] for x in supabase.table("message_campaign").select("add_list").execute().data]
        
        # Filter out common script words
        stop_words = ['apply', 'target', 'launch', 'marketing', 'seeking', 'platform', 'branding', 'contact']
        new_leads = [{"add_list": u, "status": "pending"} for u in found if u not in existing and u.lower() not in stop_words]
        
        if new_leads: supabase.table("message_campaign").insert(new_leads).execute()
        await event.respond(f"✅ Filtered & Added {len(new_leads)} real leads.")

@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    sets = get_settings()
    leads = supabase.table("message_campaign").select("status").execute().data
    pending = sum(1 for x in leads if x['status'] == 'pending')
    await event.respond(f"📊 **Audit**\nPending: {pending}\nAccounts: {len(glob.glob('*.session'))-1}\nSched: {'ON' if sets['is_sched_active'] else 'OFF'}")

# Re-including missing triggers
@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    await event.respond("👑 **Sentinel v5.8.1**\n/status | /add_list | /add_account")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account_cmd(event):
    # (Existing Interactive Login Logic goes here)
    await event.respond("📱 Interactive Login Active. Provide number:")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

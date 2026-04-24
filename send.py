import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime, timedelta
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

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Import New List:**\n(URL, @, or Raw Text)")
        r = await conv.get_response()
        
        # Working Username Format Converter
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        existing = [x['add_list'] for x in supabase.table("message_campaign").select("add_list").execute().data]
        valid = []
        
        await event.respond(f"🔍 Sentinel filtering {len(found)} leads...")
        
        s_acc = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])[0].replace(".session","")
        async with TelegramClient(s_acc, API_ID, API_HASH) as client:
            for u in found:
                if u in existing: continue 
                try:
                    await asyncio.sleep(1.2)
                    u_info = await client(functions.users.GetFullUserRequest(id=u))
                    user = u_info.users[0]
                    if user.bot or user.deleted: continue
                    
                    if isinstance(user.status, (types.UserStatusOnline, types.UserStatusRecently, types.UserStatusLastWeek)):
                        valid.append({"add_list": u, "status": "pending"})
                except: continue
        
        if valid: supabase.table("message_campaign").insert(valid).execute()
        await event.respond(f"✅ Added {len(valid)} verified leads.")

from handlers import *

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

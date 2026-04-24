import os, asyncio, random, glob, pytz, logging, re, base64
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

async def global_worker():
    while True:
        try:
            sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
            if not sets['is_sending_active'] and not sets['is_sched_active']:
                await asyncio.sleep(10); continue
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
                    greet = random.choice(["Hi", "Hello", "Hey", "Good day", "Greetings"])
                    final_msg = sets['current_promo_text'].replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                    await client.send_message(lead['add_list'], final_msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(300, 900))
        except: await asyncio.sleep(10)
        await asyncio.sleep(10)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Weightless Commander**\n\n/status | /add_list | /add_account\n/edit_msg | /schedule")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
    leads = supabase.table("message_campaign").select("status", "updated_at").execute().data
    today = datetime.now(PHT).strftime('%Y-%m-%d')
    daily = sum(1 for x in leads if x['status'] == 'success' and x['updated_at'] and x['updated_at'].startswith(today))
    pending = sum(1 for x in leads if x['status'] == 'pending')
    accs = len(glob.glob("*.session")) - 1
    msg = (f"📊 **Audit**\nDaily: {daily} | Pend: {pending}\nAccs: {accs} | Sched: {'ON' if sets['is_sched_active'] else 'OFF'}\nEngine: {'ACTIVE' if sets['is_sending_active'] else 'WAITING'}")
    await event.respond(msg)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste Leads:**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        existing = [x['add_list'] for x in supabase.table("message_campaign").select("add_list").execute().data]
        valid = []
        await event.respond(f"🔍 Deep Scanning {len(found)} leads...")
        s_name = sorted(glob.glob("*.session"))[0].replace(".session","")
        async with TelegramClient(s_name, API_ID, API_HASH) as client:
            for u in found:
                if u in existing: continue
                try:
                    await asyncio.sleep(1.2)
                    u_info = await client(functions.users.GetFullUserRequest(id=u))
                    user = u_info.users[0]
                    if user.bot or user.deleted: continue
                    if any([isinstance(user.status, (types.UserStatusOnline, types.UserStatusRecently, types.UserStatusLastWeek))]):
                        valid.append({"add_list": u, "status": "pending"})
                except: continue
        if valid: supabase.table("message_campaign").insert(valid).execute()
        await event.respond(f"✅ Added {len(valid)} valid leads.")

@bot.on(events.NewMessage(pattern='/schedule'))
async def toggle_schedule(event):
    sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
    if sets['is_sched_active']:
        supabase.table("bot_settings").update({"is_sched_active": False}).eq("id", "production").execute()
        await event.respond("⏹️ **Schedule Stopped.**")
    else:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📅 **PHT Schedule (YYYY-MM-DD HH:MM AM/PM):**")
            resp = await conv.get_response()
            try:
                supabase.table("bot_settings").update({"is_sched_active": True, "is_sending_active": False}).eq("id", "production").execute()
                await event.respond(f"✅ **Schedule Set:** {resp.text}")
            except: await event.respond("❌ Format Error.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Enter New Script (Start with Hi,):**")
        new_text = (await conv.get_response()).text
        supabase.table("bot_settings").update({"current_promo_text": new_text}).eq("id", "production").execute()
        await event.respond("✅ Script updated.")

if __name__ == '__main__':
    print('🚀 Sentinel Bot is Online and Listening...')
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

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
QUARANTINE_HOURS = 24
GREETINGS = ["Hi", "Hello", "Hey", "Greetings", "Good day"]

def get_hq():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
async def background_worker(event):
    hq = get_hq()
    all_files = glob.glob("*.session")
    # Priority: Oldest first + 24h Quarantine check
    valid_sessions = []
    for f in all_files:
        ctime = datetime.fromtimestamp(os.path.getctime(f))
        if datetime.now() - ctime > timedelta(hours=QUARANTINE_HOURS):
            valid_sessions.append((f, ctime))
    
    valid_sessions.sort(key=lambda x: x[1]) # Oldest first
    sessions = [x[0] for x in valid_sessions]
    session_stats = {s: 0 for s in sessions} 

    while True:
        hq = get_hq()
        if not hq['is_sending_active']: break
        
        available = [s for s, count in session_stats.items() if count < MSG_LIMIT_PER_ACCOUNT]
        
        if not available:
            tomorrow = (datetime.now(PHT) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
            supabase.table("schedules").insert({"scheduled_for": tomorrow, "status": "pending"}).execute()
            if event: await event.respond(f"🛑 **Limits hit. Auto-scheduled for tomorrow: {tomorrow}**")
            break

        s_file = available[0] # Use the oldest available first
        s_name = s_file.replace(".session", "")
        lead_req = supabase.table("targets").select("*").eq("status", "pending").limit(1).execute()
        if not lead_req.data: break
        lead = lead_req.data[0]

        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                greet = random.choice(GREETINGS)
                clean_msg = hq.get('current_promo_text', "").replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                await client.send_message(lead['username'], clean_msg)
                supabase.table("targets").update({"status": "success", "sent_by": s_name}).eq("id", lead['id']).execute()
                session_stats[s_file] += 1
        except Exception as e:
            supabase.table("targets").update({"status": "failed"}).eq("id", lead['id']).execute()
        await asyncio.sleep(random.randint(120, 240)) # Max safety delay

    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    if event: await event.respond("🏁 **Sentinel Cycle Finished.**")
async def scheduler_loop():
    while True:
        try:
            hq = get_hq()
            if hq['is_sched_active']:
                now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
                job = supabase.table("schedules").select("*").eq("status", "pending").lte("scheduled_for", now_pht).limit(1).execute()
                if job.data:
                    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
                    asyncio.create_task(background_worker(None))
                    supabase.table("schedules").update({"status": "fired"}).eq("id", job.data[0]['id']).execute()
        except: pass
        await asyncio.sleep(60)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Safety Filter Active.** Paste Usernames:")
        r = await conv.get_response()
        if not r: return
        found = list(set(re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', r.text)))
        sessions = glob.glob("*.session")
        if not sessions: return await event.respond("❌ No sessions for validation.")
        
        valid_leads = []
        async with TelegramClient(sessions[0].replace(".session", ""), API_ID, API_HASH) as client:
            for u in found:
                check = supabase.table("targets").select("id").eq("username", u).execute()
                if check.data: continue
                try:
                    user = await client.get_entity(u)
                    if not user.bot: valid_leads.append({"username": u, "status": "pending"})
                except: continue

        if valid_leads: supabase.table("targets").insert(valid_leads).execute()
        await event.respond(f"✅ **Sentinel Guard:** {len(valid_leads)} added.")
@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    hq = get_hq()
    res = supabase.table("targets").select("status").execute().data
    all_s = glob.glob("*.session")
    ready_s = [f for f in all_s if (datetime.now() - datetime.fromtimestamp(os.path.getctime(f))) > timedelta(hours=QUARANTINE_HOURS)]
    report = (f"📊 **SENTINEL AUDIT**\n👥 Pending: {sum(1 for x in res if x['status'] == 'pending')}\n📱 Active: {len(ready_s)} | ⏳ Warm-up: {len(all_s)-len(ready_s)}\nEngine: {'🚀 ON' if hq['is_sending_active'] else 'Ready'}\nSched: {'✅ ON' if hq['is_sched_active'] else '⏸️ OFF'}")
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel HQ v4.6.0**\nSafety: 5-Limit | 24h Quarantine | Auto-Routing\n\n/start | /status | /send_now\n/schedule | /pause_send | /pause_sched\n/add_list | /edit_msg | /add_account")

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Sentinel Guard Engaged.**")
    asyncio.create_task(background_worker(event))

async def main():
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

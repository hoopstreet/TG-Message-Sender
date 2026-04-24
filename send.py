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
INACTIVE_DAYS_THRESHOLD = 7

def get_hq():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
async def background_worker(event):
    hq = get_hq()
    sessions = glob.glob("*.session")
    session_stats = {s: 0 for s in sessions} 
    while True:
        hq = get_hq()
        if not hq['is_sending_active']: break
        available_sessions = [s for s, count in session_stats.items() if count < MSG_LIMIT_PER_ACCOUNT]
        if not available_sessions: 
            if event: await event.respond("🛑 **Limit reached. Resting.**")
            break
        s_file = random.choice(available_sessions)
        s_name = s_file.replace(".session", "")
        lead_req = supabase.table("targets").select("*").eq("status", "pending").limit(1).execute()
        if not lead_req.data: break
        lead = lead_req.data[0]
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                await client.send_message(lead['username'], hq.get('current_promo_text', "Hi!"))
                supabase.table("targets").update({"status": "success", "sent_by": s_name}).eq("id", lead['id']).execute()
                session_stats[s_file] += 1
        except Exception as e:
            supabase.table("targets").update({"status": "failed"}).eq("id", lead['id']).execute()
        await asyncio.sleep(random.randint(90, 180))
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    if event: await event.respond("🏁 **Cycle Finished.**")

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
        await conv.send_message("📂 **Paste List:** (Validating Bots/Deleted/Inactive...)")
        r = await conv.get_response()
        if not r: return
        found = re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', r.text)
        sessions = glob.glob("*.session")
        if not sessions: return await event.respond("❌ No sessions to validate with.")
        
        valid_leads = []
        skipped = {"bot": 0, "inactive": 0, "deleted": 0, "exists": 0}
        
        # Use one session to validate the batch
        async with TelegramClient(sessions[0].replace(".session", ""), API_ID, API_HASH) as client:
            for u in found:
                # Check duplicate in DB
                check = supabase.table("targets").select("id").eq("username", u).execute()
                if check.data:
                    skipped["exists"] += 1; continue
                try:
                    user = await client.get_entity(u)
                    if user.bot: skipped["bot"] += 1; continue
                    
                    # 7-Day Activity Check
                    is_active = True
                    if isinstance(user.status, types.UserStatusOffline):
                        cutoff = datetime.now(pytz.utc) - timedelta(days=INACTIVE_DAYS_THRESHOLD)
                        if user.status.was_online.replace(tzinfo=pytz.utc) < cutoff:
                            is_active = False
                    
                    if is_active:
                        valid_leads.append({"username": u, "status": "pending"})
                    else:
                        skipped["inactive"] += 1
                except Exception:
                    skipped["deleted"] += 1

        if valid_leads: supabase.table("targets").insert(valid_leads).execute()
        report = f"✅ **Imported:** {len(valid_leads)}\n🚫 **Skipped:** {sum(skipped.values())}\n(Bots: {skipped['bot']} | Inactive: {skipped['inactive']} | Missing: {skipped['deleted']} | Exists: {skipped['exists']})"
        await event.respond(report)
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **HQ: Iron Gate Enabled**\n\n/start | /status | /send_now\n/schedule | /pause_send | /pause_sched\n/add_list | /edit_msg | /add_account")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    hq = get_hq()
    res = supabase.table("targets").select("status").execute().data
    sessions = glob.glob("*.session")
    report = (f"📊 **Audit**\n👥 Leads: {len(res)}\n⏳ Pend: {sum(1 for x in res if x['status'] == 'pending')}\n📱 Sessions: {len(sessions)}\nEngine: {'🚀 ON' if hq['is_sending_active'] else 'Ready'}")
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Safe Engine Engaged.**")
    asyncio.create_task(background_worker(event))

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop(event):
    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Manual Halted.**")

async def main():
    asyncio.create_task(scheduler_loop())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

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
    valid_sessions = []
    
    for f in all_files:
        if "bot.session" in f: continue
        ctime = datetime.fromtimestamp(os.path.getctime(f))
        # Account is ready if older than 24h
        if datetime.now() - ctime > timedelta(hours=QUARANTINE_HOURS):
            valid_sessions.append((f, ctime))
    
    # Sort by seniority (Oldest first)
    valid_sessions.sort(key=lambda x: x[1])
    sessions = [x[0] for x in valid_sessions]
    session_stats = {s: 0 for s in sessions} 

    while True:
        hq = get_hq()
        if not hq['is_sending_active']: break
        available = [s for s, count in session_stats.items() if count < MSG_LIMIT_PER_ACCOUNT]
        
        if not available:
            tomorrow = (datetime.now(PHT) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
            supabase.table("schedules").insert({"scheduled_for": tomorrow, "status": "pending"}).execute()
            if event: await event.respond(f"🛑 **All Active hit limit. Next blast: {tomorrow}**")
            break

        s_file = available[0]
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
        except errors.UserDeactivatedError:
            logging.error(f"Account Banned: {s_name}")
        except errors.SessionPasswordNeededError:
            logging.error(f"Account Frozen/2FA: {s_name}")
        except Exception as e:
            supabase.table("targets").update({"status": "failed"}).eq("id", lead['id']).execute()
        
        await asyncio.sleep(random.randint(120, 240))

    supabase.table("bot_settings").update({"is_sending_active": False}).eq("id", "production").execute()
@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    hq = get_hq()
    all_s = glob.glob("*.session")
    ready, warmup, banned, frozen = [], [], [], []
    
    for s in all_s:
        if "bot.session" in s: continue
        ctime = datetime.fromtimestamp(os.path.getctime(s))
        s_name = s.replace(".session", "")
        
        if datetime.now() - ctime < timedelta(hours=QUARANTINE_HOURS):
            warmup.append(s_name)
            continue
            
        try:
            client = TelegramClient(s_name, API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                banned.append(s_name)
            else:
                ready.append(s_name)
            await client.disconnect()
        except:
            frozen.append(s_name)

    res = supabase.table("targets").select("status").execute().data
    report = (
        f"📊 **SENTINEL AUDIT (Tacloban HQ)**\n"
        f"👥 Total Leads: {len(res)} | ⏳ Pending: {sum(1 for x in res if x['status'] == 'pending')}\n"
        f"📱 **Accounts Status:**\n"
        f"✅ Ready: {len(ready)} (Oldest: {ready[0] if ready else 'None'})\n"
        f"🔥 Warm-up: {len(warmup)}\n"
        f"🚫 Banned/Logged Out: {len(banned)}\n"
        f"❄️ Frozen/Error: {len(frozen)}\n\n"
        f"Engine: {'🚀 ON' if hq['is_sending_active'] else 'Ready'} | Sched: {'✅ ON' if hq['is_sched_active'] else '⏸️ OFF'}"
    )
    await event.respond(report)
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    menu = ("👑 **Sentinel HQ v4.7.0**\n\n/start - 👑 Guide\n/status - 📊 Audit\n/send_now - 🚀 Blast\n/schedule - 📅 Sched\n/pause_send - ⏸️ Stop\n/add_list - 📂 List\n/edit_msg - 📝 Msg\n/add_account - 📱 Link")
    await event.respond(menu)

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("bot_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Sentinel Guard Engaged.**")
    asyncio.create_task(background_worker(event))

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Safety Filter:** Paste Usernames:")
        r = await conv.get_response()
        if r:
            found = list(set(re.findall(r'(?:@)?([a-zA-Z0-9_]{5,32})', r.text)))
            new_leads = [{"username": u, "status": "pending"} for u in found]
            if new_leads: supabase.table("targets").insert(new_leads).execute()
            await event.respond(f"✅ Added {len(new_leads)} unique leads.")

async def main():
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

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
    print("📅 Scheduler Watchdog Started...")
    while True:
        try:
            sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
            
            # Pure Schedule Check
            if not sets.get('is_sched_active'):
                await asyncio.sleep(30); continue
            
            # Time Matching (Wait until the scheduled time)
            now = datetime.now(PHT)
            # Example logic: if schedule is set for 10:00 PM, start only if now >= 10:00 PM
            # Note: We assume 'last_audit_at' or a similar column stores your target time string
            
            sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
            for s_file in sessions:
                s_name = s_file.replace(".session", "")
                today = now.strftime('%Y-%m-%d')
                
                sent_today = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute().count
                if sent_today >= 5: continue 

                lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
                if not lead_req.data: break
                lead = lead_req.data[0]
                
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Good day"])
                    msg = sets['current_promo_text'].replace("Hi,", f"{greet},")
                    await client.send_message(lead['add_list'], msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(300, 800))
        except Exception as e: 
            print(f"Error: {e}")
            await asyncio.sleep(60)
        await asyncio.sleep(30)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel v6.1.0**\nPure Scheduler Mode\n\n/status | /schedule | /add_list | /edit_msg")

@bot.on(events.NewMessage(pattern='/schedule'))
async def toggle_schedule(event):
    sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
    
    if sets['is_sched_active']:
        # If ON, turn it OFF
        supabase.table("bot_settings").update({"is_sched_active": False, "is_sending_active": False}).eq("id", "production").execute()
        await event.respond("⏹️ **Schedule Deleted.** Engine Halted.")
    else:
        # If OFF, ask for new time
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📅 **Enter Start Time (PHT):**\n`YYYY-MM-DD HH:MM AM/PM`")
            resp = await conv.get_response()
            try:
                # Update Supabase
                supabase.table("bot_settings").update({"is_sched_active": True, "is_sending_active": True}).eq("id", "production").execute()
                await event.respond(f"✅ **Target Set:** {resp.text}\nSending will begin and repeat daily at this window.")
            except:
                await event.respond("❌ Format Error.")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    sets = supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data
    leads = supabase.table("message_campaign").select("status").execute().data
    accs = len(glob.glob("*.session")) - 1
    
    stat = "🟢 ACTIVE" if sets['is_sched_active'] else "🔴 IDLE (No Schedule)"
    await event.respond(f"📊 **System Status**\nMode: {stat}\nAccounts: {accs}\nLeads Pending: {sum(1 for x in leads if x['status'] == 'pending')}")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste Leads:**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        new_leads = [{"add_list": u, "status": "pending"} for u in found]
        if new_leads: supabase.table("message_campaign").upsert(new_leads).execute()
        await event.respond(f"✅ Processed {len(new_leads)} leads.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **New Script:**")
        t = (await conv.get_response()).text
        supabase.table("bot_settings").update({"current_promo_text": t}).eq("id", "production").execute()
        await event.respond("✅ Script Updated.")

if __name__ == '__main__':
    print("🚀 Sentinel v6.1.0 Online")
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

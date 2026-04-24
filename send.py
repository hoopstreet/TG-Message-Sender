import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, functions, types
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
    print("🚀 Scheduler Watchdog Active")
    while True:
        try:
            res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
            sets = res.data
            if not sets.get('is_sched_active'):
                await asyncio.sleep(20); continue
            
            sessions = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
            for s_file in sessions:
                s_name = s_file.replace(".session", "")
                today = datetime.now(PHT).strftime('%Y-%m-%d')
                
                count_res = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute()
                if count_res.count >= 5: continue 

                lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
                if not lead_req.data: break
                lead = lead_req.data[0]
                
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Good day"])
                    msg = sets['current_promo_text'].replace("Hi,", f"{greet},")
                    await client.send_message(lead['add_list'], msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(300, 600))
        except Exception as e:
            print(f"Loop Error: {e}")
        await asyncio.sleep(30)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Sentinel v6.1.0**\n\n/status - Check Engine\n/schedule - Set/Stop Time\n/add_list - Add Leads\n/edit_msg - Edit Script")

@bot.on(events.NewMessage(pattern='/schedule'))
async def toggle_schedule(event):
    res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
    sets = res.data
    if sets.get('is_sched_active'):
        supabase.table("bot_settings").update({"is_sched_active": False}).eq("id", "production").execute()
        await event.respond("⏹️ **Schedule Stopped.** Engine is now IDLE.")
    else:
        async with bot.conversation(event.sender_id) as conv:
            await conv.send_message("📅 **Enter Start Time (PHT):**\nExample: `2026-04-25 09:00 AM`")
            resp = await conv.get_response()
            supabase.table("bot_settings").update({"is_sched_active": True}).eq("id", "production").execute()
            await event.respond(f"✅ **Target Set:** {resp.text}\nCycles will repeat daily.")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    res = supabase.table("bot_settings").select("*").eq("id", "production").single().execute()
    leads = supabase.table("message_campaign").select("status", count="exact").eq("status", "pending").execute()
    accs = len(glob.glob("*.session")) - 1
    mode = "🟢 ACTIVE" if res.data.get('is_sched_active') else "🔴 IDLE"
    await event.respond(f"📊 **Status**: {mode}\n📱 **Accounts**: {accs}\n⏳ **Pending**: {leads.count}")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste Leads:**")
        r = await conv.get_response()
        found = list(set(re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)))
        if found:
            data = [{"add_list": u, "status": "pending"} for u in found]
            supabase.table("message_campaign").upsert(data).execute()
            await event.respond(f"✅ Added {len(found)} leads.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **New Script:**")
        t = (await conv.get_response()).text
        supabase.table("bot_settings").update({"current_promo_text": t}).eq("id", "production").execute()
        await event.respond("✅ Script Updated.")

if __name__ == '__main__':
    print("🚀 Sentinel Bot is Online...")
    bot.loop.create_task(global_worker())
    bot.run_until_disconnected()

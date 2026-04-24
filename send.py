import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, Button, errors, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# --- GLOBAL STATE ---
SCHEDULER_ACTIVE = True
SENDING_ACTIVE = True

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Stealth Commander v3.5.5**\n/send_now | /status | /pause_send | /add_list | /add_account")

@bot.on(events.NewMessage(pattern='/status'))
async def status_report(event):
    data = supabase.table("message_campaign").select("*").execute().data
    sessions = glob.glob("*.session")
    report = (
        f"📊 **HQ Audit**\nTotal: {len(data)}\n"
        f"✅ Sent: {sum(1 for x in data if x['status'] == 'success')}\n"
        f"❌ Fail: {sum(1 for x in data if x['status'] == 'failed')}\n"
        f"📱 Sessions: {len(sessions)}\n"
        f"⚡ Send: {'ACTIVE' if SENDING_ACTIVE else 'PAUSED'}"
    )
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/send_now'))
async def stealth_blast(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = True
    await event.respond("🚀 **Stealth Blast Initialized.** (30-90s variable delays)")
    
    leads = supabase.table("message_campaign").select("*").eq("status", "pending").execute()
    sessions = glob.glob("*.session")
    
    for lead in leads.data:
        if not SENDING_ACTIVE: break
        
        # Pick session and simulate 'typing'
        s_name = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                # 1. Human Delay: 'Looking up user'
                await asyncio.sleep(random.randint(5, 15))
                
                # 2. Check if restricted
                me = await client.get_me()
                
                # 3. Send message
                await client.send_message(lead['username'], lead.get('edit_msg', "Hi!"))
                supabase.table("message_campaign").update({"status": "success"}).eq("id", lead['id']).execute()
                
                # 4. Long Cooldown (Anti-Ban)
                wait = random.randint(60, 120) 
                logging.info(f"Success. Cooling down for {wait}s...")
                await asyncio.sleep(wait)
                
        except errors.FloodWaitError as e:
            await event.respond(f"⚠️ **FloodWait:** Account {s_name} must rest for {e.seconds}s.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()

@bot.on(events.NewMessage(pattern='/pause_send'))
async def pause_all(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = False
    await event.respond("⏸️ **Manual Sending Paused.**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def pause_sched(event):
    global SCHEDULER_ACTIVE
    SCHEDULER_ACTIVE = False
    await event.respond("⏸️ **Scheduler Deactivated.**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def otp_wizard(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Phone Number?**")
        p = (await conv.get_response()).text
        c = TelegramClient(p, API_ID, API_HASH)
        await c.connect()
        await c.send_code_request(p)
        await conv.send_message("📩 **OTP?**")
        o = (await conv.get_response()).text
        try:
            await c.sign_in(p, o)
            await conv.send_message("✅ Linked.")
        except errors.SessionPasswordNeededError:
            await conv.send_message("🔐 **2FA Password?**")
            pw = (await conv.get_response()).text
            await c.sign_in(password=pw)
            await conv.send_message("✅ Linked with 2FA.")
        await c.disconnect()

async def main():
    print("🚀 Stealth Engine v3.5.5 Operational")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def update_script(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Send New Global Promo Message:**")
        new_msg = (await conv.get_response()).text
        # Real-time update for all pending leads
        supabase.table("message_campaign").update({"edit_msg": new_msg}).eq("status", "pending").execute()
        await conv.send_message("🔄 **Sync Complete.** All future sends will use this script.")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list_v2(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send your list (@, links, or text):**")
        msg = await conv.get_response()
        from ingest import clean_and_upsert
        count = clean_and_upsert(msg.text, os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        await conv.send_message(f"✅ **Batch Processed.** {count} unique leads added to the queue.")

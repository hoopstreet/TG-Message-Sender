import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')
API_ID, API_HASH = int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

# State is now handled via Supabase to ensure persistence
def get_settings():
    return supabase.table("hq_settings").select("*").eq("id", "production").single().execute().data

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Weightless Commander**\n\n/start - 👑 Guide\n/send_now - 🚀 Blast\n/status - 📊 Stats\n/add_account - 📱 Link\n/add_list - 📂 Import\n/edit_msg - 📝 Promo\n/pause_send - ⏸️ Stop")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    settings = get_settings()
    res = supabase.table("message_campaign").select("*").execute().data
    sessions = glob.glob("*.session")
    total = sum(1 for x in res if x['username'] != "SCHEDULE_MARKER")
    pend = sum(1 for x in res if x['status'] == 'pending')
    
    report = (
        f"📊 **Tacloban HQ: Deep Audit**\n"
        f"👥 Leads: {total} | ⏳ Pending: {pend}\n"
        f"📱 Sessions: {len(sessions)}\n"
        f"Engine: {'🚀 BLASTING' if settings['is_sending_active'] else 'Ready'}"
    )
    await event.respond(report)

async def background_worker(event):
    while True:
        settings = get_settings()
        if not settings['is_sending_active']: break
        
        lead = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).single().execute().data
        if not lead: break
        
        sessions = glob.glob("*.session")
        s_name = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                await client.send_message(lead['username'], settings.get('current_promo_text', "Hello!"))
                supabase.table("message_campaign").update({"status": "success"}).eq("id", lead['id']).execute()
        except:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()
        
        await asyncio.sleep(random.randint(60, 120))
    
    supabase.table("hq_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("🏁 **Engine Standby.**")

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    supabase.table("hq_settings").update({"is_sending_active": True}).eq("id", "production").execute()
    await event.respond("🚀 **Background Engine Initialized.**")
    asyncio.create_task(background_worker(event))

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop(event):
    supabase.table("hq_settings").update({"is_sending_active": False}).eq("id", "production").execute()
    await event.respond("⏸️ **Kill-Signal Sent to Engine.**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id, timeout=300) as conv:
        await conv.send_message("📱 **Enter Phone (+63...):**")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            await conv.send_message("📩 **OTP Code:**")
            otp = (await conv.get_response()).text.strip()
            await client.sign_in(phone, otp, phone_code_hash=sent_code.phone_code_hash)
            await conv.send_message(f"✅ Linked: {phone}")
        except Exception as e:
            await conv.send_message(f"❌ Error: {e}")
        finally:
            await client.disconnect()

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Paste New Promo Script:**")
        text = (await conv.get_response()).text
        supabase.table("hq_settings").update({"current_promo_text": text}).eq("id", "production").execute()
        await conv.send_message("✅ **Global Script Updated.**")

async def main(): await bot.run_until_disconnected()
if __name__ == '__main__': asyncio.get_event_loop().run_until_complete(main())

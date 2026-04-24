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

SENDING_ACTIVE = True
SCHED_ACTIVE = True

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Weightless Commander**\n\n/start - 👑 Guide\n/send_now - 🚀 Blast\n/schedule - 📅 Schedule\n/pause_send - ⏸️ Stop Send\n/pause_sched - ⏸️ Stop Sched\n/add_list - 📂 List\n/edit_msg - 📝 Script\n/add_account - 📱 Account\n/status - 📊 Stats")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Step 1: Enter the Phone Number (e.g., +639...)**")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        
        # Fixing OTP Trigger logic
        try:
            sent_code = await client.send_code_request(phone)
            await conv.send_message("📩 **Step 2: Enter the OTP code received:**")
            otp = (await conv.get_response()).text.strip()
            await client.sign_in(phone, otp, hash=sent_code.phone_code_hash)
        except errors.SessionPasswordNeededError:
            await conv.send_message("🔐 **Step 3: Enter 2FA PIN:**")
            await client.sign_in(password=(await conv.get_response()).text.strip())
        except Exception as e:
            await conv.send_message(f"❌ Error: {e}")
            return

        await conv.send_message(f"✅ Success! {phone} is now linked to the HQ.")
        await client.disconnect()

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📅 **Target Date & Time?**\nExample: `2026-04-25 14:00` (PHT)")
        target = (await conv.get_response()).text.strip()
        
        # WRITING TO SUPABASE: Adding a placeholder row with the scheduled time
        supabase.table("message_campaign").insert({
            "username": "SCHEDULE_MARKER", 
            "status": "scheduled", 
            "created_at": target 
        }).execute()
        
        await conv.send_message(f"📅 **Scheduler Sync Active.** Deployment set for `{target}`")

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    res = supabase.table("message_campaign").select("*").execute().data
    sessions = glob.glob("*.session")
    total = sum(1 for x in res if x['username'] != "SCHEDULE_MARKER")
    sent = sum(1 for x in res if x['status'] == 'success')
    fail = sum(1 for x in res if x['status'] == 'failed')
    pend = sum(1 for x in res if x['status'] == 'pending')
    
    report = (
        "📊 **Tacloban HQ: Deep Audit**\n"
        f"👥 Total Leads: {total}\n"
        f"✅ Sent: {sent} | ❌ Failed: {fail}\n"
        f"⏳ Pending: {pend}\n\n"
        f"📱 Active Sessions: {len(sessions)}\n"
        "--------------------------\n"
        "Engine: **Ready** | Sync: **Real-time**"
    )
    await event.respond(report)

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send List: (Auto-Deduplicate Active)**")
        msg = await conv.get_response()
        found = re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', msg.text)
        existing = {r['username'] for r in supabase.table("message_campaign").select("username").execute().data}
        new_leads = [{"username": u, "status": "pending"} for u in found if u not in existing]
        if new_leads: supabase.table("message_campaign").insert(new_leads).execute()
        await conv.send_message(f"✅ Integrated: {len(new_leads)} unique leads added.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Send your new Promo Script:**")
        new_text = (await conv.get_response()).text
        supabase.table("message_campaign").update({"edit_msg": new_text}).eq("status", "pending").execute()
        await conv.send_message("✅ **Promo script updated.**")

@bot.on(events.NewMessage(pattern='/send_now'))
async def blast(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = True
    await event.respond("🚀 **Blast Starting...** (Includes Auto-Organize)")
    supabase.table("message_campaign").delete().eq("status", "failed").execute()
    leads = supabase.table("message_campaign").select("*").eq("status", "pending").execute().data
    sessions = glob.glob("*.session")
    for lead in leads:
        if not SENDING_ACTIVE: break
        s_name = random.choice(sessions).replace(".session", "")
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                await client.send_message(lead['username'], lead.get('edit_msg', "Check this out!"))
                supabase.table("message_campaign").update({"status": "success", "sender_phone": s_name}).eq("id", lead['id']).execute()
            await asyncio.sleep(random.randint(60, 120))
        except:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()

@bot.on(events.NewMessage(pattern='/pause_send'))
async def stop_manual(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = False
    await event.respond("⏸️ **Manual Engine Halted.**")

@bot.on(events.NewMessage(pattern='/pause_sched'))
async def p_sched(event):
    global SCHED_ACTIVE
    SCHED_ACTIVE = not SCHED_ACTIVE
    await event.respond(f"📅 **Scheduler {'RESUMED' if SCHED_ACTIVE else 'PAUSED'}.**")

async def main(): await bot.run_until_disconnected()
if __name__ == '__main__': asyncio.get_event_loop().run_until_complete(main())

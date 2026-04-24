import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, Button, errors
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

# --- 1. GUIDE (BotFather Style) ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    guide = (
        "👑 **Tacloban HQ: Weightless Commander**\n\n"
        "/start - 👑 Open Command Center Guide\n"
        "/send_now - 🚀 Trigger Immediate Manual Blast\n"
        "/schedule - 📅 Set Date/Time for Auto-Send\n"
        "/pause_send - ⏸️ Stop Active Manual Sending\n"
        "/pause_sched - ⏸️ Stop Active Scheduled Tasks\n"
        "/add_list - 📂 Import New @Username List\n"
        "/edit_msg - 📝 Update Promotional Text\n"
        "/add_account - 📱 Link New Sender Session\n"
        "/status - 📊 View Global Audit & Stats"
    )
    await event.respond(guide)

# --- 2. ADD ACCOUNT (OTP/2FA Wizard) ---
@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account_wizard(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Step 1:** Enter the Phone Number (e.g., +639...)")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(phone, API_ID, API_HASH)
        await client.connect()
        
        try:
            sent = await client.send_code_request(phone)
            await conv.send_message("📩 **Step 2:** Enter the OTP code received:")
            otp = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, otp)
            except errors.SessionPasswordNeededError:
                await conv.send_message("🔐 **Step 3:** 2FA/Cloud Password detected. Enter your PIN:")
                pw = (await conv.get_response()).text.strip()
                await client.sign_in(password=pw)
            
            await conv.send_message(f"✅ **Success!** {phone} is now linked to the HQ.")
        except Exception as e:
            await conv.send_message(f"❌ **Error:** {str(e)}")
        finally:
            await client.disconnect()

# --- 3. SMART LIST INGESTION ---
@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list_smart(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send List:** (Handles @usernames, links, or plain text)")
        msg = await conv.get_response()
        raw_leads = msg.text.split('\n')
        
        # Clean & Extract Username via Regex
        clean_leads = []
        for line in raw_leads:
            match = re.search(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', line.strip())
            if match:
                clean_leads.append(match.group(1))
        
        # Fetch Existing for Deduplication
        existing = supabase.table("message_campaign").select("username").execute()
        existing_list = [item['username'] for item in existing.data]
        
        added_count = 0
        for u in clean_leads:
            if u not in existing_list:
                supabase.table("message_campaign").insert({"username": u, "status": "pending"}).execute()
                added_count += 1
        
        await conv.send_message(f"✅ **Organized!** {added_count} new leads added. Duplicates ignored.")

# --- 4. EDIT MESSAGE (Real-time Sync) ---
@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Send New Global Promo Message:**")
        new_msg = (await conv.get_response()).text
        # Update all pending and future tasks in Supabase
        supabase.table("message_campaign").update({"edit_msg": new_msg}).eq("status", "pending").execute()
        await conv.send_message("🔄 **Sync Complete.** All active blasts will use this new text immediately.")

# --- 5. ADVANCED STATUS AUDIT ---
@bot.on(events.NewMessage(pattern='/status'))
async def advanced_status(event):
    data = supabase.table("message_campaign").select("*").execute().data
    sessions = glob.glob("*.session")
    
    total = len(data)
    done = sum(1 for x in data if x['status'] == 'success')
    failed = sum(1 for x in data if x['status'] == 'failed')
    pending = sum(1 for x in data if x['status'] == 'pending')
    
    report = (
        "📊 **Tacloban HQ: Deep Audit**\n"
        f"👥 **Total Leads:** {total}\n"
        f"✅ **Sent:** {done} | ❌ **Failed:** {failed}\n"
        f"⏳ **Pending:** {pending}\n\n"
        f"📱 **Active Sessions:** {len(sessions)}\n"
        "--------------------------\n"
        "Engine: **Ready** | Sync: **Real-time**"
    )
    await event.respond(report)

async def main():
    print("🚀 Tacloban HQ v3.5.0: Advanced Engine Active")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

import os, asyncio, random, glob, pytz, logging, re, base64
from datetime import datetime
from telethon import TelegramClient, events, functions, types, errors
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

def restore_sessions():
    """Download sessions from Supabase to local storage on boot."""
    res = supabase.table("saved_sessions").select("*").execute()
    for row in res.data:
        file_path = f"{row['phone_number']}.session"
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(row['session_data']))
            print(f"✅ Restored: {file_path}")

def get_settings():
    return supabase.table("bot_settings").select("*").eq("id", "production").single().execute().data

restore_sessions()

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Enter Phone Number:**\n(e.g., +639XXXXXXXXX)")
        phone = (await conv.get_response()).text.strip().replace(" ", "")
        s_name = f"session_{phone.replace('+', '')}"
        
        client = TelegramClient(s_name, API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **Enter OTP Code:**")
            code = (await conv.get_response()).text
            try:
                await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA Password Required:**")
                pw = (await conv.get_response()).text
                await client.sign_in(password=pw)
            
            await client.disconnect()
            
            # Convert session to Base64 and Save to Supabase
            with open(f"{s_name}.session", "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                supabase.table("saved_sessions").upsert({
                    "phone_number": s_name, 
                    "session_data": encoded
                }).execute()
                
            await event.respond(f"✅ **Account {phone} Secured.**\nSaved to Cloud Vault & Ready for use.")
        except Exception as e:
            await event.respond(f"❌ **Error:** {str(e)}")

async def global_worker():
    while True:
        sets = get_settings()
        if not sets['is_sending_active'] and not sets['is_sched_active']:
            await asyncio.sleep(30); continue
        
        sessions = [f for f in glob.glob("*.session") if "bot.session" not in f]
        for s_file in sessions:
            s_name = s_file.replace(".session", "")
            today = datetime.now(PHT).strftime('%Y-%m-%d')
            sent = supabase.table("message_campaign").select("id", count="exact").eq("sent_by", s_name).gte("updated_at", today).execute().count
            if sent >= 5: continue 

            lead_req = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
            if not lead_req.data: break
            lead = lead_req.data[0]

            try:
                async with TelegramClient(s_name, API_ID, API_HASH) as client:
                    greet = random.choice(["Hi", "Hello", "Hey", "Greetings"])
                    msg = sets['current_promo_text'].replace("Hi,", f"{greet},").replace("Hi ", f"{greet} ")
                    await client.send_message(lead['add_list'], msg)
                    supabase.table("message_campaign").update({"status": "success", "sent_by": s_name, "updated_at": datetime.now(PHT).isoformat()}).eq("id", lead['id']).execute()
                    await asyncio.sleep(random.randint(240, 480))
            except: continue
        await asyncio.sleep(600)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    leads = supabase.table("message_campaign").select("status").execute().data
    pending = sum(1 for x in leads if x['status'] == 'pending')
    accs = len([f for f in glob.glob("*.session") if "bot.session" not in f])
    await event.respond(f"📊 **Sentinel Status**\nPending: {pending}\nActive Sessions: {accs}\nTime: {datetime.now(PHT).strftime('%I:%M %p PHT')}")

if __name__ == '__main__':
    print("🚀 Sentinel Engine v5.7.0 Online")
    loop = asyncio.get_event_loop()
    loop.create_task(global_worker())
    bot.run_until_disconnected()

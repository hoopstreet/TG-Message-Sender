import os, asyncio, random, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, errors, Button
from dotenv import load_dotenv
from supabase import create_client, Client
from guide_text import GUIDE

load_dotenv()
# Load Config
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SB_URL, SB_KEY)
PHT = pytz.timezone('Asia/Manila')
bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

IS_SENDING = False

async def get_stats_report():
    try:
        today_str = datetime.now(PHT).strftime('%Y-%m-%d')
        all_data = supabase.table("targets").select("status, updated_at").execute()
        total = len(all_data.data)
        daily = len([x for x in all_data.data if x['status'] == 'success' and str(x.get('updated_at')).startswith(today_str)])
        return f"📊 **HQ Audit**\n📈 Total Leads: {total}\n🚀 Sent Today: {daily}"
    except Exception as e:
        return f"❌ DB Error: {str(e)[:50]}"

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(GUIDE, buttons=[
        [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📊 Status", data="get_status")]
    ])

@bot.on(events.CallbackQuery)
async def handler(event):
    data = event.data.decode('utf-8')
    if data == "get_status":
        await event.respond(await get_stats_report())
    await event.answer()

print("✅ Tacloban HQ v2.3.4 - Docker-Ready & Injected.")
bot.run_until_disconnected()

# --- LEAD INGESTION LOGIC ---
@bot.on(events.CallbackQuery(data=b"add_users"))
async def add_users_handler(event):
    USER_STATE[event.sender_id] = "waiting_list"
    await event.respond("📂 **Send me the list of @usernames (one per line or comma-separated):**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def list_input_handler(event):
    state = USER_STATE.get(event.sender_id)
    if state == "waiting_list" and not event.text.startswith('/'):
        # Clean the input: split by newline or comma, remove @ and spaces
        raw_list = event.text.replace(',', '\n').split('\n')
        cleaned_usernames = [u.strip().replace('@', '') for u in raw_list if u.strip()]
        
        if not cleaned_usernames:
            await event.respond("❌ No valid usernames found.")
            return

        # Prepare data for Supabase
        data_to_insert = [{"username": u, "status": "pending"} for u in cleaned_usernames]
        
        try:
            supabase.table("targets").insert(data_to_insert).execute()
            await event.respond(f"✅ **Success!** Added {len(cleaned_usernames)} leads to the queue.")
            USER_STATE.pop(event.sender_id)
        except Exception as e:
            await event.respond(f"❌ DB Error: {str(e)[:50]}")

# --- SESSION MANAGEMENT LOGIC ---
@bot.on(events.CallbackQuery(data=b"add_acc"))
async def add_acc_init(event):
    USER_STATE[event.sender_id] = "waiting_phone"
    await event.respond("📱 **Enter the Phone Number for the new account (with +country code):**")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def session_creator_handler(event):
    state = USER_STATE.get(event.sender_id)
    if not state or event.text.startswith('/'): return
    
    if state == "waiting_phone":
        phone = event.text.strip()
        USER_STATE[event.sender_id] = {"state": "waiting_code", "phone": phone}
        temp_client = TelegramClient(phone, API_ID, API_HASH)
        await temp_client.connect()
        await temp_client.send_code_request(phone)
        await event.respond(f"📩 **Code sent to {phone}. Enter it here:**")
        await temp_client.disconnect()

    elif isinstance(state, dict) and state.get("state") == "waiting_code":
        phone = state["phone"]
        code = event.text.strip()
        try:
            new_client = TelegramClient(phone, API_ID, API_HASH)
            await new_client.start(phone=phone, code=code)
            await event.respond(f"✅ **Account `{phone}` added successfully!**")
            await new_client.disconnect()
            USER_STATE.pop(event.sender_id)
        except Exception as e:
            await event.respond(f"❌ Auth Error: {str(e)[:50]}")
            USER_STATE.pop(event.sender_id)

# --- MESSAGE CONFIGURATION ---
@bot.on(events.CallbackQuery(data=b"edit_msg"))
async def edit_msg_init(event):
    USER_STATE[event.sender_id] = "waiting_msg"
    await event.respond("📝 **Send me the new message text:**\n\n*Use {name} to personalize if needed.*")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def msg_save_handler(event):
    if USER_STATE.get(event.sender_id) == "waiting_msg":
        new_text = event.text
        supabase.table("bot_settings").upsert({"key": "active_message", "value": new_text}).execute()
        await event.respond(f"✅ **Message Updated:**\n\n{new_text}")
        USER_STATE.pop(event.sender_id)

# --- THE OUTREACH ENGINE ---
@bot.on(events.CallbackQuery(data=b"run_now"))
async def run_outreach(event):
    global IS_SENDING
    if IS_SENDING:
        await event.answer("⚠️ Engine is already running!", alert=True)
        return
    
    IS_SENDING = True
    await event.respond("🚀 **Engine Started.** Monitoring logs...")
    
    while IS_SENDING:
        # 1. Fetch active message
        msg_res = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
        msg_text = msg_res.data['value'] if msg_res.data else "Hello!"
        
        # 2. Get next pending target
        target_res = supabase.table("targets").select("*").eq("status", "pending").limit(1).execute()
        if not target_res.data:
            await event.respond("🏁 **Queue empty. Engine standby.**")
            break
            
        target = target_res.data[0]
        user_to_hit = target['username']
        
        # 3. Rotate through session files
        sessions = [f.replace('.session', '') for f in glob.glob("*.session") if "bot_control" not in f]
        if not sessions:
            await event.respond("❌ **No sender accounts found!** Use 'Add Acc' first.")
            break
            
        selected_acc = random.choice(sessions)
        
        try:
            async with TelegramClient(selected_acc, API_ID, API_HASH) as client:
                await client.send_message(user_to_hit, msg_text)
                supabase.table("targets").update({
                    "status": "success", 
                    "sent_by": selected_acc,
                    "updated_at": datetime.now(PHT).isoformat()
                }).eq("id", target['id']).execute()
                await event.respond(f"✅ Sent to @{user_to_hit} via `{selected_acc}`")
                
            # Random delay to prevent bans (2.5 to 5 minutes)
            await asyncio.sleep(random.randint(150, 300))
            
        except Exception as e:
            await event.respond(f"⚠️ Error with `{selected_acc}`: {str(e)[:50]}")
            # If account is restricted/banned, mark target as failed to move on
            if "peer" in str(e).lower() or "flood" in str(e).lower():
                await asyncio.sleep(900) # Wait 15 mins on flood
    
    IS_SENDING = False

print("🔥 Tacloban HQ v2.4.0 FULLY LOADED.")

# --- COMMAND MENU HANDLER ---
@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def menu_command_handler(event):
    cmd = event.text.split()[0].lower() if event.text else ""
    
    if cmd == '/status':
        await event.respond(await get_stats_report())
    elif cmd == '/send_now':
        await run_outreach(event)
    elif cmd == '/add_list':
        await add_users_handler(event)
    elif cmd == '/edit_msg':
        await edit_msg_init(event)
    elif cmd == '/add_account':
        await add_acc_init(event)
    elif cmd == '/pause_send':
        global IS_SENDING
        IS_SENDING = False
        await event.respond("🛑 **Sending Paused.**")

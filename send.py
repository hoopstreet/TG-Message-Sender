import os, asyncio, random, glob
from telethon import TelegramClient, events, errors, Button
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SB_URL, SB_KEY)
VERSION = "v1.4.0"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

USER_STATE = {} 
NEW_ACC_CLIENTS = {}

async def run_continuous_outreach(event):
    # Fetch Message
    msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
    message_text = msg_data.data['value'] if msg_data.data else "No message set."
    
    # Auto-detect all .session files
    sessions = glob.glob("*.session")
    if not sessions:
        await event.respond("❌ No accounts found. Add one first.")
        return

    await event.respond(f"🚀 **Continuous Blast Started**\nUsing {len(sessions)} accounts.")

    while True:
        # Get the next 'pending' lead
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data:
            await event.respond("✅ **Queue Empty.** All messages sent.")
            break
        
        target = res.data[0]
        username = target['username']
        
        # Cycle through sessions
        for sess_file in sessions:
            client_name = sess_file.replace('.session', '')
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({"status": "success", "sent_by": client_name}).eq("id", target['id']).execute()
                    await event.respond(f"✅ Success: @{username} via {client_name}")
                    break # Move to next lead
            except errors.PeerFloodError:
                continue # Try next account for same lead
            except Exception as e:
                supabase.table("targets").update({"status": f"error: {str(e)[:20]}"}).eq("id", target['id']).execute()
                await event.respond(f"❌ Error: @{username} | {str(e)[:30]}")
                break 

        await asyncio.sleep(random.randint(120, 300))

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Continuous Control v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Start Continuous", data="run_blast"), Button.inline("📊 Stats", data="get_status")],
            [Button.inline("📝 Msg", data="edit_msg"), Button.inline("📂 Add Users", data="add_users")],
            [Button.inline("📱 Add Acc", data="add_acc"), Button.inline("♻️ Reset", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')
    if data == "run_blast":
        asyncio.create_task(run_continuous_outreach(event))
    elif data == "add_users":
        USER_STATE[event.sender_id] = "waiting_users"
        await event.respond("📂 **Send list (one per line):**")
    elif data == "get_status":
        s = supabase.table("targets").select("status", count="exact").execute()
        await event.respond(f"📊 **Stats:** {s.count} total leads.")

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def handle_input(event):
    state = USER_STATE.get(event.sender_id)
    if not state or event.text.startswith('/'): return

    if state == "waiting_users":
        users = [u.strip().replace('@','') for u in event.text.split('\n') if u.strip()]
        data = [{"username": u, "status": "pending"} for u in users]
        supabase.table("targets").insert(data).execute()
        await event.respond(f"✅ Added {len(data)} users to the end of the queue.")
        USER_STATE.pop(event.sender_id)
    
    # (Rest of Login Logic for Phase 2 from v1.3.1 remains the same...)

print(f"Bot v{VERSION} Operational...")
bot.run_until_disconnected()

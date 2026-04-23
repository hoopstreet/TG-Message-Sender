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
VERSION = "v1.5.0"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Global control flags
IS_PAUSED = True

async def run_relay_outreach(event):
    global IS_PAUSED
    IS_PAUSED = False
    
    msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
    message_text = msg_data.data['value'] if msg_data.data else "No message set."
    
    sessions = glob.glob("*.session")
    if not sessions:
        await event.respond("❌ No accounts found.")
        return

    await event.respond("🚀 **Relay Blast Active.** Accounts will cycle on limits.")

    while not IS_PAUSED:
        # Get next pending lead
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data:
            await event.respond("✅ **Queue Empty.**")
            break
        
        target = res.data[0]
        username = target['username']
        lead_sent = False

        for sess_file in sessions:
            if IS_PAUSED: break
            client_name = sess_file.replace('.session', '')
            
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({"status": "success", "sent_by": client_name}).eq("id", target['id']).execute()
                    await event.respond(f"✅ @{username} sent by {client_name}")
                    lead_sent = True
                    break # Success! Move to next lead
            
            except errors.FloodWaitError as e:
                await event.respond(f"⚠️ {client_name} hit limit. Switching to next account...")
                continue # Try next account for this same lead
            
            except Exception as e:
                await event.respond(f"❌ {client_name} error: {str(e)[:20]}")
                continue

        if not lead_sent and not IS_PAUSED:
            await event.respond("🕒 **All accounts limited.** Cooling down for 15 mins...")
            await asyncio.sleep(900) # Wait 15 mins before retrying the cycle
        
        await asyncio.sleep(random.randint(120, 300))

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        f"👑 **Relay Control v{VERSION}**",
        buttons=[
            [Button.inline("🚀 Send Now", data="run_blast"), Button.inline("⏸️ Pause", data="pause_bot")],
            [Button.inline("📊 Stats", data="get_status"), Button.inline("♻️ Reset", data="reset_db")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    global IS_PAUSED
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')
    
    if data == "run_blast":
        if not IS_PAUSED:
            await event.answer("⚠️ Already running!", alert=True)
        else:
            asyncio.create_task(run_relay_outreach(event))
            
    elif data == "pause_bot":
        IS_PAUSED = True
        await event.edit("⏸️ **System Paused.** Standing by...")
        
    elif data == "get_status":
        s = supabase.table("targets").select("status", count="exact").execute()
        await event.answer(f"Leads: {s.count}", alert=True)

print(f"Bot v{VERSION} Relay Engine Online...")
bot.run_until_disconnected()

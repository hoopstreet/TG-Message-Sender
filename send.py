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
VERSION = "v1.5.1"

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
IS_PAUSED = True

async def run_relay_outreach(event):
    global IS_PAUSED
    IS_PAUSED = False
    
    msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
    message_text = msg_data.data['value'] if msg_data.data else "No message set."
    
    await event.respond("🚀 **Smart Relay Started.**\nSafety delays and auto-switching enabled.")

    while not IS_PAUSED:
        sessions = glob.glob("*.session")
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        
        if not res.data:
            await event.respond("✅ **Queue Finished.**")
            break
        
        target = res.data[0]
        username = target['username']
        success = False

        for sess_file in sessions:
            if IS_PAUSED: break
            client_name = sess_file.replace('.session', '')
            
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({
                        "status": "success", 
                        "sent_by": client_name
                    }).eq("id", target['id']).execute()
                    
                    await event.respond(f"✅ @{username} | via {client_name}")
                    success = True
                    # Safety Wait after successful send
                    wait_time = random.randint(150, 300) 
                    await asyncio.sleep(wait_time)
                    break 

            except errors.FloodWaitError as e:
                await event.respond(f"⏳ {client_name} limited for {e.seconds}s. Trying next account...")
                continue # Move to next account in the list
            
            except Exception as e:
                print(f"Error on {client_name}: {e}")
                continue

        if not success and not IS_PAUSED:
            await event.respond("😴 **All accounts limited.** Global sleep for 10 mins...")
            await asyncio.sleep(600)

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
        await event.edit("⏸️ **Paused.** Bot will stop after current attempt.")
    elif data == "get_status":
        s = supabase.table("targets").select("status", count="exact").eq("status", "pending").execute()
        await event.answer(f"Pending: {s.count}", alert=True)

print(f"Relay Engine v{VERSION} Online...")
bot.run_until_disconnected()

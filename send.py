import os
import asyncio
import sys
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
ADMIN_VAL = os.getenv('ADMIN_ID')

print(f"DEBUG: API_ID is {'set' if API_ID else 'MISSING'}")
print(f"DEBUG: API_HASH is {'set' if API_HASH else 'MISSING'}")
print(f"DEBUG: ADMIN_ID is {ADMIN_VAL}")

if not API_ID or not API_HASH:
    print("FATAL: Missing API_ID or API_HASH. Check Northflank Env Vars.")
    sys.exit(1)

try:
    ADMIN_ID = int(ADMIN_VAL) if ADMIN_VAL else 0
except ValueError:
    print(f"FATAL: ADMIN_ID '{ADMIN_VAL}' is not a valid number.")
    sys.exit(1)

client = TelegramClient('bot_session', int(API_ID), API_HASH)

is_paused = False
current_index = 0

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    await event.respond("🚀 **TG-Sender Active**\nCommands: /send, /pause, /status")

@client.on(events.NewMessage(pattern='/send'))
async def start_sending(event):
    global is_paused, current_index
    if event.sender_id != ADMIN_ID: return
    is_paused = False
    await event.respond(f"▶️ Starting from index {current_index}...")
    if not os.path.exists('targets.txt'):
        await event.respond("❌ Error: targets.txt not found!")
        return
    with open('targets.txt', 'r') as f:
        targets = f.readlines()
    for i in range(current_index, len(targets)):
        if is_paused: break
        username = targets[i].strip()
        if not username: continue
        try:
            await client.send_message(username, "Your Marketing Message")
            current_index = i + 1
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Msg Error: {e}")
            await asyncio.sleep(5)

@client.on(events.NewMessage(pattern='/pause'))
async def pause_sending(event):
    global is_paused
    if event.sender_id != ADMIN_ID: return
    is_paused = True
    await event.respond("⏸ Paused.")

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    await event.respond(f"📊 Progress: {current_index} targets processed.")

async def main():
    try:
        await client.start()
        print("✅ Bot authenticated and running!")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"FATAL Client Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

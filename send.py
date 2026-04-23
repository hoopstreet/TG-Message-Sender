import os
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

client = TelegramClient('bot_session', API_ID, API_HASH)

is_paused = False
current_index = 0

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    await event.respond("🚀 **TG-Sender Command Center**\n\n1. `/send`\n2. `/pause`\n3. `/status`\n4. `/set_index <num>`")

@client.on(events.NewMessage(pattern='/send'))
async def start_sending(event):
    global is_paused, current_index
    if event.sender_id != ADMIN_ID: return
    is_paused = False
    await event.respond(f"▶️ Starting batch from index {current_index}...")
    with open('targets.txt', 'r') as f:
        targets = f.readlines()
    for i in range(current_index, len(targets)):
        if is_paused: break
        username = targets[i].strip()
        try:
            await client.send_message(username, "Your Marketing Message")
            current_index = i + 1
            await asyncio.sleep(30)
        except Exception as e:
            await event.respond(f"❌ Error at {username}: {str(e)}")

@client.on(events.NewMessage(pattern='/pause'))
async def pause_sending(event):
    global is_paused
    if event.sender_id != ADMIN_ID: return
    is_paused = True
    await event.respond("⏸ Paused.")

@client.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    await event.respond(f"📊 Index: {current_index}\nPaused: {is_paused}")

async def main():
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

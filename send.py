import os
from telethon import TelegramClient

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

print(f"DEBUG: API_ID is {'SET' if api_id else 'MISSING'}")
print(f"DEBUG: API_HASH is {'SET' if api_hash else 'MISSING'}")

if not api_id or not api_hash:
    print("FATAL: Environment variables not found!")
    exit(1)

client = TelegramClient('bot_session', int(api_id), api_hash)

async def main():
    print("✅ Bot session started successfully!")
    await client.send_message('me', 'Automation is live!')

with client:
    client.loop.run_until_complete(main())

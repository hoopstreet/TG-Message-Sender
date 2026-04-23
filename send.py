import os
import sys
from telethon import TelegramClient

# Absolute path to ensure the container finds the session file
base_dir = os.path.dirname(os.path.abspath(__file__))
session_path = os.path.join(base_dir, 'bot_session.session')

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

print(f"DEBUG: API_ID is {'SET' if api_id else 'MISSING'}")
print(f"DEBUG: API_HASH is {'SET' if api_hash else 'MISSING'}")

if not api_id or not api_hash:
    print("FATAL: Environment variables not found!")
    sys.exit(1)

# Initialize with the session file path
client = TelegramClient(session_path, int(api_id), api_hash)

async def main():
    print("✅ Connection Successful!")
    # Sending a confirmation to your saved messages
    await client.send_message('me', 'Automation is live on Northflank!')

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())

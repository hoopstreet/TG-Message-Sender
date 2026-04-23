import os, asyncio, random
from telethon import TelegramClient, events, errors
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("YOUR_TELEGRAM_ID", 0))

SESSIONS = [".telegram_session", "catherine_session", "mara_session", "jasmine_session", "alaska_session"]
CURRENT_MESSAGE = (
    "Hi, We are launching a new iGaming platform this week and seeking one "
    "professional team to lead all marketing and growth operations.\n\n"
    "The Role:\nFull ownership of the marketing funnel, including Social Media, "
    "Banner Promotions, and CSR initiatives.\n\n"
    "📩 TO APPLY: Message @XeniaXu8 with your experience and 1st-month targets."
)

bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def run_outreach(event):
    idx = 0
    if os.path.exists('last_sent.txt'):
        with open('last_sent.txt', 'r') as f:
            line = f.read().strip()
            idx = int(line) if line else 0
    if not os.path.exists('targets.txt'):
        await event.respond("❌ Error: targets.txt not found.")
        return
    with open('targets.txt', 'r') as f:
        targets = [l.strip().replace('@', '') for l in f if l.strip()]
    
    await event.respond(f"🚀 Outreach started! Index: {idx}")
    for session in SESSIONS:
        if idx >= len(targets): break
        try:
            async with TelegramClient(session, API_ID, API_HASH) as client:
                while idx < len(targets):
                    user = targets[idx]
                    try:
                        await client.send_message(user, CURRENT_MESSAGE)
                        idx += 1
                        with open('last_sent.txt', 'w') as f: f.write(str(idx))
                        await asyncio.sleep(random.randint(120, 240))
                    except errors.PeerFloodError:
                        await event.respond(f"⚠️ {session} hit limit. Switching...")
                        break
                    except Exception:
                        idx += 1
                        continue
        except Exception as e:
            continue
    await event.respond(f"✅ Batch complete. Final Progress: {idx}")

@bot.on(events.NewMessage(pattern='/send_now', from_users=ADMIN_ID))
async def trigger(event):
    asyncio.create_task(run_outreach(event))

@bot.on(events.NewMessage(pattern='/status', from_users=ADMIN_ID))
async def status(event):
    idx = "0"
    if os.path.exists('last_sent.txt'):
        with open('last_sent.txt', 'r') as f: idx = f.read().strip()
    await event.respond(f"📊 Current Progress: Index {idx}")

print("Manager Bot is Online...")
bot.run_until_disconnected()

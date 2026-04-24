import os, asyncio, random, glob, pytz, logging, re
from datetime import datetime
from telethon import TelegramClient, events, Button, errors, functions, types
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
PHT = pytz.timezone('Asia/Manila')
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))
except Exception as e:
    print(f"❌ Initialization Error: {e}")

SENDING_ACTIVE = True

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ: Stealth Commander v3.7.2**\n/send_now | /status | /add_list | /add_account | /cleanup")

@bot.on(events.NewMessage(pattern='/send_now'))
async def stealth_blast(event):
    global SENDING_ACTIVE
    SENDING_ACTIVE = True
    await event.respond("🚀 **Blast Initialized.** Tagging accounts for audit...")
    leads = supabase.table("message_campaign").select("*").eq("status", "pending").execute()
    sessions = glob.glob("*.session")
    for lead in leads.data:
        if not SENDING_ACTIVE: break
        s_file = random.choice(sessions)
        s_name = s_file.replace(".session", "")
        try:
            async with TelegramClient(s_name, API_ID, API_HASH) as client:
                await asyncio.sleep(random.randint(5, 10))
                await client.send_message(lead['username'], lead.get('edit_msg', "Check this out!"))
                # UPDATE LOGIC: Save the sender identity
                supabase.table("message_campaign").update({
                    "status": "success", 
                    "sender_phone": s_name
                }).eq("id", lead['id']).execute()
                await asyncio.sleep(random.randint(60, 120))
        except Exception as e:
            supabase.table("message_campaign").update({"status": "failed"}).eq("id", lead['id']).execute()

@bot.on(events.NewMessage(pattern='/status'))
async def status_report(event):
    res = supabase.table("message_campaign").select("sender_phone, status").execute()
    stats = {}
    for row in res.data:
        p = row.get('sender_phone') or "Legacy/Unknown"
        if p not in stats: stats[p] = 0
        if row['status'] == 'success': stats[p] += 1
    acc_report = "\n".join([f"📱 {p}: {c} sends" for p, c in stats.items()])
    await event.respond(f"📊 **HQ Deep Audit**\n{acc_report}\n\nEngine: **Active**")

@bot.on(events.NewMessage(pattern='/cleanup'))
async def cleanup(event):
    supabase.table("message_campaign").delete().eq("status", "failed").execute()
    await event.respond("🧹 **Failed leads cleared.**")

async def main():
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

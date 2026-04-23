import os, asyncio, random, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, errors, Button
from dotenv import load_dotenv
from supabase import create_client, Client
from guide_text import GUIDE

load_dotenv()
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
USER_STATE = {}

async def compact_queue():
    res = supabase.table("targets").select("id, username").eq("status", "pending").execute()
    to_delete = [row['id'] for row in res.data if not row['username'] or row['username'].strip() == ""]
    for i in to_delete: supabase.table("targets").delete().eq("id", i).execute()
    return len(to_delete)

async def get_stats_report():
    today_str = datetime.now(PHT).strftime('%Y-%m-%d')
    all_data = supabase.table("targets").select("status, sent_by, updated_at").execute()
    total = len(all_data.data)
    sent = len([x for x in all_data.data if x['status'] == 'success'])
    daily = len([x for x in all_data.data if x['status'] == 'success' and str(x.get('updated_at')).startswith(today_str)])
    sessions = [f.replace('.session', '') for f in glob.glob("*.session") if "bot_control" not in f]
    acc_log = "".join([f"👤 `{s}`: {len([x for x in all_data.data if x['sent_by']==s])} total\n" for s in sessions])
    return f"📊 **HQ Audit**\n━━━━━━━━\n📈 Total: {total}\n✅ Sent: {sent}\n🚀 Today: {daily}\n\n📱 **Accounts:**\n{acc_log if acc_log else 'None'}"

async def shared_outreach_logic(event):
    global IS_SENDING
    IS_SENDING = True
    removed = await compact_queue()
    if removed > 0: await event.respond(f"🧹 Cleaned {removed} empty leads.")
    while IS_SENDING:
        msg_data = supabase.table("bot_settings").select("value").eq("key", "active_message").single().execute()
        message_text = msg_data.data['value'] if msg_data.data else "Hello!"
        res = supabase.table("targets").select("*").eq("status", "pending").order("id").limit(1).execute()
        if not res.data:
            await event.respond("✅ **Queue Finished.**"); break
        target = res.data[0]
        username, success = target['username'], False
        for sess_file in glob.glob("*.session"):
            if not IS_SENDING or "bot_control" in sess_file: continue
            client_name = sess_file.replace('.session', '')
            try:
                async with TelegramClient(client_name, API_ID, API_HASH) as client:
                    await client.send_message(username, message_text)
                    supabase.table("targets").update({
                        "status": "success", "sent_by": client_name,
                        "updated_at": datetime.now(PHT).isoformat()
                    }).eq("id", target['id']).execute()
                    await event.respond(f"✅ `[OK]` @{username} via {client_name}")
                    success = True
                    await asyncio.sleep(random.randint(150, 300)); break 
            except Exception as e: await event.respond(f"⚠️ `{client_name}`: {str(e)[:40]}")
        if not success and IS_SENDING: await asyncio.sleep(900)
    IS_SENDING = False

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(GUIDE, buttons=[
        [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📊 Status", data="get_status")],
        [Button.inline("📱 Add Acc", data="add_acc"), Button.inline("📝 Edit Msg", data="edit_msg")],
        [Button.inline("📂 Add List", data="add_users"), Button.inline("⏸️ Stop", data="stop")]
    ])

@bot.on(events.CallbackQuery)
async def handler(event):
    global IS_SENDING
    data = event.data.decode('utf-8')
    if data == "get_status": await event.respond(await get_stats_report())
    elif data == "run_now": asyncio.create_task(shared_outreach_logic(event))
    elif data == "stop": IS_SENDING = False; await event.answer("🛑 Engine Stopping...", alert=True)
    await event.answer()

print("✅ Tacloban HQ v2.3.2 Online.")
bot.run_until_disconnected()

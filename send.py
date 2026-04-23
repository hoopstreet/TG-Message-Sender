import os, asyncio, random, glob, pytz, re
from datetime import datetime, date
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
VERSION = "v2.1.0"
PHT = pytz.timezone('Asia/Manila')
bot = TelegramClient('bot_control', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
IS_SENDING, USER_STATE, TEMP_CLIENTS = False, {}, {}

async def compact_queue():
    res = supabase.table("targets").select("id, username").eq("status", "pending").execute()
    to_delete = [row['id'] for row in res.data if not row['username'] or row['username'].strip() == ""]
    if to_delete:
        for i in to_delete: supabase.table("targets").delete().eq("id", i).execute()
    return len(to_delete)

async def shared_outreach_logic(event, mode_name):
    global IS_SENDING
    IS_SENDING = True
    removed = await compact_queue()
    if removed > 0: await event.respond(f"🧹 Purged {removed} empty leads.")
    await event.respond(f"⚡ **Outreach Started** ({mode_name})")
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
            except errors.FloodWaitError as e: await event.respond(f"🕒 `{client_name}` limited: {e.seconds}s")
            except Exception as e: await event.respond(f"❌ `{client_name}`: {str(e)[:40]}")
        if not success and IS_SENDING: await asyncio.sleep(900)
    IS_SENDING = False

async def get_stats_report():
    today_str = datetime.now(PHT).strftime('%Y-%m-%d')
    all_data = supabase.table("targets").select("status, sent_by, updated_at").execute()
    total_leads, total_sent = len(all_data.data), len([x for x in all_data.data if x['status'] == 'success'])
    daily_sent = len([x for x in all_data.data if x['status'] == 'success' and x.get('updated_at', '').startswith(today_str)])
    sessions = [f.replace('.session', '') for f in glob.glob("*.session") if "bot_control" not in f]
    acc_report = ""
    for acc in sessions:
        lifetime = len([x for x in all_data.data if x['sent_by'] == acc])
        today = len([x for x in all_data.data if x['sent_by'] == acc and x.get('updated_at', '').startswith(today_str)])
        acc_report += f"👤 `{acc}`: {today} today | {lifetime} total\n"
    return (f"📊 **Global Audit v{VERSION}**\n━━━━━━━━━━━━━━━━━━\n📈 **Performance**\n┣ Total: {total_leads} | Sent: {total_sent}\n┗ Today: {daily_sent} 🚀\n\n📱 **Accounts**\n{acc_report if acc_report else 'None'}\n⚙️ **Engine:** {'🟢 Running' if IS_SENDING else '🔴 Idle'}")

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(f"👑 **Tacloban HQ v{VERSION}**", buttons=[
        [Button.inline("🚀 Start Blast", data="run_now"), Button.inline("📊 Full Audit", data="get_status")],
        [Button.inline("📱 Add Acc", data="add_acc"), Button.inline("📝 Edit Msg", data="edit_msg")],
        [Button.inline("📂 Add Users", data="add_users"), Button.inline("⏸️ Stop", data="stop")]
    ])

@bot.on(events.CallbackQuery)
async def callback(event):
    if event.data == b"get_status": await event.respond(await get_stats_report())
    elif event.data == b"run_now": asyncio.create_task(shared_outreach_logic(event, "Manual"))
    elif event.data == b"stop": global IS_SENDING; IS_SENDING = False; await event.edit("⏸️ **Engine Paused.**")

print(f"Audit Engine v{VERSION} Online.")
bot.run_until_disconnected()

from guide_text import GUIDE

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        GUIDE,
        buttons=[
            [Button.inline("🚀 Start Blast", data="run_now"), 
             Button.inline("📊 Full Audit", data="get_status")],
            [Button.inline("📱 Add Account", data="add_acc"), 
             Button.inline("📝 Edit Message", data="edit_msg")],
            [Button.inline("📂 Add Leads", data="add_users"), 
             Button.inline("⏸️ Stop Engine", data="stop")]
        ]
    )

@bot.on(events.NewMessage(pattern='/start', from_users=ADMIN_ID))
async def start(event):
    await event.respond(
        GUIDE,
        buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), 
             Button.inline("📅 Schedule", data="set_sched")],
            [Button.inline("⏸️ Pause Send", data="stop"), 
             Button.inline("⏸️ Pause Sched", data="stop_sched")],
            [Button.inline("📂 Add List", data="add_users"), 
             Button.inline("📝 Edit Msg", data="edit_msg")],
            [Button.inline("📱 Add Account", data="add_acc"), 
             Button.inline("📊 Status", data="get_status")]
        ]
    )

@bot.on(events.CallbackQuery)
async def callback(event):
    data = event.data
    if data == b"get_status":
        await event.respond(await get_stats_report())
    elif data == b"run_now":
        asyncio.create_task(shared_outreach_logic(event, "Manual Blast"))
    elif data == b"set_sched":
        USER_STATE[event.sender_id] = "waiting_sched_time"
        await event.respond("📅 **Set Schedule:**\nFormat: `YYYY-MM-DD HH:MM`\nExample: `2026-04-25 09:00` (PHT)")
    elif data == b"stop":
        global IS_SENDING
        IS_SENDING = False
        await event.respond("🛑 **Manual Sending Paused.**")
    elif data == b"stop_sched":
        # Logic to cancel background scheduled tasks
        await event.respond("⏸️ **Scheduled Task Stopped.**")
    elif data == b"add_acc":
        USER_STATE[event.sender_id] = "waiting_phone"
        await event.respond("📱 Enter phone (+63...):")

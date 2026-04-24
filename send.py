import os, asyncio, glob, pytz
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
PHT = pytz.timezone('Asia/Manila')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = TelegramClient('bot', int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")).start(bot_token=os.getenv("CONTROL_BOT_TOKEN"))

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("👑 **Tacloban HQ v2.3.0**", buttons=[
        [Button.inline("🚀 Send Now", data="send_now"), Button.inline("📅 Schedule", data="schedule")],
        [Button.inline("📊 Status", data="status"), Button.inline("📂 Add List", data="add_list")],
        [Button.inline("📝 Edit Msg", data="edit_msg"), Button.inline("📱 Add Acc", data="add_account")],
        [Button.inline("⏸️ Pause Send", data="pause_send"), Button.inline("⏸️ Pause Sched", data="pause_sched")]
    ])

@bot.on(events.CallbackQuery)
async def handler(event):
    cmd = event.data.decode('utf-8')
    if cmd == "status":
        res = supabase.table("message_campaign").select("status").execute()
        success = sum(1 for r in res.data if r['status'] == 'success')
        await event.respond(f"📊 **Global Audit:** {success} Successful Blasts.")
@bot.on(events.CallbackQuery(data="add_list"))
async def add_list_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Send @usernames (one per line):**")
        msg = await conv.get_response()
        names = [n.strip() for n in msg.text.split('\n') if n.strip()]
        for name in names:
            supabase.table("message_campaign").upsert({"username": name, "status": "pending"}).execute()
        await conv.send_message(f"✅ Imported {len(names)} leads to `message_campaign`.")

@bot.on(events.CallbackQuery(data="edit_msg"))
async def edit_msg_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Enter your new Promotional Text:**")
        msg = await conv.get_response()
        supabase.table("message_campaign").update({"edit_msg": msg.text}).eq("status", "pending").execute()
        await conv.send_message("✅ Promo text updated for all pending leads.")
@bot.on(events.CallbackQuery(data="send_now"))
async def send_now_handler(event):
    await event.respond("🚀 **Manual Blast Started...**")
    # Logic to fetch first pending row and rotate .session files
    res = supabase.table("message_campaign").select("*").eq("status", "pending").limit(1).execute()
    if res.data:
        # Execution loop would go here
        pass

@bot.on(events.CallbackQuery(data="pause_send"))
async def pause_send_handler(event):
    supabase.table("message_campaign").update({"status": "paused"}).eq("status", "pending").execute()
    await event.respond("⏸️ **Manual loop set to PAUSED.**")

@bot.on(events.CallbackQuery(data="pause_sched"))
async def pause_sched_handler(event):
    supabase.table("message_campaign").update({"pause_sched": True}).execute()
    await event.respond("⏸️ **Scheduled tasks set to PAUSED.**")
async def scheduler_loop():
    while True:
        now_pht = datetime.now(PHT).strftime('%Y-%m-%d %H:%M')
        # 1:1 Match: checking 'schedule' and 'pause_sched' columns
        res = supabase.table("message_campaign").select("*").eq("schedule", now_pht).eq("pause_sched", False).eq("status", "pending").execute()
        for task in res.data:
            asyncio.create_task(run_blast(task))
        await asyncio.sleep(60)

async def run_blast(row):
    # This is the engine that actually sends the message
    # It updates 'status', 'send_now', and 'updated_at'
    pass

@bot.on(events.CallbackQuery(data="status"))
async def status_audit(event):
    res = supabase.table("message_campaign").select("status").execute()
    stats = {"success": 0, "failed": 0, "pending": 0}
    for r in res.data:
        stats[r['status']] = stats.get(r['status'], 0) + 1
    await event.respond(f"📊 **Audit Report**\n✅ Success: {stats['success']}\n❌ Failed: {stats['failed']}\n⏳ Pending: {stats['pending']}")
@bot.on(events.CallbackQuery(data="add_account"))
async def add_account_handler(event):
    sessions = glob.glob("*.session")
    active_sessions = [s.replace(".session", "") for s in sessions if "bot" not in s]
    if not active_sessions:
        await event.respond("⚠️ No .session files found in root. Upload them via iSH first.")
    else:
        await event.respond(f"📱 **Active Sessions:**\n" + "\n".join(active_sessions))
async def run_blast(row):
    sessions = [s for s in glob.glob("*.session") if "bot" not in s]
    if not sessions: return
    
    # Select random session for rotation
    session_file = random.choice(sessions).replace('.session', '')
    try:
        async with TelegramClient(session_file, int(os.getenv("TELEGRAM_API_ID")), os.getenv("TELEGRAM_API_HASH")) as client:
            await client.send_message(row['username'], row['edit_msg'])
            # 1:1 Map Update
            supabase.table("message_campaign").update({
                "status": "success",
                "send_now": session_file,
                "updated_at": datetime.now(PHT).isoformat()
            }).eq("id", row['id']).execute()
    except Exception as e:
        supabase.table("message_campaign").update({"status": "failed"}).eq("id", row['id']).execute()

@bot.on(events.CallbackQuery(data="schedule"))
async def schedule_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📅 **Enter PHT Time (YYYY-MM-DD HH:MM):**")
        response = await conv.get_response()
        supabase.table("message_campaign").update({"schedule": response.text}).eq("status", "pending").execute()
        await conv.send_message(f"✅ Leads scheduled for {response.text} PHT.")

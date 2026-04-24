from telethon import TelegramClient, events, Button
import asyncio

# --- 1. DEFINE TRIGGER LOGIC (The "Functions") ---
async def trigger_send_now(event):
    global IS_SENDING
    IS_SENDING = True
    await event.respond("🚀 **Manual Blast Started.**")
    await shared_outreach_logic(event, "Manual")

async def trigger_status(event):
    report = await get_stats_report()
    await event.respond(report)

async def trigger_add_list(event):
    USER_STATE[event.sender_id] = "waiting_list"
    await event.respond("📂 **Send @usernames (one per line):**")

# --- 2. COMMAND ROUTER (Handles Slash Commands /menu) ---
@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def router(event):
    if not event.text: return
    cmd = event.text.split()[0].lower()

    # Map Slash Commands to Functions
    if cmd == '/start': await start(event)
    elif cmd == '/send_now': await trigger_send_now(event)
    elif cmd == '/status': await trigger_status(event)
    elif cmd == '/add_list': await trigger_add_list(event)
    elif cmd == '/edit_msg': 
        USER_STATE[event.sender_id] = "waiting_msg"
        await event.respond("📝 Send new promo text:")
    elif cmd == '/add_account':
        USER_STATE[event.sender_id] = "waiting_phone"
        await event.respond("📱 Enter Phone (+63...):")
    elif cmd in ['/pause_send', '/pause_sched']:
        global IS_SENDING
        IS_SENDING = False
        await event.respond("⏸️ **Stopped.**")

# --- 3. CALLBACK ROUTER (Handles Buttons) ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data
    if data == b"run_now": await trigger_send_now(event)
    elif data == b"get_status": await trigger_status(event)
    elif data == b"add_users": await trigger_add_list(event)
    # ... Add other button mappings here

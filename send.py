import asyncio, pytz, glob
from datetime import datetime
from telethon import TelegramClient, events, Button

# --- THE UNIVERSAL ROUTER ---
@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def universal_handler(event):
    if not event.text: return
    
    # 1. Clean the command (e.g., /send_now -> send_now)
    cmd = event.text.split()[0].lower().replace('/', '')

    # 2. Map Slash Commands to Internal Logic
    if cmd == 'start':
        await event.respond(GUIDE, buttons=[
            [Button.inline("🚀 Send Now", data="run_now"), Button.inline("📅 Schedule", data="set_sched")],
            [Button.inline("⏸️ Pause Send", data="stop"), Button.inline("⏸️ Pause Sched", data="stop_sched")],
            [Button.inline("📂 Add List", data="add_users"), Button.inline("📝 Edit Msg", data="edit_msg")],
            [Button.inline("📱 Add Acc", data="add_acc"), Button.inline("📊 Status", data="get_status")]
        ])
    
    elif cmd in ['status', 'get_status']:
        await event.respond(await get_stats_report())
        
    elif cmd in ['send_now', 'run_now']:
        asyncio.create_task(shared_outreach_logic(event, "Manual Blast"))
        
    elif cmd in ['add_account', 'add_acc']:
        USER_STATE[event.sender_id] = "waiting_phone"
        await event.respond("📱 **Enter phone number (+63...):**")
        
    elif cmd in ['edit_msg']:
        USER_STATE[event.sender_id] = "waiting_msg"
        await event.respond("📝 **Send the new promotional text:**")
        
    elif cmd in ['add_list', 'add_users']:
        USER_STATE[event.sender_id] = "waiting_list"
        await event.respond("📂 **Paste your @username list:**")

    elif cmd in ['pause_send', 'pause_sched', 'stop', 'stop_sched']:
        global IS_SENDING
        IS_SENDING = False
        await event.respond("⏸️ **All Outreach Paused.**")

# --- CALLBACK HANDLER (For Button Taps) ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    # This just redirects button clicks to the same handler above
    event.text = f"/{event.data.decode('utf-8')}"
    await universal_handler(event)

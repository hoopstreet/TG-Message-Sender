# --- A to B TRIGGER REWIRING ---
import glob, random, asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
# ... (Keep your existing imports and Supabase init here)

@bot.on(events.NewMessage(from_users=ADMIN_ID))
async def universal_router(event):
    if not event.text or not event.text.startswith('/'):
        return

    # Extract the command (e.g., /send_now -> send_now)
    command = event.text.split()[0].lower().replace('/', '')

    # --- THE MAPPING LOGIC ---
    if command == 'start':
        await start(event)
    
    elif command == 'status':
        # Ensure your get_stats_report function is defined above
        report = await get_stats_report()
        await event.respond(report)
    
    elif command == 'send_now':
        await run_outreach(event)
    
    elif command == 'add_list':
        await add_users_handler(event)
    
    elif command == 'edit_msg':
        await edit_msg_init(event)
    
    elif command == 'add_account':
        await add_acc_init(event)
    
    elif command in ['pause_send', 'pause_sched']:
        global IS_SENDING
        IS_SENDING = False
        await event.respond("⏸️ **All operations paused.**")
    
    elif command == 'schedule':
        await event.respond("📅 **Schedule Engine: Please send the time in YYYY-MM-DD HH:MM format.**")
        USER_STATE[event.sender_id] = "waiting_schedule"

# --- Keep all your function definitions (run_outreach, etc.) below this ---

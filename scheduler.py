import asyncio
from datetime import datetime
import pytz

async def scheduler_loop(bot, supabase, PHT):
    print("📅 Scheduler Watchdog Started...")
    while True:
        # Pull pending schedules
        now = datetime.now(PHT).strftime("%Y-%m-%d %H:%M")
        # Logic: If current time matches a 'scheduled_at' column in Supabase
        # then trigger stealth_blast(None)
        await asyncio.sleep(60) # Check every minute

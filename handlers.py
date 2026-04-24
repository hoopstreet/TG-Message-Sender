
@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_promo(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📝 **Send your new Promo Script:**\n(Use 'Hi,' or 'Hi [Name]' as the placeholder for random greetings)")
        r = await conv.get_response()
        supabase.table("bot_settings").update({"current_promo_text": r.text}).eq("id", "production").execute()
        await event.respond("✅ **Promo Script Updated Successfully!**")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account_guide(event):
    guide = (
        "📱 **How to add a new account:**\n\n"
        "1. Open iSH on your iPhone.\n"
        "2. Run: `python3 login.py` (if you have the login script).\n"
        "3. Enter the phone number and OTP.\n"
        "4. Once the `.session` file is created, push it to GitHub.\n\n"
        "Current Active Sessions: " + str(len(glob.glob('*.session'))-1)
    )
    await event.respond(guide)

@bot.on(events.NewMessage(pattern='/start'))
async def start_guide(event):
    guide = (
        "👑 **Weightless Commander v5.3.0**\n\n"
        "/status - 📊 View real-time stats\n"
        "/add_list - 📂 Add & filter leads\n"
        "/edit_msg - 📝 Change promo text\n"
        "/schedule - 📅 Toggle/Set schedule\n"
        "/add_account - 📱 Manage sessions\n"
        "/pause - ⏸️ Stop all activities"
    )
    await event.respond(guide)

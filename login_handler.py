@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Enter Phone Number:**\n(e.g., +639123456789)")
        phone = (await conv.get_response()).text
        
        # Initialize a temporary client for the new session
        # We use the phone number as the session name
        new_client = TelegramClient(phone, API_ID, API_HASH)
        await new_client.connect()
        
        try:
            sent_code = await new_client.send_code_request(phone)
            await conv.send_message("📩 **Enter the OTP (code):**")
            otp = (await conv.get_response()).text
            
            try:
                await new_client.sign_in(phone, otp)
            except errors.SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA detected. Enter Password:**")
                pwd = (await conv.get_response()).text
                await new_client.sign_in(password=pwd)
            
            await new_client.disconnect()
            await event.respond(f"✅ **Account Added Successfully!**\nSession `{phone}.session` is now warm and ready.")
            
        except Exception as e:
            await event.respond(f"❌ **Login Failed:** {str(e)}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account_cmd(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📱 **Enter Phone Number (+63...):**")
        phone = (await conv.get_response()).text.strip().replace(" ", "")
        s_name = f"session_{phone.replace('+', '')}"
        
        client = TelegramClient(s_name, API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **Enter OTP Code:**")
            code = (await conv.get_response()).text
            try:
                await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA Password Required:**")
                pw = (await conv.get_response()).text
                await client.sign_in(password=pw)
            
            # Save to Supabase Cloud Vault
            with open(f"{s_name}.session", "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                supabase.table("saved_sessions").upsert({"phone_number": s_name, "session_data": encoded}).execute()
            
            await client.disconnect()
            await event.respond(f"✅ **Account {phone} linked and backed up to Cloud.**")
        except Exception as e:
            await event.respond(f"❌ **Error:** {e}")

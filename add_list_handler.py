@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📂 **Paste List (@, Links, or Plain):**")
        r = await conv.get_response()
        
        # Regex to catch @user, t.me/user, and plain usernames
        raw_found = re.findall(r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})', r.text)
        found = list(set(raw_found)) # Local dedupe
        
        if not found:
            await event.respond("❌ No valid usernames detected.")
            return

        await event.respond(f"🔍 **Sentinel Filtering {len(found)} leads...**")
        
        # Get existing leads for dedupe
        existing = [x['add_list'] for x in supabase.table("message_campaign").select("add_list").execute().data]
        
        valid_entries = []
        skipped_count = 0

        # Need a session to validate
        all_s = [f for f in glob.glob("*.session") if "bot.session" not in f]
        if not all_s:
            await event.respond("❌ No sessions available for validation.")
            return
            
        async with TelegramClient(all_s[0].replace(".session",""), API_ID, API_HASH) as client:
            for u in found:
                if u in existing:
                    skipped_count += 1
                    continue
                
                try:
                    full = await client(functions.users.GetFullUserRequest(id=u))
                    user = full.users[0]
                    
                    # Filter: Deleted, Bots, or Inactive > 7 days
                    if getattr(user, 'deleted', False) or getattr(user, 'bot', False):
                        skipped_count += 1
                        continue
                    
                    # Status Check
                    status = user.status
                    is_active = False
                    if isinstance(status, types.UserStatusOnline): is_active = True
                    elif isinstance(status, types.UserStatusRecently): is_active = True
                    elif isinstance(status, types.UserStatusLastWeek): is_active = True
                    
                    if is_active:
                        valid_entries.append({"add_list": u, "status": "pending"})
                    else:
                        skipped_count += 1
                except Exception:
                    skipped_count += 1
        
        if valid_entries:
            supabase.table("message_campaign").insert(valid_entries).execute()
        
        await event.respond(f"✅ **Import Complete**\n🚀 Added: {len(valid_entries)}\n🛡️ Filtered (Inactive/Dupes): {skipped_count}")


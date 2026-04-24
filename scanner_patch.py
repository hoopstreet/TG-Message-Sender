        # Need a session to validate (Alphabetical Seniority)
        all_s = sorted([f for f in glob.glob("*.session") if "bot.session" not in f])
        if not all_s:
            await event.respond("❌ No sessions available for scanning.")
            return
            
        async with TelegramClient(all_s[0].replace(".session",""), API_ID, API_HASH) as client:
            for u in found:
                if u in existing:
                    skipped_count += 1
                    continue
                
                try:
                    # Lookup with 1.5s human-like spacing to avoid ban
                    await asyncio.sleep(1.5)
                    full = await client(functions.users.GetFullUserRequest(id=u))
                    user = full.users[0]
                    
                    if getattr(user, 'deleted', False) or getattr(user, 'bot', False):
                        skipped_count += 1
                        continue
                    
                    # 7-Day Activity Logic
                    status = user.status
                    is_active = any([
                        isinstance(status, types.UserStatusOnline),
                        isinstance(status, types.UserStatusRecently),
                        isinstance(status, types.UserStatusLastWeek)
                    ])
                    
                    if is_active:
                        valid_entries.append({"add_list": u, "status": "pending"})
                    else:
                        skipped_count += 1
                except errors.FloodWaitError as e:
                    await event.respond(f"⚠️ **Flood Limit Hit!** Waiting {e.seconds}s...")
                    await asyncio.sleep(e.seconds)
                except Exception:
                    skipped_count += 1

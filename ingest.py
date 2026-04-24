import re
from supabase import create_client
import os

def clean_and_upsert(raw_text, supabase_url, supabase_key):
    supabase = create_client(supabase_url, supabase_key)
    # Extract usernames from links, @tags, or plain text
    pattern = r'(?:https?://t\.me/|@)?([a-zA-Z0-9_]{5,32})'
    usernames = re.findall(pattern, raw_text)
    
    # Get existing to avoid duplicates
    res = supabase.table("message_campaign").select("username").execute()
    existing = {row['username'] for row in res.data}
    
    new_leads = []
    for u in usernames:
        if u not in existing:
            new_leads.append({"username": u, "status": "pending"})
            existing.add(u) # Prevent duplicates within the same batch
            
    if new_leads:
        supabase.table("message_campaign").insert(new_leads).execute()
    return len(new_leads)

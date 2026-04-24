# This is a snippet to replace the update logic in send.py
# We are adding "sender_phone": s_name to the update call
supabase.table("message_campaign").update({
    "status": "success", 
    "sender_phone": s_name 
}).eq("id", lead['id']).execute()

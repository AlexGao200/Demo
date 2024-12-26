Guest sessions & chats work by:

Check if guest session with generated chat matches that of active guest session. If there is a mismatch, the chat guest_session_id is updated to match that of the token. This is handled in chat_service.py in the get_chat_history method.

Guest chats persist for six hours. The CRON job in app.py checks for expires_at field every 30 minutes, and deletes mongodb model instances accordingly. The expiration time for chats is set in the ChatService class. Guest sessions also last 6 hours, and this is specified in the GuestSessionManager and GuestService classes. Guest sessions have a 30 message limit.

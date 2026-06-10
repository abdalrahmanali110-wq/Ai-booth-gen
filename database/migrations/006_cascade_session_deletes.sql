-- Ensure child rows are removed when a chat session is deleted.
-- Run in Supabase SQL editor if session delete fails with FK errors.

ALTER TABLE chat_messages
DROP CONSTRAINT IF EXISTS chat_messages_session_id_fkey;

ALTER TABLE chat_messages
ADD CONSTRAINT chat_messages_session_id_fkey
FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;

ALTER TABLE booth_requirements
DROP CONSTRAINT IF EXISTS booth_requirements_session_id_fkey;

ALTER TABLE booth_requirements
ADD CONSTRAINT booth_requirements_session_id_fkey
FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;

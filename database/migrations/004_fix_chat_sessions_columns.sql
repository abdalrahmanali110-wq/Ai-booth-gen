-- Add missing columns if chat_sessions was created without them
ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS booth_request_id UUID;

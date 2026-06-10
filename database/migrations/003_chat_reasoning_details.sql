ALTER TABLE chat_messages
ADD COLUMN IF NOT EXISTS reasoning_details JSONB;

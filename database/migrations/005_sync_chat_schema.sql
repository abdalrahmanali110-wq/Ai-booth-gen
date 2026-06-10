-- Run this in Supabase SQL Editor to fix chat schema mismatches

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS booth_request_id UUID;

ALTER TABLE chat_messages
ADD COLUMN IF NOT EXISTS reasoning_details JSONB;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS special_requirements JSONB DEFAULT '[]'::jsonb;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS booth_request_id UUID;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

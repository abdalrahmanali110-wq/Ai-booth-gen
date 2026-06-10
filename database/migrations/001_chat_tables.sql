-- Chat sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    title TEXT,
    status TEXT DEFAULT 'active',
    booth_request_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Booth requirements collected via chat
CREATE TABLE IF NOT EXISTS booth_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    industry TEXT,
    event_name TEXT,
    booth_size TEXT,
    budget INTEGER,
    theme TEXT,
    location TEXT,
    special_requirements JSONB DEFAULT '[]'::jsonb,
    booth_request_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
ON chat_messages(session_id);

CREATE INDEX IF NOT EXISTS idx_booth_requirements_session
ON booth_requirements(session_id);

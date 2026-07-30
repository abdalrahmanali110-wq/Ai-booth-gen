-- Lead-gen chat + anonymous quota + 3D jobs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS anonymous_visitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS generation_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id UUID REFERENCES anonymous_visitors(id) ON DELETE SET NULL,
    user_id UUID,
    session_id UUID,
    kind TEXT NOT NULL DEFAULT 'image',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generation_attempts_visitor
ON generation_attempts(visitor_id, kind);

CREATE INDEX IF NOT EXISTS idx_generation_attempts_session
ON generation_attempts(session_id);

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS visitor_id UUID REFERENCES anonymous_visitors(id) ON DELETE SET NULL;

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS claimed_user_id UUID;

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS anon BOOLEAN DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS model_3d_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    session_id UUID,
    source_image_url TEXT NOT NULL,
    source_image_id UUID,
    status TEXT NOT NULL DEFAULT 'PENDING',
    provider TEXT,
    model_url TEXT,
    error TEXT,
    prompt TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_3d_jobs_session
ON model_3d_jobs(session_id);

CREATE INDEX IF NOT EXISTS idx_model_3d_jobs_user
ON model_3d_jobs(user_id);

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    auth_user_id UUID,
    name TEXT,
    email TEXT NOT NULL,
    phone TEXT,
    company TEXT,
    session_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS email TEXT;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS phone TEXT;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS company TEXT;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS auth_user_id UUID;

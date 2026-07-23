-- Booth design questionnaire submissions (guided flow)
CREATE TABLE IF NOT EXISTS booth_designs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    title TEXT DEFAULT 'Booth Design',
    status TEXT DEFAULT 'in_progress',
    answers JSONB DEFAULT '{}'::jsonb,
    compiled_prompt TEXT,
    image_url TEXT,
    image_provider TEXT,
    regenerate_count INTEGER DEFAULT 0,
    contact JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_booth_designs_user
ON booth_designs(user_id);

CREATE INDEX IF NOT EXISTS idx_booth_designs_created
ON booth_designs(created_at DESC);

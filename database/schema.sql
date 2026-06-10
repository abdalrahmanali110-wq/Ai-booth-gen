-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

----------------------------------------------------
-- USERS
----------------------------------------------------

CREATE TABLE users (
    id UUID PRIMARY KEY,
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

----------------------------------------------------
-- BOOTH REQUESTS
----------------------------------------------------
CREATE TABLE booth_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    industry VARCHAR(100) NOT NULL,

    booth_theme VARCHAR(100),

    booth_size VARCHAR(50),

    colors TEXT,

    prompt TEXT NOT NULL,

    status VARCHAR(50) DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_booth_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

----------------------------------------------------
-- GENERATED IMAGES
----------------------------------------------------
CREATE TABLE generated_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    booth_request_id UUID NOT NULL,

    image_url TEXT NOT NULL,

    image_provider VARCHAR(50),

    prompt_used TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_generated_image_request
        FOREIGN KEY (booth_request_id)
        REFERENCES booth_requests(id)
        ON DELETE CASCADE
);

----------------------------------------------------
-- SUPPLIER RECOMMENDATIONS
----------------------------------------------------
CREATE TABLE supplier_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    booth_request_id UUID NOT NULL,

    company_name VARCHAR(255) NOT NULL,

    website_url TEXT,

    phone_number VARCHAR(100),

    location VARCHAR(255),

    description TEXT,

    source VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_supplier_request
        FOREIGN KEY (booth_request_id)
        REFERENCES booth_requests(id)
        ON DELETE CASCADE
);

----------------------------------------------------
-- INDEXES
----------------------------------------------------
CREATE INDEX idx_booth_requests_user
ON booth_requests(user_id);

CREATE INDEX idx_generated_images_request
ON generated_images(booth_request_id);

CREATE INDEX idx_supplier_request
ON supplier_recommendations(booth_request_id);

----------------------------------------------------
-- CHAT SESSIONS
----------------------------------------------------
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    title TEXT,
    status TEXT DEFAULT 'active',
    booth_request_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

----------------------------------------------------
-- CHAT MESSAGES
----------------------------------------------------
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    reasoning_details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

----------------------------------------------------
-- BOOTH REQUIREMENTS (from chat agent)
----------------------------------------------------
CREATE TABLE booth_requirements (
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

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_booth_requirements_session ON booth_requirements(session_id);

----------------------------------------------------
-- PROJECT PROPOSALS
----------------------------------------------------
CREATE TABLE project_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_request_id UUID REFERENCES booth_requests(id) ON DELETE CASCADE,
    proposal_title TEXT,
    proposal_summary TEXT,
    estimated_budget INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_project_proposals_booth ON project_proposals(booth_request_id);
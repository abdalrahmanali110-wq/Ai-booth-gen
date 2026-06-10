CREATE TABLE IF NOT EXISTS project_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booth_request_id UUID REFERENCES booth_requests(id) ON DELETE CASCADE,
    proposal_title TEXT,
    proposal_summary TEXT,
    estimated_budget INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_proposals_booth
ON project_proposals(booth_request_id);

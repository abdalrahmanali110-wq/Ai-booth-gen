-- Extra intake fields from chatbox prompt-pattern guidance
ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS brand_name TEXT;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS open_sides TEXT;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS brand_colors TEXT;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS slogan TEXT;

ALTER TABLE booth_requirements
ADD COLUMN IF NOT EXISTS event_date TEXT;

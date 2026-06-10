
-- 1. Create a table for auto-learning metric keyword mapping
CREATE TABLE IF NOT EXISTS metric_keywords (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    category TEXT,
    subcategory TEXT,
    short_key TEXT,
    source_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Update metric_definitions insert logic (in code):
-- INSERT INTO metric_definitions (...) 
-- ON CONFLICT (unified_key) DO UPDATE 
-- SET tags = EXCLUDED.tags, source_keys = EXCLUDED.source_keys;

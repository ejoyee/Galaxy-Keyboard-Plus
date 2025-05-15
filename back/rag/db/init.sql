CREATE TABLE IF NOT EXISTS image_keywords (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    access_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    caption TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 검색 최적화를 위한 인덱스 (선택 사항)
CREATE INDEX idx_user_access ON image_keywords(user_id, access_id);
CREATE INDEX idx_keyword ON image_keywords(keyword);

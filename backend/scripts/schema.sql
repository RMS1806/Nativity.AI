-- Nativity.ai PostgreSQL schema
-- Run via: python scripts/setup_postgres.py

CREATE TABLE IF NOT EXISTS videos (
    job_id            TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    input_file        TEXT NOT NULL DEFAULT '',
    target_language   TEXT NOT NULL DEFAULT '',
    status            TEXT NOT NULL DEFAULT 'pending',
    progress          INTEGER DEFAULT 0,
    message           TEXT,
    error_message     TEXT,
    output_url        TEXT,
    output_s3_key     TEXT,
    whatsapp_url      TEXT,
    subtitle_s3_key   TEXT,
    file_size_mb      NUMERIC(10,2),
    segments_count    INTEGER,
    words_localized   INTEGER,
    draft_segments    TEXT,
    approved_segments TEXT,
    cultural_report   TEXT,
    cultural_analysis TEXT,
    created_at        TEXT,
    updated_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_videos_user_id    ON videos (user_id);
CREATE INDEX IF NOT EXISTS idx_videos_status     ON videos (status);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos (created_at DESC);

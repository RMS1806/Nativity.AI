-- Nativity.ai — PostgreSQL schema
-- One row per localization job. JSON blobs are stored as TEXT (json.dumps output)
-- to match the previous store, so application code reads them with json.loads.

CREATE TABLE IF NOT EXISTS videos (
    job_id            TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    target_language   TEXT,
    input_file        TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    message           TEXT NOT NULL DEFAULT '',
    progress          INTEGER,
    error_message     TEXT,

    output_url        TEXT,
    output_s3_key     TEXT,
    subtitle_s3_key   TEXT,
    whatsapp_url      TEXT,
    file_size_mb      DOUBLE PRECISION,
    segments_count    INTEGER,
    words_localized   INTEGER,

    cultural_report   TEXT,   -- json.dumps(dict)
    cultural_analysis TEXT,   -- json.dumps(list)
    draft_segments    TEXT,   -- json.dumps(list)

    created_at        TEXT,   -- ISO-8601 string, e.g. 2026-06-21T10:00:00Z
    updated_at        TEXT
);

-- Fast "my history, newest first"
CREATE INDEX IF NOT EXISTS idx_videos_user_created ON videos (user_id, created_at DESC);

-- Fast "active jobs" scans
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos (status);

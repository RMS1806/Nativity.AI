-- Nativity.ai PostgreSQL schema
-- Run via: python scripts/setup_postgres.py
-- Run migrations via: python scripts/migrate.py

-- ── Core table (original) ────────────────────────────────────────────────────
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

-- ── Migration 1: audio-dub support ──────────────────────────────────────────
-- job_type: 'localization' (default) | 'audio_dub'
-- dub_audio_s3_key: R2 key for the dubbed .aac file produced by the audio-only pipeline
ALTER TABLE videos ADD COLUMN IF NOT EXISTS job_type         TEXT DEFAULT 'localization';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS dub_audio_s3_key TEXT;

-- ── Migration 2: shorts support (Phase 2 — not yet implemented) ──────────────
-- short_id links a localization job back to its source short clip.
-- If NULL → regular job (shown in Dashboard).
-- If set  → short localization (shown in Shorts tab under the parent short).
ALTER TABLE videos ADD COLUMN IF NOT EXISTS short_id TEXT;
CREATE INDEX IF NOT EXISTS idx_videos_short_id ON videos (short_id);
CREATE INDEX IF NOT EXISTS idx_videos_job_type ON videos (job_type);

-- shorts table: one row per extracted clip
-- source_job_id → the videos.job_id of the video this clip came from
CREATE TABLE IF NOT EXISTS shorts (
    short_id        TEXT PRIMARY KEY,
    source_job_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    title           TEXT,
    start_time_s    NUMERIC(10,3),
    end_time_s      NUMERIC(10,3),
    s3_key          TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    description     TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shorts_source_job ON shorts (source_job_id);
CREATE INDEX IF NOT EXISTS idx_shorts_user_id    ON shorts (user_id);

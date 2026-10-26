-- Run as the database OWNER (not the app user), connected to the shortly database:
--   sudo -u postgres psql -d shortly -f db/schema.sql
-- Safe to re-run.

CREATE TABLE IF NOT EXISTS links (
    id          bigserial    PRIMARY KEY,
    code        varchar(16)  NOT NULL UNIQUE,
    target_url  text         NOT NULL,
    clicks      bigint       NOT NULL DEFAULT 0,
    created_at  timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS links_created_at_idx ON links (created_at DESC);

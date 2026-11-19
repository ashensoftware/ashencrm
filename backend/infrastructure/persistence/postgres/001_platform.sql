-- Esquema de plataforma para Postgres. La cola usa FOR UPDATE SKIP LOCKED
-- desde el código, no desde esta migración.

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    created_at BIGINT NOT NULL,
    started_at BIGINT,
    finished_at BIGINT,
    cancel_requested_at BIGINT,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS pipeline_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    sequence INTEGER NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    available_at BIGINT NOT NULL,
    heartbeat_at BIGINT,
    locked_by TEXT,
    error_code TEXT,
    safe_error_message TEXT,
    result_json JSONB,
    UNIQUE (run_id, sequence)
);

CREATE INDEX IF NOT EXISTS pipeline_steps_claim_idx
    ON pipeline_steps (status, available_at, id);

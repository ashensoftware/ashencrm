-- Esquema de plataforma aplicado en el proyecto cvvjhacipntbjcmzqfnk.
-- RLS queda activo y anon/authenticated no tienen privilegios.
-- El rol de servicio de Supabase es el único que puede leer estas tablas.

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

CREATE TABLE IF NOT EXISTS pipeline_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    step_id TEXT,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS businesses (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    domain TEXT,
    phone_e164 TEXT,
    status TEXT NOT NULL,
    merged_into_id TEXT,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE (provider, external_id)
);

CREATE TABLE IF NOT EXISTS field_observations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id TEXT NOT NULL REFERENCES businesses(id),
    field_name TEXT NOT NULL,
    value_json JSONB NOT NULL,
    provider TEXT NOT NULL,
    observed_at BIGINT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_connections (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    label TEXT NOT NULL,
    auth_method TEXT NOT NULL,
    status TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 0,
    budget_usd DOUBLE PRECISION,
    external_workspace TEXT,
    scopes TEXT,
    secret_ciphertext TEXT,
    secret_last4 TEXT,
    token_expires_at BIGINT,
    last_check_at BIGINT,
    last_error TEXT,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppression_entries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    normalized_contact TEXT NOT NULL,
    channel TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    UNIQUE (normalized_contact, channel)
);

CREATE TABLE IF NOT EXISTS outreach_consents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    normalized_contact TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    granted_at BIGINT,
    UNIQUE (normalized_contact, channel)
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    business_id TEXT,
    campaign_id TEXT,
    status TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    body_preview TEXT,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject TEXT NOT NULL,
    role TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    created_at BIGINT NOT NULL
);

DO $$
DECLARE
    tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'pipeline_runs', 'pipeline_steps', 'pipeline_events', 'businesses',
        'field_observations', 'provider_connections', 'suppression_entries',
        'outreach_consents', 'outreach_messages', 'audit_log'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
        EXECUTE format('REVOKE ALL ON TABLE %I FROM PUBLIC, anon, authenticated', tbl);
    END LOOP;
END $$;

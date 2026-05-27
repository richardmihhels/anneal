CREATE TABLE IF NOT EXISTS traces (
    id          TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL DEFAULT 'org_demo',
    agent_id    TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    outcome     TEXT NOT NULL DEFAULT 'unknown',
    metadata    JSONB NOT NULL DEFAULT '{}'
);

ALTER TABLE traces
    ADD COLUMN IF NOT EXISTS organization_id TEXT NOT NULL DEFAULT 'org_demo';

CREATE INDEX IF NOT EXISTS traces_organization_id_idx ON traces (organization_id);
CREATE INDEX IF NOT EXISTS traces_agent_id_idx  ON traces (agent_id);
CREATE INDEX IF NOT EXISTS traces_created_at_idx ON traces (created_at DESC);
CREATE INDEX IF NOT EXISTS traces_outcome_idx    ON traces (outcome);

CREATE TABLE IF NOT EXISTS alarms (
    id                   TEXT PRIMARY KEY,
    organization_id      TEXT NOT NULL DEFAULT 'org_demo',
    agent_id             TEXT NOT NULL,
    category             TEXT NOT NULL,
    baseline_rate        DOUBLE PRECISION NOT NULL,
    current_rate         DOUBLE PRECISION NOT NULL,
    window_hours         INT NOT NULL,
    affected_trace_count INT NOT NULL,
    first_detected       TIMESTAMPTZ NOT NULL,
    cause_hypothesis     TEXT NOT NULL,
    notified             BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS alarms_agent_id_category_idx ON alarms (agent_id, category, first_detected DESC);

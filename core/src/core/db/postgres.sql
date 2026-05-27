CREATE TABLE IF NOT EXISTS traces (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    outcome     TEXT NOT NULL DEFAULT 'unknown',
    metadata    JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS traces_agent_id_idx  ON traces (agent_id);
CREATE INDEX IF NOT EXISTS traces_created_at_idx ON traces (created_at DESC);
CREATE INDEX IF NOT EXISTS traces_outcome_idx    ON traces (outcome);

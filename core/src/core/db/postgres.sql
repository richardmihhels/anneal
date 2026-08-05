CREATE TABLE IF NOT EXISTS traces (
    organization_id TEXT NOT NULL DEFAULT 'org_demo',
    id          TEXT NOT NULL,
    agent_id    TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    outcome     TEXT NOT NULL DEFAULT 'unknown',
    metadata    JSONB NOT NULL DEFAULT '{}',
    payload     JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (organization_id, id)
);

ALTER TABLE traces
    ADD COLUMN IF NOT EXISTS organization_id TEXT NOT NULL DEFAULT 'org_demo';
ALTER TABLE traces
    ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}';

-- Older installations used a global trace-id primary key. Migrate that key
-- in place so one organization can neither block nor overwrite another
-- organization's externally supplied trace id.
DO $$
DECLARE
    legacy_primary_key TEXT;
BEGIN
    SELECT constraint_name
      INTO legacy_primary_key
      FROM information_schema.table_constraints
     WHERE table_schema = current_schema()
       AND table_name = 'traces'
       AND constraint_type = 'PRIMARY KEY'
       AND constraint_name IN (
           SELECT constraint_name
             FROM information_schema.key_column_usage
            WHERE table_schema = current_schema()
              AND table_name = 'traces'
            GROUP BY constraint_name
           HAVING array_agg(column_name::TEXT ORDER BY ordinal_position) = ARRAY['id']::TEXT[]
       );

    IF legacy_primary_key IS NOT NULL THEN
        EXECUTE format('ALTER TABLE traces DROP CONSTRAINT %I', legacy_primary_key);
        ALTER TABLE traces ADD PRIMARY KEY (organization_id, id);
    END IF;
END $$;

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

CREATE TABLE IF NOT EXISTS optimization_runs (
    id                  TEXT PRIMARY KEY,
    organization_id     TEXT NOT NULL DEFAULT 'org_demo',
    agent_id            TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    status              TEXT NOT NULL,
    cluster_ids         JSONB NOT NULL DEFAULT '[]',
    proposed_change_ids JSONB NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS optimization_runs_org_created_idx
    ON optimization_runs (organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS run_events (
    id       TEXT PRIMARY KEY,
    run_id   TEXT NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    stage    TEXT NOT NULL,
    event    TEXT NOT NULL,
    message  TEXT NOT NULL,
    ts       TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS run_events_run_id_ts ON run_events(run_id, ts);

CREATE TABLE IF NOT EXISTS failure_clusters (
    id                      TEXT PRIMARY KEY,
    optimization_run_id     TEXT NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    label                   TEXT NOT NULL,
    description             TEXT NOT NULL,
    trace_ids               JSONB NOT NULL DEFAULT '[]',
    size                    INT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL,
    representative_trace_id TEXT
);

CREATE INDEX IF NOT EXISTS failure_clusters_run_idx ON failure_clusters (optimization_run_id);

CREATE TABLE IF NOT EXISTS proposed_changes (
    id                  TEXT PRIMARY KEY,
    optimization_run_id TEXT NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    target              TEXT NOT NULL,
    before              TEXT NOT NULL,
    after               TEXT NOT NULL,
    rationale           TEXT NOT NULL,
    eval_result_id      TEXT
);

CREATE INDEX IF NOT EXISTS proposed_changes_run_idx ON proposed_changes (optimization_run_id);

CREATE TABLE IF NOT EXISTS eval_results (
    id                   TEXT PRIMARY KEY,
    optimization_run_id  TEXT REFERENCES optimization_runs(id) ON DELETE CASCADE,
    proposed_change_id   TEXT,
    run_at               TIMESTAMPTZ NOT NULL,
    baseline_score       DOUBLE PRECISION NOT NULL,
    candidate_score      DOUBLE PRECISION NOT NULL,
    delta                DOUBLE PRECISION NOT NULL,
    p_value              DOUBLE PRECISION NOT NULL,
    sample_size          INT NOT NULL,
    passed               BOOLEAN NOT NULL,
    judge_agreement_rate DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS eval_results_run_id_idx ON eval_results (optimization_run_id);
CREATE INDEX IF NOT EXISTS eval_results_run_at_idx ON eval_results (run_at DESC);

CREATE TABLE IF NOT EXISTS weekly_digests (
    id                   TEXT PRIMARY KEY,
    optimization_run_id  TEXT NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    organization_id      TEXT NOT NULL DEFAULT 'org_demo',
    agent_id             TEXT NOT NULL,
    week_start           TIMESTAMPTZ NOT NULL,
    week_end             TIMESTAMPTZ NOT NULL,
    generated_at         TIMESTAMPTZ NOT NULL,
    subject              TEXT NOT NULL,
    summary              TEXT NOT NULL,
    pr_shipped           BOOLEAN NOT NULL,
    pr_urls              JSONB NOT NULL DEFAULT '[]',
    health_direction     TEXT NOT NULL,
    alarm_ids            JSONB NOT NULL DEFAULT '[]',
    email_body           TEXT NOT NULL,
    page_body            TEXT NOT NULL,
    UNIQUE (optimization_run_id)
);

CREATE INDEX IF NOT EXISTS weekly_digests_org_week_idx
    ON weekly_digests (organization_id, week_end DESC);

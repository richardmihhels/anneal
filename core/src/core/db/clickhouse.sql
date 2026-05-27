CREATE TABLE IF NOT EXISTS spans (
    trace_id     String,
    span_id      String,
    organization_id String DEFAULT 'org_demo',
    agent_id     String,
    session_id   String,
    name         String,
    start_time   DateTime64(3, 'UTC'),
    end_time     DateTime64(3, 'UTC'),
    duration_ms  Float64,
    input        String,
    output       String,
    error        Nullable(String),
    metadata     String,
    ingested_at  DateTime64(3, 'UTC') DEFAULT now64()
) ENGINE = MergeTree()
ORDER BY (organization_id, agent_id, trace_id, start_time)
TTL ingested_at + INTERVAL 1 YEAR;

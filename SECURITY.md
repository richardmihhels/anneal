# Security Policy

## Supported version

Security fixes are applied to the latest commit on `main`. This project has not
yet declared a stable release line.

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** button in the repository Security
tab. Do not open a public issue for authentication bypasses, secret exposure,
cross-organization data access, or unsafe prompt publication behavior.

Include the affected component, reproduction steps, impact, and any suggested
mitigation. You should receive an acknowledgement within seven days.

## Security boundaries

- Production ingestion fails closed unless an organization API key is configured.
- The dashboard calls the core API from the server; API keys are never sent to the browser.
- Trace payloads are scrubbed before persistence.
- Candidate prompt changes must clear calibration, holdout, and significance gates.
- Demo mode uses synthetic data and must not be exposed as a production deployment.

## Dependency-audit exception

`dspy` currently depends on `diskcache==5.6.3`, for which
`PYSEC-2026-2447` has no patched release. The issue requires an attacker to
write a crafted entry into a cache directory that the application later reads.
Anneal disables DSPy's disk cache before its first model call and uses only the
process-local memory cache, so the vulnerable deserialization path is not used.
CI ignores only this advisory and continues to fail on every other production
dependency finding, including optional SDK extras. Remove the exception when a
patched `diskcache` release is available.

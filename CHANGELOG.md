# Changelog

All notable changes will be documented here. This project follows Semantic
Versioning once the first public release is tagged.

## Unreleased

### Added

- Authenticated, organization-scoped ingestion and dashboard APIs.
- Postgres-backed trace replay and persistence for clusters, changes, evals, and digests.
- Validated worker configuration and an HTTP agent replay contract.
- Explicit offline demo and fail-closed production modes.
- Full CI coverage for Python, dashboard, browser tests, audits, and container builds.
- A typed LangChain/LangGraph SDK with asynchronous trace delivery and secret scrubbing.

### Changed

- Upgraded the dashboard to Next.js 16.
- Made local builds independent of remote font downloads.
- Changed Azure deployment to an explicit manual workflow using immutable image tags.
- Enforced tenant-safe persistence for externally supplied trace and agent identifiers.
- Hardened evaluation gates with a 10-sample minimum and family-wise error correction.
- Made publishing configuration and GitHub write failures fail the optimization run.
- Audited optional SDK dependencies and raised vulnerable transitive packages to patched releases.

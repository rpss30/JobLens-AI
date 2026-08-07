# Test Suite Audit

Last measured: 2026-08-07

## Current State

JobLens has a large, deterministic pytest suite. It is useful today, but the
next improvement should be better layering rather than more tests for its own
sake.

Measured from `feature/test-suite-audit` after merging current `main`:

| Measure | Result |
| --- | --- |
| Collected tests | 399 |
| Test files | 62 |
| Full suite runtime | 399 passed in 14.67s pytest time, 17.09s wall time |
| Coverage command | `pytest -q --cov=src --cov-report=term-missing --cov-report=xml` |
| Source coverage | 69% |
| CI shape | One GitHub Actions test job running the full suite with coverage |
| Test layout | Flat `tests/` directory |
| Browser E2E tests | None |
| Real PostgreSQL tests | None found |

Warnings observed:

- `StarletteDeprecationWarning` from FastAPI `TestClient`.
- `DeprecationWarning` from `google.genai.types` on Python 3.14.

## Approximate Distribution

These categories are approximate because the suite is not yet marked by layer.
They are based on test names, imports, fixtures, and representative file reads.

| Layer | Current signal |
| --- | --- |
| Unit and service behavior | Strong coverage for matching, search, resume analysis, skill normalization, location rules, validation helpers, and data transformations. |
| API contract tests | Good FastAPI `TestClient` coverage for success paths, validation, rate limiting, CORS, dataset operations, and sanitized failures. Many API tests monkeypatch service or database boundaries. |
| Provider boundary tests | Good unit-level tests for Greenhouse, Lever, Ashby, career page fetching, and normalization edge cases. Fixtures are mostly inline and do not yet form a shared contract library. |
| LLM/extraction boundary tests | Good deterministic tests for Groq/Gemini response parsing, fallback behavior, empty extraction handling, and pipeline metadata around extraction. No live provider calls in normal CI. |
| Pipeline/script tests | Good script-level coverage for Canada fetch/build workflows, validation summaries, refresh workflow behavior, and production ingestion scheduling. |
| SQLAlchemy persistence tests | Repository behavior is mostly exercised through `FakeSession` and `FakeSeedSession`, not a real PostgreSQL database. |
| Django operations tests | Useful `pytest-django` coverage exists, but test settings use in-memory SQLite. |
| Operations/deployment tests | Strong script and artifact checks for backups, monitoring, security scans, secret rotation, readiness, Lightsail planning, and production compose/deployment runbooks. |
| Browser E2E | No Playwright/Selenium layer currently. |

## Slowest Tests

The suite is fast overall. The slowest test is infrastructure validation, not
business logic.

| Duration | Test |
| --- | --- |
| 3.65s | `tests/test_lightsail_deployment_plan.py::test_lightsail_terraform_validates_when_cli_is_available` |
| 0.95s | `tests/test_operations_monitoring.py::test_log_aggregation_writes_normalized_jsonl_without_real_services` |
| 0.58s | `tests/test_security_scanning.py::test_security_scan_script_runs_fake_dependency_and_static_scans` |
| 0.53s | `tests/test_secret_rotation.py::test_parameter_store_renderer_writes_private_env_and_audits` |
| 0.41s | `tests/test_secret_rotation.py::test_parameter_store_renderer_dry_run_detects_missing_required_key` |

No immediate speed split is required before adding database tests. Once a real
PostgreSQL layer lands, CI should split fast tests from database and workflow
tests.

## Heavily Mocked Areas

- `tests/test_database_repository.py` uses fake SQLAlchemy sessions for dataset,
  processed job, skill, extraction result, and ingestion run persistence.
- `tests/test_api.py` uses FastAPI `TestClient`, but many database-backed
  endpoint tests monkeypatch service/repository calls.
- Provider clients monkeypatch `requests.get`, which is appropriate, but shared
  realistic response fixtures would make contract intent clearer.
- LLM tests stub extractor boundaries, which is correct for normal CI. Future
  integration tests should keep that external boundary stubbed while exercising
  real persistence and diagnostics behavior.

## Duplication And Consolidation Opportunities

Keep these tests for now, but revisit them after stronger integration coverage
exists:

- Repository parsing and naming helpers in `tests/test_database_repository.py`
  could be grouped with parameterized examples where several tests differ only
  by input value.
- API dataset list, get, rename, and delete cases repeat a pattern of
  monkeypatch service call, request, status assertion, and JSON assertion. Some
  should remain contract tests; others can shrink once real database-backed API
  integration tests exist.
- Provider client tests repeat the same fake response structure across
  Greenhouse, Lever, and Ashby. A shared fixture shape would reduce drift while
  preserving provider-specific contract assertions.
- Secret/readiness/monitoring script tests are valuable, but some shell-output
  checks may be better expressed as status JSON contract checks.

No removals should happen in this audit branch. Deletions should only follow a
reviewed branch that replaces low-level mocked coverage with stronger behavior
coverage.

## Coverage Observations

Coverage is useful as a signal, not a target.

Current `src` coverage is 69%. Important low-coverage areas:

- `src/dashboard/app.py`: 10%
- `src/dashboard/components.py`: 10%
- `src/dashboard/charts.py`: 23%
- `src/database/db.py`: 43%
- `src/database/init_db.py`: 0%
- live extractor call paths in `src/skill_extraction/groq_extractor.py` and
  `src/skill_extraction/gemini_extractor.py`: about 69-71%

The dashboard coverage gap should not automatically trigger many unit tests.
If the dashboard remains important, cover a few high-value user flows through a
browser layer after deterministic fixtures exist. The database gaps should be
addressed first through PostgreSQL integration and migration checks.

## Keep

- Matching, weighted scoring, search, and skill-gap behavior tests.
- Resume privacy and failure-path regression tests.
- FastAPI request/response contract tests.
- Provider normalization tests for missing and unusual fields.
- LLM parsing and fallback tests that avoid live provider calls.
- Pipeline summary, validation, and refresh workflow tests.
- Operations/deployment script tests that protect production runbooks.

## Consolidate

- Repeated helper tests where a parameterized table would protect the same
  behavior with less noise.
- Repeated API service monkeypatch tests after database-backed API integration
  tests are available.
- Repeated provider client fake-response setup into shared provider fixtures.

## Replace

- Some fake SQLAlchemy session tests should be replaced by PostgreSQL-backed
  persistence tests for uniqueness, relationships, transactions, migrations,
  ingestion run metadata, extraction result persistence, and query behavior.
- Some API tests that mock the database should be replaced by API integration
  tests against a seeded test database.
- Some script tests should be replaced by pipeline integration tests that use
  provider fixtures, real normalization, real deduplication, and real
  persistence while still stubbing network and LLM boundaries.

## Remove

No tests should be removed in this audit branch.

Potential removals should be considered only after replacement coverage exists
and should focus on tests that assert implementation details rather than user,
API, database, or pipeline behavior.

## Add

Highest-value additions for later branches:

1. PostgreSQL integration foundation.
2. Alembic migration validation against a clean PostgreSQL database.
3. Database-backed API integration tests for dataset and analysis flows.
4. Provider contract fixtures for Greenhouse, Lever, and Ashby.
5. Pipeline integration tests for provider fixture to normalized posting to
   deduplication to PostgreSQL persistence.
6. Extraction failure integration tests that persist empty or failed extraction
   attempts and expose them through diagnostics.
7. A small E2E suite for ingestion, candidate analysis, duplicate handling, and
   failure diagnostics.
8. Browser E2E only after selecting a stable UI workflow and deterministic seed
   data.

## Target Test Strategy

The target is not a larger test count. The target is a clearer risk-based
distribution:

- Fast unit tests for deterministic transformations and scoring.
- API contract tests for externally visible FastAPI behavior.
- Real PostgreSQL integration tests for persistence behavior that mocks cannot
  validate.
- Provider contract tests using deterministic external-response fixtures.
- Pipeline integration tests that cross normalization, deduplication,
  extraction handling, and persistence.
- Failure-path tests that prove bad provider or extraction behavior becomes
  diagnosable.
- A small E2E layer for critical workflows.

## Recommended Branch Sequence

1. `feature/postgres-integration-tests`
   Add disposable PostgreSQL test infrastructure, migration validation, and a
   small set of persistence tests for datasets, postings, skills, extraction
   results, and ingestion run metadata.

2. `feature/api-contract-tests`
   Keep FastAPI contract coverage, but add database-backed contract cases for
   dataset and analysis endpoints. Avoid duplicating existing unit-level service
   tests.

3. `feature/provider-contract-tests`
   Add shared provider fixtures for Greenhouse, Lever, and Ashby. Cover
   pagination, missing optional fields, malformed payloads, location shapes, and
   provider-specific normalization.

4. `feature/pipeline-integration-tests`
   Add provider-fixture to normalization to deduplication to PostgreSQL
   workflows. Add extraction success and empty-result flows with the LLM
   boundary stubbed.

5. `feature/end-to-end-tests`
   Add a small number of critical workflows, likely ingestion, duplicate
   ingestion, candidate analysis, invalid API request, and extraction failure
   diagnostics.

6. `feature/testing-ci-pipeline`
   Split CI into understandable layers after markers and database infrastructure
   exist. Keep the fast feedback path short.

7. `feature/test-suite-cleanup`
   Consolidate or remove low-value mocked tests only after stronger integration
   coverage has landed.

## Marker Rollout

This branch registers markers, but it intentionally does not mass-mark existing
tests. Markers should be applied when each layer is clarified:

- `unit`
- `contract`
- `integration`
- `db`
- `e2e`
- `slow`

Mass-marking the current flat suite would create false precision. Apply markers
as files are moved, rewritten, or added in focused branches.

## CI Recommendation

Keep the current full-suite CI job until PostgreSQL and E2E layers exist. Once
they do, split into:

1. Fast unit and contract tests.
2. PostgreSQL integration and migration tests.
3. Pipeline and failure-path integration tests.
4. Small E2E/browser workflow tests, if added.
5. Existing security scan and container validation.

CI should remain deterministic and must not call live provider APIs, live LLM
providers, production databases, or production cloud resources.

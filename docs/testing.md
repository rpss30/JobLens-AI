# Testing Strategy

JobLens AI uses an offline-first pytest suite. Tests should not call live ATS
boards, LLM providers, cloud services, or PostgreSQL unless a test explicitly
mocks or isolates that dependency.

## Test Layers

- Unit tests cover matching, search, resume analysis, skill extraction schemas,
  location normalization, and ingestion helpers.
- API tests use FastAPI `TestClient` and monkeypatch database access where
  needed, including request validation, CORS, and rate limiting behavior.
- Pipeline tests validate fetch/build summaries, ingestion metrics, duplicate
  detection, malformed records, and workflow behavior.
- Dashboard service tests cover filtering, uploads, reports, search modes, and
  candidate-facing summaries without launching a browser.
- Reliability regression tests focus on failure paths such as malformed CSVs,
  invalid API inputs, duplicate postings, empty result sets, and resume privacy.

The suite is moving toward explicit pytest markers for the long-term layers:

```text
unit
contract
integration
db
e2e
slow
```

Those markers are intentionally registered before the whole suite is
reorganized. New tests should use them when the layer is clear, but existing
files should not be mass-marked mechanically. The current test-suite audit is
documented in [testing-strategy-audit.md](testing-strategy-audit.md).

## Fixtures

Shared fixtures live in:

```text
tests/conftest.py
```

They provide representative processed jobs, resume text, API payloads, and saved
analysis data. New tests should prefer these fixtures over hand-rolled records
unless the test needs a very specific edge case.

## Running Tests

Run the full suite:

```bash
pytest
```

Run a focused slice:

```bash
pytest tests/test_reliability_regressions.py tests/test_api.py -q
```

Run a marker slice once tests in that layer are marked:

```bash
pytest -m unit
pytest -m contract
pytest -m integration
pytest -m db
pytest -m e2e
pytest -m slow
```

Run coverage locally after installing dependencies:

```bash
pytest --cov=src --cov-report=term-missing --cov-report=xml
```

## CI

The main test workflow installs dependencies, runs pytest with source coverage,
prints missing-line coverage to the job log, and uploads `coverage.xml` as an
artifact. The security scan workflow runs dependency, static Python, and
container image scans and uploads JSON reports for review. The Canada snapshot
refresh workflow still runs the full pytest suite after rebuilding the
candidate snapshot, but it does not upload coverage because its primary purpose
is data quality gating.

## Reliability Rules

- Tests must not require live external APIs.
- LLM behavior should be tested with mocked responses or deterministic fallback
  paths.
- Resume tests must not persist or echo raw resume text.
- CSV upload tests should cover malformed rows, missing columns, blank values,
  empty inputs, unsafe extensions, oversized files, and row-count limits.
- Ingestion tests should cover missing required fields and duplicate stable
  identifiers such as `job_id` and `source_url`.

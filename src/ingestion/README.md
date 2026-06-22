## Data Ingestion

JobLens AI uses first-party employer career data for its packaged Canada jobs
snapshot. The source registry currently combines public Greenhouse, Lever, and
Ashby job-board endpoints from employers hiring in Canada.

### Current Data Flow

```text
First-party employer job boards
        |
        v
scripts/fetch_canada_jobs.py
        |
        v
data/raw/canada_jobs.csv
        |
        v
scripts/build_canada_jobs_snapshot.py
        |
        v
data/processed/canada_jobs_snapshot.csv
```

The fetch step keeps current technical postings that explicitly support a
Canadian city, province, or Canada-wide remote work. Locations are normalized,
expired postings are removed when expiry metadata is available, and duplicate
jobs are removed before snapshot selection.

The snapshot step selects a role-, employer-, and location-balanced subset and
uses Groq on each complete first-party description. Successful rows are saved
incrementally so interrupted runs can resume without repeating completed calls.
On later refreshes, unchanged descriptions reuse their prior Groq extraction
while retaining current source metadata. Changed and new descriptions are sent
to Groq again. Deterministic extraction is retained only as an emergency
fallback.

### Weekly Refresh

The `Refresh Canada Jobs Snapshot` GitHub Actions workflow runs every Monday at
14:17 UTC and can also be started manually. It:

1. Fetches current postings from the configured employer boards.
2. Builds a candidate snapshot with Groq-first skill extraction.
3. Validates job count, baseline retention, employer and location diversity,
   role coverage, source diversity, freshness, URL integrity, and Groq coverage.
4. Runs the full test suite against the candidate snapshot.
5. Opens a pull request when the committed snapshot changed.

The workflow never writes directly to `main`. A maintainer reviews and merges
each refresh pull request. Repository setup requires a GitHub Actions secret
named `GROQ_API_KEY` and permission for GitHub Actions to create pull requests.

To run the same flow locally:

```bash
python scripts/fetch_canada_jobs.py
python scripts/build_canada_jobs_snapshot.py
python scripts/validate_canada_jobs_snapshot.py \
  --candidate-path data/processed/canada_jobs_snapshot.csv
pytest
```

### Supporting Workflows

- `scripts/fetch_greenhouse_jobs.py` fetches and normalizes public job postings.
- `scripts/fetch_canada_jobs.py` builds the Canada-only raw posting set.
- `scripts/build_canada_jobs_snapshot.py` creates the packaged Groq-enriched snapshot.
- `scripts/validate_canada_jobs_snapshot.py` blocks low-quality snapshot replacements.
- `scripts/process_greenhouse_jobs.py` applies deterministic processing.
- `scripts/process_greenhouse_jobs_ai_first.py` runs the AI-first extraction experiment.
- `scripts/build_greenhouse_ai_demo_jobs.py` builds the curated dashboard demo.
- `scripts/extract_skills_greenhouse_gemini.py` compares Gemini extraction on a small sample.

External APIs and LLMs are not required at dashboard runtime. The committed
snapshot keeps the application stable while retaining current first-party
source URLs, refresh metadata, and realistic job descriptions.

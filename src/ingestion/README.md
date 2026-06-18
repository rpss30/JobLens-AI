## Data Ingestion

JobLens AI uses public applicant-tracking-system job boards for optional
real-job ingestion experiments. Greenhouse is the primary source for the
packaged demo dataset.

### Current Data Flow

```text
Public Greenhouse job boards
        |
        v
scripts/fetch_greenhouse_jobs.py
        |
        v
data/raw/greenhouse_jobs.csv
        |
        +--> scripts/process_greenhouse_jobs.py
        |
        +--> scripts/process_greenhouse_jobs_ai_first.py
        |
        v
data/processed/greenhouse_ai_demo_jobs.csv
```

The full raw fetch and intermediate experiment outputs are generated locally
and ignored by Git. The curated `greenhouse_ai_demo_jobs.csv` file is packaged
with the dashboard so the demo remains deterministic and reproducible.

Lever normalization support is also available as an optional ingestion module,
but it is not the source of the packaged demo.

### Supporting Workflows

- `scripts/fetch_greenhouse_jobs.py` fetches and normalizes public job postings.
- `scripts/process_greenhouse_jobs.py` applies deterministic processing.
- `scripts/process_greenhouse_jobs_ai_first.py` runs the AI-first extraction experiment.
- `scripts/build_greenhouse_ai_demo_jobs.py` builds the curated dashboard demo.
- `scripts/extract_skills_greenhouse_gemini.py` compares Gemini extraction on a small sample.

External APIs and LLMs are not required at dashboard runtime. This keeps the
core application stable while preserving a realistic ingestion and enrichment
workflow for portfolio demonstrations.

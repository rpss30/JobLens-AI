# Job Ingestion Sources

JobLens AI currently supports multiple real-job ingestion experiments.

## Preferred source: Greenhouse

Greenhouse is currently the preferred real-job source because its public job board API provides fuller job descriptions than the Adzuna aggregator results tested so far.

Greenhouse output:

- Source script: `scripts/fetch_greenhouse_jobs.py`
- Output file: `data/raw/greenhouse_jobs.csv`
- Notes:
  - Fetches public company job boards.
  - Saves all fetched postings.
  - Adds `is_target_job` as a lightweight relevance flag.
  - Provides long descriptions that are suitable for AI-first skill extraction.

## Secondary source: Adzuna

Adzuna is useful for broad market coverage, but the tested API descriptions are often truncated. This makes it less reliable for skill extraction quality.

Adzuna output:

- Source script: `scripts/fetch_adzuna_jobs.py`
- Output file: `data/raw/adzuna_jobs.csv`

## Experimental source: Lever

Lever client support exists, but the initial company slug list did not return useful results. Keep this as experimental until verified Lever company slugs are added.

Lever output:

- Source script: `scripts/fetch_lever_jobs.py`
- Output file: `data/raw/lever_jobs.csv`

## Skill extraction direction

The current direction is:

1. Ingest full real job descriptions from Greenhouse.
2. Use Gemini as the primary AI skill extractor.
3. Later add Groq as a fallback for quota/rate-limit/provider errors.
4. Keep the deterministic extractor as an emergency fallback.
5. Use TF-IDF role weighting after skills are extracted.
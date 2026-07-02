# Database Schema and Migrations

JobLens AI uses PostgreSQL for saved datasets, processed job postings, skill
relationships, analysis history, and pipeline metadata. Alembic owns schema
changes so local Docker, AWS RDS, and future production environments can move
forward through reviewed migrations instead of relying on `create_all`.

## Migration workflow

Fresh database:

```bash
alembic upgrade head
python -m scripts.seed_database
```

Existing local database that was created before Alembic:

```bash
alembic stamp 202607010001
alembic upgrade head
```

Use the stamp path only when the existing tables match the baseline schema that
was previously created by `python -m src.database.init_db`. For disposable local
databases, recreating the database and running `alembic upgrade head` is simpler.

## Tables

| Table | Purpose |
| --- | --- |
| `datasets` | One saved dataset, such as the sample jobs, Canada snapshot, or an uploaded CSV. |
| `job_postings` | Raw job posting text plus ATS/source metadata and duplicate-prevention keys. |
| `processed_jobs` | Cleaned title/description, role category, extracted skills, and extraction status. |
| `skills` | Canonical skill names used for normalized matching. |
| `job_skills` | Many-to-many bridge between processed jobs and skills. |
| `analysis_runs` | Saved role-fit inputs and summary outputs from the dashboard/API. |
| `ingestion_runs` | Pipeline run status, counts, timestamps, and failure logs written by refresh scripts. |
| `extraction_results` | Per-job AI extraction provenance, prompt version, model metadata, extracted skills, and errors. |

## Duplicate prevention

`job_postings` has uniqueness constraints on:

- `dataset_id`, `job_id`
- `dataset_id`, `source_url`

Both keys are dataset-scoped because the same public posting may appear in a
demo snapshot and in a user-uploaded dataset. Blank optional IDs are converted
to `NULL` before insertion so PostgreSQL does not treat empty strings as a real
deduplication key.

## Query indexes

The schema indexes the paths used most often by the dashboard and API:

- dataset source listing: `datasets(source_type, created_at)`
- job filters: `job_postings(dataset_id, company)`,
  `job_postings(dataset_id, location)`,
  `job_postings(dataset_id, experience_level)`
- ingestion freshness: `job_postings(dataset_id, fetched_at)` and
  `ingestion_runs(dataset_id, started_at)`
- role-fit grouping: `processed_jobs(role_category)`
- saved analysis history: `analysis_runs(dataset_name, created_at)` and
  `analysis_runs(dataset_id, created_at)`
- AI extraction auditing: `extraction_results(provider, created_at)` and
  `extraction_results(processed_job_id, created_at)`

These are practical portfolio-sized indexes. Larger production systems would
measure workload-specific query plans before adding more specialized indexes.

## EXPLAIN ANALYZE examples

Use `EXPLAIN ANALYZE` after loading a realistic dataset to verify query plans.

Dataset load used by the dashboard:

```sql
EXPLAIN ANALYZE
SELECT jp.title, jp.company, jp.location, pj.role_category, pj.extracted_skills
FROM job_postings jp
JOIN processed_jobs pj ON pj.job_posting_id = jp.id
JOIN datasets d ON d.id = jp.dataset_id
WHERE d.name = 'sample_jobs'
ORDER BY jp.id;
```

Common filtered search path:

```sql
EXPLAIN ANALYZE
SELECT jp.id, jp.title, jp.company, jp.location, pj.role_category
FROM job_postings jp
JOIN processed_jobs pj ON pj.job_posting_id = jp.id
WHERE jp.dataset_id = 1
  AND jp.location = 'Toronto, ON'
  AND jp.experience_level = 'Entry Level'
  AND pj.role_category = 'Software Engineering';
```

Dataset freshness/status path:

```sql
EXPLAIN ANALYZE
SELECT status, started_at, completed_at, processed_job_count
FROM ingestion_runs
WHERE dataset_id = 1
ORDER BY started_at DESC
LIMIT 5;
```

## Design tradeoffs

- The schema keeps raw resume text out of persistent storage. Resume analysis
  runs in memory and saved analyses store extracted profile skills and summary
  outputs rather than private resume content.
- `ingestion_runs` is intentionally compact: it stores operational status,
  counts, timestamps, and failure messages, while detailed JSON/Markdown run
  artifacts can stay in CI logs or local files.
- `extraction_results` stores compact LLM provenance when processed datasets
  include model or prompt-version metadata. Raw model responses remain optional
  to avoid bloating committed CSV snapshots.
- `pgvector` is deferred. Semantic search currently uses local deterministic SVD
  embeddings over in-memory job snapshots; pgvector becomes worthwhile when
  embeddings need to be persisted, indexed, and refreshed in the background for
  larger datasets.

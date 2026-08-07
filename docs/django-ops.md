# Django Operations Service

JobLens includes a Django operations service alongside the existing FastAPI API,
Streamlit dashboard, and PostgreSQL database. The service authenticates staff
users, connects to the shared PostgreSQL database, and reads existing pipeline
metadata without taking ownership of Alembic-managed application tables.

## Local Docker Startup

Start the full local stack:

```bash
docker compose up --build
```

Initialize the existing Alembic-owned application tables:

```bash
docker compose exec dashboard alembic upgrade head
```

Create Django-owned authentication and session tables:

```bash
docker compose exec django-ops python -m django_ops.manage migrate
```

Create a local staff user:

```bash
docker compose exec django-ops python -m django_ops.manage createsuperuser
```

Create the operations access groups:

```bash
docker compose exec django-ops python -m django_ops.manage bootstrap_ops_roles
```

Assign the staff user to one of:

- `JobLens Ops Viewers` for read-only operations access.
- `JobLens Ops Managers` for future state-changing operations workflows.

The Django service runs at:

```text
http://localhost:8001
```

Health check:

```text
http://localhost:8001/health/
```

Staff-only operations routes:

```text
http://localhost:8001/ops/
http://localhost:8001/ops/runs/
http://localhost:8001/ops/runs/<run_id>/
http://localhost:8001/ops/extractions/issues/
```

Manager-only POST route:

```text
http://localhost:8001/ops/extractions/<result_id>/actions/
```

Dedicated login and logout routes:

```text
http://localhost:8001/ops/login/
http://localhost:8001/ops/logout/
```

Logout accepts POST only and is protected by Django CSRF middleware.

## Authentication and Authorization

The operations portal uses Django's built-in user, session, CSRF, and group
systems.

Access requirements for `/ops/` and child operations pages:

- user is authenticated
- user is active
- user has `is_staff = True`
- user is a superuser, belongs to `JobLens Ops Viewers`, or belongs to
  `JobLens Ops Managers`

Current permission levels:

| Role | Access |
| --- | --- |
| `JobLens Ops Viewers` | Can view the operations dashboard and read-only investigation pages. |
| `JobLens Ops Managers` | Can view the dashboard and is reserved for later reviewed/retry actions. |

Session and CSRF settings:

- session cookie is HTTP-only
- session and CSRF cookies use `SameSite=Lax`
- secure cookies default to enabled when `DJANGO_DEBUG=false`
- logout is POST-only and CSRF-protected

## Migration Ownership

Alembic owns the existing JobLens application tables:

- `datasets`
- `job_postings`
- `processed_jobs`
- `skills`
- `job_skills`
- `analysis_runs`
- `ingestion_runs`
- `extraction_results`

Django maps the pipeline tables it needs as unmanaged models. These models have
`managed = False`, so Django migrations do not create, alter, or drop those
tables.

Django migrations own Django framework tables:

- `auth_*`
- `django_admin_log`
- `django_content_type`
- `django_migrations`
- `django_session`

They also own operations-only tables:

- `ops_extraction_reviews`
- `ops_audit_events`

Deployment order:

1. Run Alembic migrations with `alembic upgrade head`.
2. Run Django migrations with `python -m django_ops.manage migrate`.
3. Start or restart the Django operations service.

Rollback should reverse the application release first. If a future branch adds
Django-managed operations tables, rollbacks must document whether those Django
migrations are reversible and whether any associated Alembic migration also
needs to be downgraded.

The production Compose runbook in
[production-compose.md](production-compose.md) uses the same migration order for
the single-server deployment path.

## Pipeline Investigation

The operations service now provides read-only pages for investigating ingestion
and enrichment health:

- `/ops/` shows run count, empty extraction count, and the latest pipeline run.
- `/ops/runs/` lists recent runs with filtering by status, provider, model,
  prompt version, and free-text search across source metadata and errors.
- `/ops/runs/<run_id>/` shows one run's timing, counts, dedup rejects,
  provider/model/prompt counts, source breakdown, and linked extraction issues.
- `/ops/extractions/issues/` lists extraction attempts with empty skill output
  or persisted errors, joined back to the source posting.

Run investigation uses `ingestion_runs.run_metadata` for bounded run-scoped
aggregates such as provider counts, model counts, prompt-version counts,
per-source totals, and dedup rejected counts. Failed or empty extractions stay
in `extraction_results`, where they can be queried and joined to
`processed_jobs` and `job_postings`.

Current limitation: extraction results are linked to run detail pages through
the run dataset because the application schema does not yet store a direct
`extraction_results.ingestion_run_id`. That keeps this branch read-only and
schema-light while still making failures visible from the operations console.

## Audited Operations Actions

Managers can now act on failed or empty extraction results from the extraction
issue list or a run detail page:

- save or update an internal review note
- mark the extraction as reviewed
- request one retry for an eligible extraction issue

Every successful manager action writes an `ops_audit_events` row with the actor,
timestamp, target extraction result, action name, and posting/provider metadata.
The current review state lives in `ops_extraction_reviews`, keyed by
`extraction_result_id`, without copying posting fields from the application
tables.

Retry safety:

- retry requests are manager-only POST actions protected by CSRF
- duplicate retry requests for the same extraction result are rejected
- the web request records the retry request but does not call external
  extraction providers inline

That last boundary is intentional. It gives operations users an audited retry
workflow without making a page load depend on provider credentials, rate limits,
or a long-running extraction call. A later worker or management command can
process requested retries.

## Current Scope

Implemented:

- Django project and settings.
- PostgreSQL configuration through `DATABASE_URL`.
- Gunicorn-compatible WSGI entrypoint.
- Dedicated `/ops/login/` and `/ops/logout/` routes.
- Staff-only `/ops/` route protected by operations groups.
- `/health/` database connectivity endpoint.
- Unmanaged Django models for existing pipeline metadata tables.
- `bootstrap_ops_roles` command for creating operations groups.
- Pipeline run list with filters and pagination.
- Pipeline run detail pages with run-scoped metadata and source results.
- Failed and empty extraction issue list with posting links.
- Manager-only review notes, reviewed status, and retry requests for extraction
  issues.
- Append-only audit events for operations actions.

Not implemented yet:

- Background worker or command for executing requested extraction retries.
- Production reverse proxy routing.

No cloud resources are created by the Django operations service.

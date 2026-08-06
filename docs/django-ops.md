# Django Operations Foundation

JobLens now includes a Django operations service foundation alongside the
existing FastAPI API, Streamlit dashboard, PostgreSQL database, and legacy Flask
ops console. This first Django slice is intentionally small: it proves Django
can start, authenticate staff users, connect to the shared PostgreSQL database,
and read existing pipeline metadata without taking ownership of FastAPI-owned
tables.

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

Staff-only operations route:

```text
http://localhost:8001/ops/
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

Access requirements for `/ops/`:

- user is authenticated
- user is active
- user has `is_staff = True`
- user is a superuser, belongs to `JobLens Ops Viewers`, or belongs to
  `JobLens Ops Managers`

Current permission levels:

| Role | Access |
| --- | --- |
| `JobLens Ops Viewers` | Can view the operations dashboard foundation. |
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

Django migrations own only Django framework tables in this foundation:

- `auth_*`
- `django_admin_log`
- `django_content_type`
- `django_migrations`
- `django_session`

Deployment order:

1. Run Alembic migrations with `alembic upgrade head`.
2. Run Django migrations with `python -m django_ops.manage migrate`.
3. Start or restart the Django operations service.

Rollback should reverse the application release first. If a future branch adds
Django-managed operations tables, rollbacks must document whether those Django
migrations are reversible and whether any associated Alembic migration also
needs to be downgraded.

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

Not implemented yet:

- Pipeline-run filters, pagination, or detail pages.
- Failed-extraction review notes or retry actions.
- Audit records for state-changing operations.
- Production reverse proxy routing.
- Removal of the Flask ops console.

No cloud resources are created by this foundation.

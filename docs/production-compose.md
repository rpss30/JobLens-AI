# Production Docker Compose Stack

This stack is the low-cost production base for running JobLens on one Linux
server. It runs Caddy, the Streamlit dashboard, FastAPI API, Django operations
service, and PostgreSQL with Docker Compose.

It does not create cloud resources or configure DNS. Caddy terminates HTTPS
with automatic certificates once the configured domain points at the server and
ports 80 and 443 are reachable.

## Files

```text
docker-compose.prod.yml
.env.production.example
deploy/caddy/Caddyfile
```

Copy the example environment file on the server:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Then replace every placeholder secret before starting the stack:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `DJANGO_SECRET_KEY`
- `JOBLENS_DOMAIN`
- `CADDY_ACME_EMAIL`
- optional provider keys such as `GROQ_API_KEY`

Keep `.env.production` out of Git.

## Network Design

Production Compose defines two Docker networks:

| Network | Purpose |
| --- | --- |
| `joblens_edge` | Shared by Caddy and app services. |
| `joblens_database` | Internal database network shared only by app services and PostgreSQL. |

Caddy is the only service that publishes host ports:

```text
80/tcp
443/tcp
```

The production Compose file uses `expose` instead of `ports` for Streamlit,
FastAPI, and Django. PostgreSQL does not publish a host port.

Public routing:

```text
/       -> dashboard:8501
/api/*  -> api:8000 with /api stripped before the request reaches FastAPI
/ops/*  -> django-ops:8001
/healthz -> Caddy edge health response
```

FastAPI uses `JOBLENS_API_ROOT_PATH=/api` so generated OpenAPI and Swagger UI
links work behind the `/api/*` proxy prefix. Django receives forwarded scheme
and host headers from Caddy and uses secure cookies in production.

## DNS and Firewall Preconditions

Before starting Caddy with a real domain:

- point `JOBLENS_DOMAIN` at the server's public IP address
- allow inbound TCP 80 and 443 through the provider firewall
- allow inbound TCP 80 and 443 through the host firewall
- do not expose PostgreSQL, FastAPI, Django, or Docker daemon ports publicly

For initial server work, SSH should be restricted separately to a trusted source
address where possible. See [server-hardening.md](server-hardening.md) for the
host firewall, SSH, deployment-user, and Docker log-rotation runbook.
See [production-deployment.md](production-deployment.md) for the manual
GitHub Actions deployment workflow and rollback procedure that run this Compose
sequence on an already-provisioned server.
See [database-backups.md](database-backups.md) for backup and restore scripts
that run through this stack's internal PostgreSQL service.
See [operations-monitoring.md](operations-monitoring.md) for local service
health, disk usage, backup freshness, and log-snapshot checks.
See [production-readiness.md](production-readiness.md) for the final preflight
checklist before a real production rollout.

## Startup

Validate the rendered Compose configuration with the example env:

```bash
docker compose --env-file .env.production.example -f docker-compose.prod.yml config -q
```

Build the shared application image:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml build
```

Start PostgreSQL first:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d db
```

Run Alembic migrations for application tables:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Run Django migrations for auth, sessions, review state, and audit tables:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm django-ops python -m django_ops.manage migrate
```

Create operations roles:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm django-ops python -m django_ops.manage bootstrap_ops_roles
```

Start the full stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

## Health Checks

Show service status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Check service health from inside the Docker network:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec api curl -fsS http://localhost:8000/health
docker compose --env-file .env.production -f docker-compose.prod.yml exec django-ops curl -fsS http://localhost:8001/health/
docker compose --env-file .env.production -f docker-compose.prod.yml exec dashboard curl -fsS http://localhost:8501/_stcore/health
```

Check the public edge after DNS and TLS are ready:

```bash
curl -fsS https://$JOBLENS_DOMAIN/healthz
curl -fsS https://$JOBLENS_DOMAIN/api/health
```

Check the latest local database backup status:

```bash
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json deploy/scripts/check_database_backup_status.sh
```

Check the full local operations status:

```bash
MONITOR_STATUS_FILE=/srv/joblens-monitoring/latest_status.json deploy/scripts/check_operations_status.sh
```

## Updates

Pull the latest application code, rebuild, run migrations, then restart:

```bash
git pull --ff-only
docker compose --env-file .env.production -f docker-compose.prod.yml build
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm django-ops python -m django_ops.manage migrate
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

Rollback should reverse the application release first. Only downgrade database
migrations after checking whether the target migration is explicitly reversible.
The deployment scripts in [production-deployment.md](production-deployment.md)
automate this order and retain the previous server revision for application
rollback.

## Current Limits

This stack intentionally does not include:

- cloud resource provisioning
- off-server backup storage
- external uptime monitoring or central log aggregation

Those belong in later focused branches.

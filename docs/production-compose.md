# Production Docker Compose Stack

This stack is the low-cost production base for running JobLens on one Linux
server. It runs the Streamlit dashboard, FastAPI API, Django operations service,
and PostgreSQL with Docker Compose.

It does not create cloud resources, configure DNS, or terminate HTTPS. A later
reverse-proxy branch should attach Caddy or Nginx to the `joblens_edge` network
and publish only ports 80 and 443.

## Files

```text
docker-compose.prod.yml
.env.production.example
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
- optional provider keys such as `GROQ_API_KEY`

Keep `.env.production` out of Git.

## Network Design

Production Compose defines two Docker networks:

| Network | Purpose |
| --- | --- |
| `joblens_edge` | Shared by app services and the future reverse proxy. |
| `joblens_database` | Internal database network shared only by app services and PostgreSQL. |

The production Compose file uses `expose` instead of `ports` for Streamlit,
FastAPI, and Django. PostgreSQL does not publish a host port. Until a reverse
proxy is added, the services are reachable only from inside Docker networks.

The intended future public routing is:

```text
/       -> dashboard:8501
/api/*  -> api:8000
/ops/*  -> django-ops:8001
```

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

## Current Limits

This branch intentionally does not include:

- Caddy or Nginx
- HTTPS
- domain routing
- host firewall rules
- automated deploys
- database backups
- cloud resource provisioning

Those belong in later focused branches.

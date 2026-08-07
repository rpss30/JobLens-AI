# Production Deployment Pipeline

This guide covers the low-cost single-server deployment path for JobLens AI.
The pipeline assumes an already-provisioned server with Docker, Docker Compose,
the repository checkout, DNS, Caddy routing, and host hardening already in
place. It does not create or modify cloud resources.

## Files

```text
.github/workflows/deploy-production.yml
deploy/scripts/deploy_production.sh
deploy/scripts/rollback_production.sh
deploy/scripts/check_production_health.sh
```

## Preconditions

Before running the deployment pipeline, confirm:

- the Linux server already exists and has a restricted deployment user
- the deployment user has SSH key access and can run Docker Compose
- the repository is checked out on the server at `DEPLOY_PATH`
- `.env.production` exists on the server and is readable only by the deployment user
- `deploy/scripts/audit_secret_configuration.sh` passes against `.env.production`
- `docker-compose.prod.yml` validates with the production environment file
- DNS points the production domain at the server
- Caddy can obtain certificates after ports 80 and 443 are reachable
- PostgreSQL is not exposed publicly

See [server-hardening.md](server-hardening.md) and
[production-compose.md](production-compose.md) before using this workflow on a
public host.
Use [production-readiness.md](production-readiness.md) as the final preflight
checklist before running the first production deployment.

## GitHub Actions

The `Deploy Production` workflow is manual-only through GitHub Actions
`workflow_dispatch`. It runs in the protected `production` environment, validates
the shell scripts, writes the deployment SSH key to the runner, and connects to
the existing server over SSH.

Required encrypted secrets:

| Secret | Purpose |
| --- | --- |
| `PRODUCTION_SSH_HOST` | Hostname or IP address for the server. |
| `PRODUCTION_SSH_USER` | Restricted deployment user on the server. |
| `PRODUCTION_SSH_KEY` | Private SSH key allowed for that deployment user. |
| `PRODUCTION_DEPLOY_PATH` | Absolute path to the repository checkout on the server. |
| `PRODUCTION_DOMAIN` | Public domain used for post-deploy health checks. |

Optional encrypted secrets:

| Secret | Purpose |
| --- | --- |
| `PRODUCTION_SSH_PORT` | SSH port, defaulting to `22` when unset. |
| `PRODUCTION_HEALTH_BASE_URL` | Full health-check base URL when it should differ from `https://$PRODUCTION_DOMAIN`. |

The workflow does not store production application secrets. Runtime secrets
remain in the server-side `.env.production` file or a later approved secret
store.
For servers that already have a Parameter Store path and read permissions,
[parameter-store-secrets.md](parameter-store-secrets.md) documents the
pre-deploy render step.

## Deployment Order

`deploy/scripts/deploy_production.sh` runs the same production Compose sequence
documented in [production-compose.md](production-compose.md):

1. record the current server revision in `.deploy/previous_revision`
2. fetch from `origin` and check out `DEPLOY_REF`
3. validate `docker-compose.prod.yml`
4. build the production image
5. start PostgreSQL
6. run `alembic upgrade head` for FastAPI-owned application tables
7. run `python -m django_ops.manage migrate` for Django-owned tables
8. run `python -m django_ops.manage bootstrap_ops_roles`
9. start the full stack
10. run public health checks

This order keeps Alembic-owned and Django-owned migrations explicit and
reviewable. If either migration step fails, the deploy exits before the full
stack restart.

## Manual Use

Run the deployment script from a trusted workstation when you want the same
sequence outside GitHub Actions:

```bash
DEPLOY_HOST=203.0.113.10 \
DEPLOY_USER=joblens \
DEPLOY_PATH=/srv/joblens-ai \
DEPLOY_REF=origin/main \
JOBLENS_DOMAIN=jobs.example.com \
deploy/scripts/deploy_production.sh
```

Use `JOBLENS_HEALTH_BASE_URL` instead of `JOBLENS_DOMAIN` when the public health
base URL is not exactly `https://$JOBLENS_DOMAIN`.

## Health Checks

`deploy/scripts/check_production_health.sh` checks the public edge after a
deploy:

```text
/healthz
/api/health
/ops/login/
```

The script retries by default because Caddy, Gunicorn, and the database may
need a short stabilization window after containers restart. Override
`HEALTH_RETRIES` and `HEALTH_DELAY_SECONDS` when needed.

## Rollback

If the deploy step fails in GitHub Actions, the workflow runs
`deploy/scripts/rollback_production.sh`. The rollback script checks out
`DEPLOY_ROLLBACK_REF` when supplied, otherwise it uses the server-side
`.deploy/previous_revision` recorded before deployment.

Manual rollback:

```bash
DEPLOY_HOST=203.0.113.10 \
DEPLOY_USER=joblens \
DEPLOY_PATH=/srv/joblens-ai \
DEPLOY_ROLLBACK_REF=abc1234 \
JOBLENS_DOMAIN=jobs.example.com \
deploy/scripts/rollback_production.sh
```

Rollback restarts application containers only. No database downgrades are run
automatically, because downgrades can corrupt or drop production data if a
migration is not explicitly reversible. Review the target Alembic and Django
migrations before any manual database rollback.

## Cost Impact

This deployment automation creates no cloud resources and starts no paid
services. It uses the existing server and normal GitHub Actions minutes. Server,
static IP, DNS, and storage costs must be tracked separately in the production
resource inventory.

Database backup and restore procedures are documented separately in
[database-backups.md](database-backups.md). Run and verify a fresh backup before
high-risk deployments or restores.

Off-server backup copy and alert delivery procedures are documented in
[offsite-backups-alerts.md](offsite-backups-alerts.md). Keep those integrations
disabled until the destination, credentials, and cost approval are in place.

Local post-deploy status checks and log snapshots are documented in
[operations-monitoring.md](operations-monitoring.md). Run the operations status
check after a release when investigating service health, backup freshness, or
disk pressure.

Scheduled Canada jobs refreshes are documented in
[production-ingestion.md](production-ingestion.md). Run and verify the refresh
manually before enabling the weekly production timer.

Runtime secret audit and rotation steps are documented in
[secret-rotation.md](secret-rotation.md). Run the audit after changing
`.env.production` and before starting a deployment window.

Rendering `.env.production` from an existing Parameter Store path is documented
in [parameter-store-secrets.md](parameter-store-secrets.md). The renderer reads
parameters only and runs the same local secret audit after writing the env file.

The full rollout checklist is documented in
[production-readiness.md](production-readiness.md). It ties together cost
guardrails, server prerequisites, secret audit, backups, monitoring, and
post-deploy verification.

Security scanning is documented in [security-scanning.md](security-scanning.md).
Run the dependency, static Python, and container image scans before high-risk
releases.

External uptime monitoring is documented in
[external-uptime-monitoring.md](external-uptime-monitoring.md). Enable it after
the production domain and HTTPS routing are stable.

## Current Limits

- no server provisioning
- no DNS updates
- no image registry publishing
- no scheduled automatic deployment
- no central log aggregation
- no automatic provider key rotation

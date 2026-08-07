# Production Readiness Checklist

This checklist ties together the low-cost single-server production path for
JobLens. It is meant to be run before the first real production deployment and
again before high-risk releases. It creates no cloud resources.

## Files

```text
deploy/scripts/check_production_readiness.sh
docs/production-readiness.md
docs/lightsail-deployment-plan.md
deploy/lightsail/resource-plan.example.json
```

## Local Repo Readiness

Run from the repository root:

```bash
deploy/scripts/check_production_readiness.sh
```

The default mode checks that the repo contains the production Compose stack,
Caddy config, deployment workflow, deployment scripts, backup scripts,
monitoring scripts, secret audit script, security docs, and required ignore
rules. It also scans deployment automation for forbidden cloud provisioning
commands.

On a development machine, the script usually reports a warning because
`.env.production` is intentionally not present. On the server, after
`.env.production` exists, run strict mode:

```bash
STRICT_READINESS=true \
RUN_COMPOSE_CONFIG=true \
RUN_SECRET_AUDIT=true \
RUN_BACKUP_STATUS_CHECK=true \
RUN_OPERATIONS_STATUS_CHECK=true \
deploy/scripts/check_production_readiness.sh
```

The script writes:

```text
deploy/readiness/latest_readiness.json
```

Generated readiness output is ignored by Git.

## Cost and Approval Gate

Before creating or changing any paid cloud resource, stop and document:

- each resource that would be created or changed
- why it is necessary
- whether it has an ongoing charge
- likely monthly cost
- whether it keeps charging when unused
- teardown steps
- resources that must be manually checked after teardown

Do not create a server, static IP, DNS hosted zone, S3 bucket, RDS instance,
load balancer, NAT gateway, or any other paid resource without explicit
approval.

Use [lightsail-deployment-plan.md](lightsail-deployment-plan.md) as the
plan-only resource inventory for the low-cost Lightsail path. The committed
`deploy/lightsail/resource-plan.example.json` is only a template; live resource
identifiers, IP addresses, URLs, and approval notes must stay in a private
inventory file or private deployment note. Treat the private inventory as the
source of truth after provisioning.

Before the first production deployment, confirm:

- an AWS Budget or equivalent billing guardrail exists
- billing alerts are configured at several thresholds
- persistent resources are listed in a private deployment note
- the Lightsail plan has been reviewed if Lightsail is the chosen server target
- teardown steps are written before provisioning
- project tags are decided for any future cloud resources

## Server Preconditions

The permanent low-cost target is one already-approved Linux server. Before
deploying:

- Docker Engine and Docker Compose are installed
- the repository is checked out at the agreed `PRODUCTION_DEPLOY_PATH`
- the deployment user has SSH key access
- the deployment user can run Docker Compose
- `/srv/joblens-backups` or the chosen backup path exists
- `/srv/joblens-monitoring` or the chosen status path exists
- a recovery-console path is known in case SSH is lost

## Network and DNS Preconditions

Before public traffic:

- the domain or subdomain points to the server
- the provider firewall allows TCP 80 and 443
- the host firewall allows TCP 80 and 443
- SSH is restricted to a trusted source range where possible
- PostgreSQL is not exposed publicly
- FastAPI and Django internal ports are not exposed publicly
- Docker daemon ports are not exposed publicly

See [server-hardening.md](server-hardening.md) and
[production-compose.md](production-compose.md).

## Secret Preconditions

Before deployment:

- `.env.production` exists on the server only
- `.env.production` has mode `0600`
- `.env.production` is not tracked by Git
- placeholders in `.env.production` have been replaced
- `POSTGRES_PASSWORD` and `DATABASE_URL` agree
- `DJANGO_SECRET_KEY` is unique and non-placeholder
- GitHub Actions deployment secrets are configured in the protected production environment

Run:

```bash
ENV_FILE=.env.production deploy/scripts/audit_secret_configuration.sh
```

See [secret-rotation.md](secret-rotation.md).

## Database Preconditions

Before the first deployment:

- `docker-compose.prod.yml` validates with `.env.production`
- Alembic ownership and Django migration ownership are understood
- a backup has been created
- a restore verification has passed
- the backup status check is fresh

Run:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config -q
BACKUP_DIR=/srv/joblens-backups deploy/scripts/backup_database.sh
BACKUP_FILE=/srv/joblens-backups/<backup-file>.dump deploy/scripts/verify_database_backup.sh
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json deploy/scripts/check_database_backup_status.sh
```

See [database-backups.md](database-backups.md).

## Deployment Preconditions

Before running the GitHub Actions deployment workflow:

- local and remote tests are green
- deployment branch is merged to `main`
- production environment approvals are configured if needed
- `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_USER`, `PRODUCTION_SSH_KEY`,
  `PRODUCTION_DEPLOY_PATH`, and `PRODUCTION_DOMAIN` are set
- `deploy/scripts/check_production_readiness.sh` passes in strict mode on the server
- rollback behavior is understood and database downgrades are not automatic

See [production-deployment.md](production-deployment.md).

## Post-Deploy Verification

After deployment:

- `https://$JOBLENS_DOMAIN/healthz` returns success
- `https://$JOBLENS_DOMAIN/api/health` returns success
- `https://$JOBLENS_DOMAIN/ops/login/` renders
- the dashboard loads
- FastAPI OpenAPI docs render behind `/api/docs`
- Django operations login works for a staff operations user
- `check_operations_status.sh` passes
- backup status remains fresh
- logs show no repeated application startup errors

Collect a log snapshot for any failed release:

```bash
LOG_DIR=/srv/joblens-log-snapshots INCLUDE_SYSTEMD_LOGS=true deploy/scripts/collect_operations_logs.sh
```

See [operations-monitoring.md](operations-monitoring.md).

## Ready Definition

The deployment is ready to share when:

- production routing works over HTTPS
- PostgreSQL is private
- backups exist and restore verification has passed
- monitoring status is fresh
- secret audit passes
- rollback steps are documented
- cost guardrails are in place
- all production URLs and resource identifiers are recorded privately

## Current Limits

- no cloud resource has been provisioned by this repository work
- no Lightsail instance, static IPv4 address, DNS record, or snapshot has been provisioned
- no external uptime monitor is configured
- no alert delivery is configured
- no off-server backup copy is implemented
- no managed secret store is integrated
- no declarative infrastructure module is applied

Those remain separate branches or manual deployment steps and require approval
when they could create ongoing charges.

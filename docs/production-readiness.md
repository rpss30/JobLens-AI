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
docs/production-ingestion.md
docs/offsite-backups-alerts.md
docs/parameter-store-secrets.md
docs/security-scanning.md
docs/external-uptime-monitoring.md
docs/log-aggregation.md
```

## Local Repo Readiness

Run from the repository root:

```bash
deploy/scripts/check_production_readiness.sh
```

The default mode checks that the repo contains the production Compose stack,
Caddy config, deployment workflow, deployment scripts, backup scripts,
monitoring scripts, scheduled ingestion scripts, secret audit script, Parameter
Store renderer, security scan workflow, external uptime workflow, security
docs, log aggregation scripts, and required ignore rules. It also scans
deployment automation for forbidden cloud provisioning commands.

On a development machine, the script usually reports a warning because
`.env.production` is intentionally not present. On the server, after
`.env.production` exists, run strict mode:

```bash
STRICT_READINESS=true \
RUN_COMPOSE_CONFIG=true \
RUN_SECRET_AUDIT=true \
RUN_PARAMETER_STORE_RENDER_CHECK=true \
RUN_BACKUP_STATUS_CHECK=true \
RUN_OFFSITE_BACKUP_STATUS_CHECK=true \
RUN_OPERATIONS_STATUS_CHECK=true \
RUN_TERRAFORM_VALIDATE=true \
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
plan-only resource inventory for the low-cost Lightsail path. Terraform template
files live in `deploy/lightsail/terraform` for local formatting and validation,
but do not plan against an AWS account or apply before approval.
No Terraform state is committed or required for local validation.
The committed `deploy/lightsail/resource-plan.example.json` is only a template;
live resource identifiers, IP addresses, URLs, and approval notes must stay in a
private inventory file or private deployment note. Treat the private inventory
as the source of truth after provisioning.

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
- the off-server backup destination is approved if that check will be enabled
- `/srv/joblens-monitoring` or the chosen status path exists
- `/srv/joblens-ingestion` or the chosen ingestion artifact path exists
- `/srv/joblens-logs` or the chosen log aggregation path exists
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
- Parameter Store env rendering has been dry-run when an approved path is used
- placeholders in `.env.production` have been replaced
- `POSTGRES_PASSWORD` and `DATABASE_URL` agree
- `DJANGO_SECRET_KEY` is unique and non-placeholder
- GitHub Actions deployment secrets are configured in the protected production environment

Run:

```bash
ENV_FILE=.env.production deploy/scripts/audit_secret_configuration.sh
PARAMETER_STORE_PATH=/joblens/production PARAMETER_STORE_DRY_RUN=true deploy/scripts/render_env_from_parameter_store.sh
```

See [secret-rotation.md](secret-rotation.md).
See [parameter-store-secrets.md](parameter-store-secrets.md).

## Database Preconditions

Before the first deployment:

- `docker-compose.prod.yml` validates with `.env.production`
- Alembic ownership and Django migration ownership are understood
- a backup has been created
- a restore verification has passed
- the backup status check is fresh
- off-server backup upload has been dry-run or enabled only after approval

Run:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config -q
BACKUP_DIR=/srv/joblens-backups deploy/scripts/backup_database.sh
BACKUP_FILE=/srv/joblens-backups/<backup-file>.dump deploy/scripts/verify_database_backup.sh
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json deploy/scripts/check_database_backup_status.sh
OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json deploy/scripts/check_offsite_backup_status.sh
```

See [database-backups.md](database-backups.md).
See [offsite-backups-alerts.md](offsite-backups-alerts.md) before enabling
off-server upload or alert delivery.

## Deployment Preconditions

Before running the GitHub Actions deployment workflow:

- local and remote tests are green
- security scans have passed or each finding has a documented exception
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
- off-server backup status remains fresh when enabled
- ingestion refresh status remains fresh
- log aggregation status remains fresh
- alert dry-run or delivery has been tested when alerts are enabled
- logs show no repeated application startup errors

Collect a log snapshot for any failed release:

```bash
LOG_DIR=/srv/joblens-log-snapshots INCLUDE_SYSTEMD_LOGS=true deploy/scripts/collect_operations_logs.sh
```

Aggregate current logs for routine investigation:

```bash
LOG_AGGREGATION_DIR=/srv/joblens-logs deploy/scripts/aggregate_operations_logs.sh
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json deploy/scripts/check_log_aggregation_status.sh
```

See [operations-monitoring.md](operations-monitoring.md).

## Ready Definition

The deployment is ready to share when:

- production routing works over HTTPS
- PostgreSQL is private
- backups exist and restore verification has passed
- off-server backup copy is enabled or explicitly deferred with approval notes
- the scheduled ingestion refresh has succeeded at least once
- monitoring status is fresh
- log aggregation status is fresh
- secret audit passes
- Parameter Store render status is fresh when that workflow is used
- dependency, static Python, and container image scans have passed
- external uptime check is configured after the production URL is stable
- rollback steps are documented
- cost guardrails are in place
- all production URLs and resource identifiers are recorded privately

## Current Limits

- no cloud resource has been provisioned by this repository work
- no Lightsail instance, static IPv4 address, DNS record, or snapshot has been provisioned
- external uptime monitoring is implemented through GitHub Actions but is skipped until a URL is configured
- off-server backup copy and alert delivery are implemented as opt-in scripts but not enabled by default
- Parameter Store env rendering is implemented for existing parameters but no parameters are created
- no declarative infrastructure module is applied

Those remain separate branches or manual deployment steps and require approval
when they could create ongoing charges.

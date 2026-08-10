# Operations Monitoring

This runbook covers low-cost production visibility for the single-server
JobLens deployment. It uses shell scripts, Docker Compose, systemd timers,
journald, and local status files. It creates no cloud resources.

## Files

```text
deploy/scripts/check_operations_status.sh
deploy/scripts/check_disk_usage.sh
deploy/scripts/collect_operations_logs.sh
deploy/scripts/aggregate_operations_logs.sh
deploy/scripts/check_log_aggregation_status.sh
deploy/scripts/check_offsite_backup_status.sh
deploy/scripts/check_ingestion_refresh_status.sh
deploy/scripts/send_operations_alert.sh
deploy/server/systemd/joblens-log-aggregation.service
deploy/server/systemd/joblens-log-aggregation.timer
deploy/server/systemd/joblens-ops-monitor.service
deploy/server/systemd/joblens-ops-monitor.timer
```

## What Gets Checked

`check_operations_status.sh` runs seven checks:

| Check | What It Verifies |
| --- | --- |
| Compose services | `caddy`, `frontend`, `api`, `django-ops`, and `db` are running. |
| Public health | `/healthz`, `/api/health`, and `/ops/login/` respond through the public edge when a domain or base URL is configured. |
| Database backup | `latest_backup.json` exists, reports success, and is fresh. |
| Off-server backup | `latest_offsite_backup.json` exists, reports success, and is fresh when the check is enabled. |
| Ingestion refresh | `latest_ingestion_refresh.json` exists, reports success, and is fresh. |
| Log aggregation | `latest_log_aggregation.json` exists, reports success, and is fresh. |
| Disk usage | watched filesystem paths are below warning and critical thresholds. |

Each run writes a compact JSON status file:

```text
/srv/joblens-monitoring/latest_status.json
```

The status file is intentionally simple so it can be inspected with `cat`,
served later through an authenticated operations view, or picked up by a future
alerting integration.

## Manual Status Check

Run from the repository checkout on the server:

```bash
JOBLENS_DOMAIN=jobs.example.com \
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json \
OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json \
INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json \
MONITOR_STATUS_FILE=/srv/joblens-monitoring/latest_status.json \
deploy/scripts/check_operations_status.sh
```

Use `JOBLENS_HEALTH_BASE_URL` instead of `JOBLENS_DOMAIN` when health checks
should target a specific base URL.

Useful defaults:

| Variable | Default |
| --- | --- |
| `DEPLOY_ENV_FILE` | `.env.production` |
| `COMPOSE_FILE` | `docker-compose.prod.yml` |
| `EXPECTED_SERVICES` | `caddy frontend api django-ops db` |
| `BACKUP_STATUS_FILE` | `/srv/joblens-backups/latest_backup.json` |
| `BACKUP_MAX_AGE_HOURS` | `30` |
| `OFFSITE_BACKUP_STATUS_FILE` | `/srv/joblens-backups/latest_offsite_backup.json` |
| `OFFSITE_BACKUP_MAX_AGE_HOURS` | `30` |
| `SKIP_OFFSITE_BACKUP_CHECK` | `true` |
| `INGESTION_STATUS_FILE` | `/srv/joblens-ingestion/latest_ingestion_refresh.json` |
| `INGESTION_MAX_AGE_HOURS` | `192` |
| `SKIP_INGESTION_REFRESH_CHECK` | `false` |
| `LOG_AGGREGATION_STATUS_FILE` | `/srv/joblens-logs/latest_log_aggregation.json` |
| `LOG_AGGREGATION_MAX_AGE_HOURS` | `6` |
| `SKIP_LOG_AGGREGATION_CHECK` | `false` |
| `DISK_PATHS` | `/ /srv/joblens-backups /srv/joblens-logs` |
| `DISK_WARN_PERCENT` | `80` |
| `DISK_CRITICAL_PERCENT` | `90` |
| `ALERT_ON_FAILURE` | `false` |
| `ALERT_FAILURES_ARE_FATAL` | `false` |

When `joblens-ingestion-refresh.timer` is left disabled, its status file never
appears and the ingestion check fails on every monitor run. Skip that one check
with a systemd drop-in so the shipped unit file stays canonical:

```text
/etc/systemd/system/joblens-ops-monitor.service.d/override.conf

[Service]
Environment=SKIP_INGESTION_REFRESH_CHECK=true
```

Run `systemctl daemon-reload` afterwards, and remove the override if scheduled
ingestion is enabled later.

For maintenance windows, individual checks can be skipped with:

```text
SKIP_COMPOSE_CHECK=true
SKIP_PUBLIC_HEALTH_CHECK=true
SKIP_BACKUP_STATUS_CHECK=true
SKIP_OFFSITE_BACKUP_CHECK=true
SKIP_INGESTION_REFRESH_CHECK=true
SKIP_LOG_AGGREGATION_CHECK=true
SKIP_DISK_CHECK=true
```

## Disk Checks

Run the disk check directly when investigating storage pressure:

```bash
DISK_PATHS="/ /srv/joblens-backups" \
DISK_WARN_PERCENT=80 \
DISK_CRITICAL_PERCENT=90 \
deploy/scripts/check_disk_usage.sh
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | all watched paths are below the warning threshold |
| `1` | at least one watched path crossed the warning threshold |
| `2` | configuration error, missing required path, or critical usage |

Use `SKIP_MISSING_DISK_PATHS=true` only when a watched path is optional during
local testing.

## Log Snapshots

Capture Compose service logs and service status into a timestamped directory:

```bash
LOG_DIR=/srv/joblens-log-snapshots \
LOG_LINES=300 \
INCLUDE_SYSTEMD_LOGS=true \
deploy/scripts/collect_operations_logs.sh
```

The script writes:

```text
compose_ps.txt
caddy.log
frontend.log
api.log
django-ops.log
db.log
systemd.log
manifest.json
```

Keep log snapshots outside Git and restrict access to the deployment user.
Application logs can include request paths, service errors, and operational
context that should not become public.

## Central Log Aggregation

Run the local log aggregator to normalize Compose and systemd logs into one
JSONL file plus a freshness status file:

```bash
LOG_AGGREGATION_DIR=/srv/joblens-logs \
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json \
deploy/scripts/aggregate_operations_logs.sh
```

Check the latest aggregation:

```bash
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json \
deploy/scripts/check_log_aggregation_status.sh
```

See [log-aggregation.md](log-aggregation.md) for the JSONL schema, retention
settings, timer installation, and query examples.

## Timer Installation

The repository includes a systemd timer template for running the aggregate
status check every five minutes:

```bash
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-ops-monitor.service /etc/systemd/system/joblens-ops-monitor.service
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-ops-monitor.timer /etc/systemd/system/joblens-ops-monitor.timer
sudo systemctl daemon-reload
sudo systemctl enable --now joblens-ops-monitor.timer
```

Install the log aggregation timer separately:

```bash
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-log-aggregation.service /etc/systemd/system/joblens-log-aggregation.service
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-log-aggregation.timer /etc/systemd/system/joblens-log-aggregation.timer
sudo systemctl daemon-reload
sudo systemctl enable --now joblens-log-aggregation.timer
```

Before enabling the timer, edit the copied service if the deployment user,
repository path, backup path, log path, or monitoring path differs from:

```text
User=joblens
WorkingDirectory=/srv/joblens-ai
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json
OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json
INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json
MONITOR_STATUS_FILE=/srv/joblens-monitoring/latest_status.json
```

The template skips public HTTPS checks by default. After DNS and TLS are stable,
set these in the service:

```text
Environment=SKIP_PUBLIC_HEALTH_CHECK=false
Environment=JOBLENS_HEALTH_BASE_URL=https://jobs.example.com
```

After an off-server backup destination and cost approval exist, set:

```text
Environment=SKIP_OFFSITE_BACKUP_CHECK=false
```

To deliver failure alerts to a generic HTTPS webhook, set:

```text
Environment=ALERT_ON_FAILURE=true
Environment=ALERT_WEBHOOK_URL=https://alerts.example.com/joblens
```

The monitor sends the compact JSON status file as the request body. Keep the
webhook URL in a root-owned systemd drop-in or another private server-side
configuration file, not in Git.

External uptime checks from outside the server are covered separately in
[external-uptime-monitoring.md](external-uptime-monitoring.md).

Check timer status:

```bash
systemctl list-timers joblens-ops-monitor.timer
systemctl status joblens-ops-monitor.service --no-pager
journalctl -u joblens-ops-monitor.service --since today
systemctl status joblens-log-aggregation.service --no-pager
```

## Failure Triage

Compose service check fails:

- run `docker compose --env-file .env.production -f docker-compose.prod.yml ps`
- collect logs with `collect_operations_logs.sh`
- check whether the latest deployment changed images, migrations, or env vars
- use the deployment rollback procedure if the failure started after a release

Public health check fails:

- confirm Caddy is running and ports 80 and 443 are reachable
- check Caddy logs for certificate or routing failures
- check `api` and `django-ops` logs for application startup errors
- verify `JOBLENS_DOMAIN`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`

Database backup check fails:

- run `systemctl status joblens-db-backup.service --no-pager`
- inspect `journalctl -u joblens-db-backup.service --since today`
- run a manual backup and then `verify_database_backup.sh`
- check disk usage on the backup directory

Off-server backup check fails:

- inspect `/srv/joblens-backups/latest_offsite_backup.json`
- run `upload_database_backup.sh` in dry-run mode first
- verify the destination URI, AWS credentials, and network egress
- confirm the local backup status is fresh before retrying an upload

Ingestion refresh check fails:

- run `systemctl status joblens-ingestion-refresh.service --no-pager`
- inspect `journalctl -u joblens-ingestion-refresh.service --since today`
- inspect `/srv/joblens-ingestion/<run-id>/canada-fetch-summary.md`
- run a manual refresh after verifying provider keys and database health

Log aggregation check fails:

- inspect `/srv/joblens-logs/latest_log_aggregation.json`
- run `aggregate_operations_logs.sh` manually and inspect stderr
- verify the deployment user can read Docker logs and selected journal units
- check disk usage and retention for `/srv/joblens-logs`

Disk check fails:

- inspect `df -h` and `docker system df`
- remove obsolete log snapshots after preserving any needed incident evidence
- verify backup retention is pruning old dumps
- prune Docker artifacts only after confirming they are not needed for rollback

## Current Limits

- external uptime monitoring runs through GitHub Actions rather than a paging-grade monitor
- alert delivery uses a generic webhook, not a paging escalation policy
- no dashboard page for the local status file
- no Prometheus or Grafana stack

Those can be added later if the server has enough capacity and the cost or
operational tradeoff is worth it.

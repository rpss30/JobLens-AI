# Local Log Aggregation

This runbook covers the low-cost central log aggregation path for the
single-server production deployment. It is a server-local workflow that
collects recent Docker Compose service logs and selected systemd journal
entries into one normalized JSONL file on the server. It creates no cloud resources
and does not require a hosted logging
provider.

## Files

```text
deploy/scripts/aggregate_operations_logs.sh
deploy/scripts/check_log_aggregation_status.sh
deploy/server/systemd/joblens-log-aggregation.service
deploy/server/systemd/joblens-log-aggregation.timer
```

## What Gets Aggregated

`aggregate_operations_logs.sh` collects:

- Compose logs for `caddy`, `dashboard`, `api`, `django-ops`, and `db`
- systemd journal entries for the operations monitor, database backup, and
  ingestion refresh timers

Each log line is written as one JSON object:

```json
{"collected_at":"2026-08-07T12:00:00Z","source":"compose","name":"api","observed_at":"2026-08-07T11:59:58Z","message":"service log line"}
```

The default local output is:

```text
deploy/log-aggregation/<run-id>.jsonl
deploy/log-aggregation/latest_log_aggregation.json
```

On the production server, use a directory outside the repository:

```text
/srv/joblens-logs
```

Restrict that directory to the deployment user because application logs can
contain request paths, stack traces, operational identifiers, and derived
analysis metadata.

## Manual Run

Run from the repository checkout on the server:

```bash
LOG_AGGREGATION_DIR=/srv/joblens-logs \
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json \
LOG_AGGREGATION_LINES=400 \
LOG_AGGREGATION_RETENTION_DAYS=14 \
INCLUDE_SYSTEMD_LOGS=true \
deploy/scripts/aggregate_operations_logs.sh
```

Useful defaults:

| Variable | Default |
| --- | --- |
| `DEPLOY_ENV_FILE` | `.env.production` |
| `COMPOSE_FILE` | `docker-compose.prod.yml` |
| `LOG_AGGREGATION_DIR` | `deploy/log-aggregation` |
| `LOG_AGGREGATION_STATUS_FILE` | `$LOG_AGGREGATION_DIR/latest_log_aggregation.json` |
| `LOG_AGGREGATION_SERVICES` | `caddy dashboard api django-ops db` |
| `LOG_AGGREGATION_LINES` | `400` |
| `LOG_AGGREGATION_RETENTION_DAYS` | `14` |
| `INCLUDE_SYSTEMD_LOGS` | `true` |
| `SYSTEMD_LOG_UNITS` | `joblens-ops-monitor.service joblens-db-backup.service joblens-ingestion-refresh.service` |
| `SYSTEMD_LOG_SINCE` | `24 hours ago` |
| `PYTHON_BIN` | `python3` |

## Status Check

Check that the latest aggregation succeeded and is fresh:

```bash
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json \
LOG_AGGREGATION_MAX_AGE_HOURS=6 \
deploy/scripts/check_log_aggregation_status.sh
```

The check exits nonzero if the status file is missing, the latest aggregation
failed, or the file is older than the configured freshness window.

`check_operations_status.sh` runs this freshness check as `log_aggregation`.

## Timer Installation

Install the timer on the server:

```bash
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-log-aggregation.service /etc/systemd/system/joblens-log-aggregation.service
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-log-aggregation.timer /etc/systemd/system/joblens-log-aggregation.timer
sudo systemctl daemon-reload
sudo systemctl enable --now joblens-log-aggregation.timer
```

Before enabling it, edit the copied service if the deployment user, repository
path, Compose file, or log directory differs from:

```text
User=joblens
WorkingDirectory=/srv/joblens-ai
LOG_AGGREGATION_DIR=/srv/joblens-logs
LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json
```

Check timer status:

```bash
systemctl list-timers joblens-log-aggregation.timer
systemctl status joblens-log-aggregation.service --no-pager
journalctl -u joblens-log-aggregation.service --since today
```

## Query Examples

Show recent API errors when `jq` is available:

```bash
jq 'select(.name == "api" and (.message | test("error|exception"; "i")))' /srv/joblens-logs/*.jsonl
```

Fallback without `jq`:

```bash
grep -i '"name":"api"' /srv/joblens-logs/*.jsonl | grep -Ei 'error|exception'
```

## Failure Triage

If aggregation fails:

- run `docker compose --env-file .env.production -f docker-compose.prod.yml ps`
- run `aggregate_operations_logs.sh` manually and inspect stderr
- verify the deployment user can read Docker logs and selected journal units
- check disk usage for `/srv/joblens-logs`
- use `collect_operations_logs.sh` for a timestamped incident snapshot

## Current Limits

- logs remain on the single production server unless an approved off-server
  destination is added later
- the aggregator keeps recent log windows, not an immutable audit archive
- there is no full-text search service, dashboard query page, or paging policy

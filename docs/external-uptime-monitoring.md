# External Uptime Monitoring

This runbook covers the low-cost external uptime check for JobLens. It uses a
scheduled GitHub Actions workflow to check the public edge from outside the
server. It does not create monitoring accounts, DNS records, cloud resources,
or paid alerting services.

## Files

```text
.github/workflows/uptime-check.yml
deploy/scripts/check_external_uptime.sh
deploy/scripts/send_operations_alert.sh
docs/external-uptime-monitoring.md
```

Generated uptime reports are written under:

```text
deploy/uptime-reports/
```

That directory is ignored by Git.

## What Gets Checked

`check_external_uptime.sh` checks the public routes that should work after a
production deployment:

| Path | Purpose |
| --- | --- |
| `/healthz` | Caddy edge health response |
| `/proxy/health` | Next.js server liveness behind the reverse proxy |
| `/api/health` | FastAPI health endpoint behind the reverse proxy |
| `/ops/login/` | Django operations login route behind the reverse proxy |

HTTP `2xx` and `3xx` responses are treated as healthy. Other status codes,
timeouts, and connection failures are recorded as failed endpoint checks.

## Local Use

Run against an already-approved production URL:

```bash
JOBLENS_UPTIME_BASE_URL=https://jobs.example.com \
UPTIME_STATUS_FILE=deploy/uptime-reports/latest_uptime_check.json \
deploy/scripts/check_external_uptime.sh
```

Useful defaults:

| Variable | Default |
| --- | --- |
| `JOBLENS_UPTIME_BASE_URL` | empty |
| `JOBLENS_DOMAIN` | empty |
| `UPTIME_PATHS` | `/healthz /proxy/health /api/health /ops/login/` |
| `UPTIME_RETRIES` | `2` |
| `UPTIME_DELAY_SECONDS` | `5` |
| `UPTIME_TIMEOUT_SECONDS` | `10` |
| `SKIP_UPTIME_CHECK_IF_UNCONFIGURED` | `true` |
| `ALERT_ON_FAILURE` | `false` |

If no base URL or domain is set, the script writes a skipped status and exits
successfully by default. Set `SKIP_UPTIME_CHECK_IF_UNCONFIGURED=false` when a
configured URL should be mandatory.

## Scheduled Workflow

The `External Uptime Check` workflow runs every 30 minutes and can also be
started manually. It uses:

```text
PRODUCTION_HEALTH_BASE_URL
PRODUCTION_DOMAIN
PRODUCTION_ALERT_WEBHOOK_URL
```

from repository or environment secrets. The manual workflow accepts a temporary
`base_url` override for testing a newly deployed domain before it becomes the
default monitor target.

The workflow uploads:

```text
deploy/uptime-reports/latest_uptime_check.json
```

as an artifact for review.

## Alert Delivery

When `PRODUCTION_ALERT_WEBHOOK_URL` is configured, the workflow sets
`ALERT_ON_FAILURE=true` and sends the uptime JSON status file through
`send_operations_alert.sh` with the `external_uptime_failed` event name.

Keep webhook URLs in private GitHub secrets. Do not commit them to this
repository.

## Triage

If the uptime check fails:

- open the uploaded JSON report and identify the failing path
- confirm the production domain resolves to the expected server
- run `check_production_health.sh` from a trusted machine
- inspect Caddy logs and application container logs
- check whether the last deployment, TLS renewal, or server firewall changed
- use the rollback runbook if the failure began after a release

## Current Limits

- GitHub Actions scheduling is not a paging-grade uptime service
- server-local log aggregation is configured separately
- no latency SLO or historical uptime dashboard is maintained
- no paid external monitoring provider is configured

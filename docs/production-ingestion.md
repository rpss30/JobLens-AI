# Production Ingestion Scheduling

This runbook covers scheduled Canada jobs refreshes for the low-cost
single-server production deployment. It uses Docker Compose, the existing
fetch/build/validate scripts, PostgreSQL seeding, local status files, and a
systemd timer. It creates no cloud resources.

## Files

```text
deploy/scripts/run_ingestion_refresh.sh
deploy/scripts/check_ingestion_refresh_status.sh
deploy/server/systemd/joblens-ingestion-refresh.service
deploy/server/systemd/joblens-ingestion-refresh.timer
```

## What The Refresh Does

`run_ingestion_refresh.sh` runs inside the already-started production Compose
stack:

1. verifies `.env.production` exists
2. verifies the `api` and `db` Compose services are running
3. fetches Canadian postings from Greenhouse, Lever, and Ashby
4. writes fetch JSON and Markdown summaries
5. builds the Groq-enriched Canada snapshot
6. writes snapshot JSON and Markdown summaries
7. validates the candidate snapshot before publishing it to PostgreSQL
8. replaces the PostgreSQL `canada_jobs` dataset with the validated snapshot
9. writes `latest_ingestion_refresh.json`

The script records ingestion-run metadata in PostgreSQL with `--save-run-to-db`
for both fetch and enrichment stages. The Django operations service can then
show run health, source failures, and extraction issues.

## Manual Refresh

Run from the repository checkout on the server:

```bash
DEPLOY_ENV_FILE=.env.production \
COMPOSE_FILE=docker-compose.prod.yml \
INGESTION_OUTPUT_DIR=/srv/joblens-ingestion \
INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json \
deploy/scripts/run_ingestion_refresh.sh
```

Useful defaults:

| Variable | Default |
| --- | --- |
| `DEPLOY_ENV_FILE` | `.env.production` |
| `COMPOSE_FILE` | `docker-compose.prod.yml` |
| `INGESTION_SERVICE` | `api` |
| `INGESTION_OUTPUT_DIR` | `deploy/ingestion` |
| `INGESTION_STATUS_FILE` | `$INGESTION_OUTPUT_DIR/latest_ingestion_refresh.json` |
| `INGESTION_DATASET_NAME` | `canada_jobs` |
| `INGESTION_MAX_JOBS` | `72` |
| `INGESTION_MAX_PER_COMPANY` | `6` |
| `INGESTION_MAX_PER_LOCATION` | `18` |
| `INGESTION_DELAY_SECONDS` | `1` |

Use a server path outside the repository, such as `/srv/joblens-ingestion`, for
production refresh artifacts. Keep that directory readable only by the
deployment user because refresh logs can include source errors and operational
context.

## Weekly Schedule

The repository includes systemd templates for a weekly refresh:

```bash
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-ingestion-refresh.service /etc/systemd/system/joblens-ingestion-refresh.service
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-ingestion-refresh.timer /etc/systemd/system/joblens-ingestion-refresh.timer
sudo systemctl daemon-reload
sudo systemctl enable --now joblens-ingestion-refresh.timer
```

Before enabling the timer, edit the copied service if the deployment user,
repository path, or artifact directory differs from:

```text
User=joblens
WorkingDirectory=/srv/joblens-ai
INGESTION_OUTPUT_DIR=/srv/joblens-ingestion
INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json
```

Check the timer:

```bash
systemctl list-timers joblens-ingestion-refresh.timer
systemctl status joblens-ingestion-refresh.service --no-pager
journalctl -u joblens-ingestion-refresh.service --since today
```

## Freshness Check

Check that the latest refresh succeeded and is not stale:

```bash
INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json \
INGESTION_MAX_AGE_HOURS=192 \
deploy/scripts/check_ingestion_refresh_status.sh
```

The broader production status check in
[operations-monitoring.md](operations-monitoring.md) runs this ingestion
freshness check alongside service health, backup freshness, and disk usage.

## Failure Triage

Refresh fails during fetch:

- inspect `canada-fetch-summary.md` in the run artifact directory
- check whether a single employer board failed or all providers failed
- rerun manually after transient network or provider errors settle

Refresh fails during enrichment:

- inspect `canada-snapshot-summary.md`
- verify `GROQ_API_KEY` is present in `.env.production`
- check Django operations extraction issues for empty or failed attempts
- consider raising `INGESTION_DELAY_SECONDS` if provider rate limits appear

Refresh fails during validation:

- inspect `canada-validation-summary.md`
- keep the previous PostgreSQL dataset active
- compare job count, company count, location coverage, and Groq coverage against
  the validation thresholds before reseeding manually

Refresh fails during seeding:

- verify Alembic migrations are current
- check PostgreSQL container health
- inspect database logs before rerunning

## Current Limits

- refreshes are scheduled weekly, not continuously streamed
- refresh artifacts are local to the server
- no off-server artifact copy is implemented
- no email, Slack, SMS, or paging alerts are sent
- no provider-specific retry queue is implemented
- no route triggers ingestion from the public app or operations service

Those can be added later if the operating cost and failure modes justify the
extra moving parts.

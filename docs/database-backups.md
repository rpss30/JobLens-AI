# Database Backups and Restore

This runbook covers PostgreSQL backups for the low-cost single-server
production path. It uses `pg_dump` from the existing PostgreSQL container and
writes backup files on the server filesystem. It creates no cloud resources.

## Files

```text
deploy/scripts/backup_database.sh
deploy/scripts/upload_database_backup.sh
deploy/scripts/verify_database_backup.sh
deploy/scripts/restore_database.sh
deploy/scripts/check_database_backup_status.sh
deploy/scripts/check_offsite_backup_status.sh
deploy/server/systemd/joblens-db-backup.service
deploy/server/systemd/joblens-db-backup.timer
```

## Backup Format

Backups are PostgreSQL custom-format dumps created with:

```text
pg_dump --format=custom --no-owner --no-privileges
```

The custom format is compact, supports `pg_restore`, and lets restore checks
fail fast with `--exit-on-error`. Ownership and privilege commands are omitted
so a backup can be restored into a fresh database owned by the production
database user.

Each successful backup writes:

```text
<backup-dir>/joblens_<timestamp>.dump
<backup-dir>/joblens_<timestamp>.dump.json
<backup-dir>/latest_backup.json
```

The JSON status file records status, start and finish timestamps, backup path,
file size, SHA-256 checksum, and retention settings. The status file is the
simple monitoring hook used by `check_database_backup_status.sh`.

## Manual Backup

Run from the repository checkout on the server:

```bash
BACKUP_DIR=/srv/joblens-backups \
DEPLOY_ENV_FILE=.env.production \
deploy/scripts/backup_database.sh
```

Defaults:

| Variable | Default |
| --- | --- |
| `DEPLOY_ENV_FILE` | `.env.production` |
| `COMPOSE_FILE` | `docker-compose.prod.yml` |
| `BACKUP_DIR` | `deploy/backups` |
| `BACKUP_RETENTION_DAYS` | `14` |
| `BACKUP_RETENTION_COUNT` | `14` |
| `BACKUP_COMPRESS_LEVEL` | `6` |
| `BACKUP_STATUS_FILE` | `$BACKUP_DIR/latest_backup.json` |
| `OFFSITE_BACKUP_ENABLED` | `false` |
| `OFFSITE_BACKUP_STATUS_FILE` | `$BACKUP_DIR/latest_offsite_backup.json` |

Use a server path outside the repository, such as `/srv/joblens-backups`, for
production backups. Keep that directory readable only by the deployment user
because dumps contain application data.

When `OFFSITE_BACKUP_ENABLED=true`, the backup script calls
`upload_database_backup.sh` after the local dump and manifest succeed. The
upload path is disabled by default and must be configured with an existing
destination before use.

## Retention

`backup_database.sh` prunes old local dumps after a successful backup:

- files older than `BACKUP_RETENTION_DAYS`
- files beyond the newest `BACKUP_RETENTION_COUNT`

Both rules apply only to files matching the configured backup label, which
defaults to `joblens_*.dump`.

## Daily Schedule

The repository includes systemd templates for a daily backup:

```bash
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-db-backup.service /etc/systemd/system/joblens-db-backup.service
sudo install -o root -g root -m 0644 deploy/server/systemd/joblens-db-backup.timer /etc/systemd/system/joblens-db-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now joblens-db-backup.timer
```

Before enabling the timer, edit the copied service if the deployment user,
repository path, or backup directory differs from:

```text
User=joblens
WorkingDirectory=/srv/joblens-ai
BACKUP_DIR=/srv/joblens-backups
```

Check the timer:

```bash
systemctl list-timers joblens-db-backup.timer
systemctl status joblens-db-backup.service --no-pager
journalctl -u joblens-db-backup.service --since today
```

## Backup Health Check

Check that the latest backup succeeded and is not stale:

```bash
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json \
BACKUP_MAX_AGE_HOURS=30 \
deploy/scripts/check_database_backup_status.sh
```

This script exits nonzero if the status file is missing, the latest backup
failed, or the status file is older than the allowed age.

The broader production status check in
[operations-monitoring.md](operations-monitoring.md) runs this backup freshness
check alongside service health and disk usage checks.

Off-server copy setup, dry-run behavior, status checks, and alert delivery are
covered in [offsite-backups-alerts.md](offsite-backups-alerts.md).

## Restore Test

Test a dump without touching the production database:

```bash
BACKUP_FILE=/srv/joblens-backups/joblens_20260806T120000Z.dump \
DEPLOY_ENV_FILE=.env.production \
deploy/scripts/verify_database_backup.sh
```

The verify script creates a temporary database inside the PostgreSQL container,
restores the dump with `pg_restore --exit-on-error`, runs a simple catalog
query, and drops the temporary database. This is the restore test that proves a
backup is usable.

Set `KEEP_RESTORE_CHECK_DATABASE=true` only when manually debugging a failed
restore test, then drop the temporary database when finished.

## Production Restore

The restore script is intentionally gated because it overwrites database state.
The default is a dry run:

```bash
BACKUP_FILE=/srv/joblens-backups/joblens_20260806T120000Z.dump \
deploy/scripts/restore_database.sh
```

Apply a restore only after choosing the correct dump and confirming the impact:

```bash
BACKUP_FILE=/srv/joblens-backups/joblens_20260806T120000Z.dump \
CONFIRM_RESTORE=yes \
DRY_RUN=no \
deploy/scripts/restore_database.sh
```

By default, the restore script:

1. verifies the backup in a temporary database
2. stops `dashboard`, `api`, and `django-ops`
3. restores with `pg_restore --clean --if-exists --exit-on-error`
4. starts the full Compose stack
5. runs public health checks when `JOBLENS_DOMAIN` or `JOBLENS_HEALTH_BASE_URL` is set

Use `SKIP_RESTORE_VERIFY=true` only when the verify step is impossible and the
risk has been accepted. Use `SKIP_PUBLIC_HEALTH_CHECK=true` only during isolated
maintenance where public routing is not available.

## Current Limits

- off-server backup copy is opt-in and requires a preapproved existing S3 URI
- no encryption-at-rest wrapper is added beyond the server disk controls
- no automated restore drill is scheduled
- alert delivery is opt-in through a generic webhook

Off-server storage should be added only with a clear cost note, retention
policy, restore test, and approval before any paid cloud storage is created.

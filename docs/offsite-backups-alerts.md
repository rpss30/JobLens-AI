# Off-Server Backups and Alerts

This runbook covers the opt-in off-server backup copy and generic webhook alert
path for the low-cost single-server deployment. It creates no cloud resources
by itself.

## Files

```text
deploy/scripts/upload_database_backup.sh
deploy/scripts/check_offsite_backup_status.sh
deploy/scripts/send_operations_alert.sh
deploy/scripts/backup_database.sh
deploy/scripts/check_operations_status.sh
```

## Cost and Approval

The upload script copies an existing local PostgreSQL dump to an existing S3
URI. It does not create buckets, policies, users, keys, alarms, or lifecycle
rules.

Before enabling real uploads, confirm:

- the S3 bucket already exists
- the bucket owner, region, and retention policy are known
- expected storage and request costs are approved
- the IAM principal has only the minimum write/read permissions for the backup prefix
- teardown and cleanup steps are documented privately

The default is `OFFSITE_BACKUP_DRY_RUN=true`, so running the script without
changing that variable only writes a local status file describing the intended
copy.

## Manual Dry Run

Create a local backup first:

```bash
BACKUP_DIR=/srv/joblens-backups \
DEPLOY_ENV_FILE=.env.production \
deploy/scripts/backup_database.sh
```

Then test the off-server command without uploading:

```bash
OFFSITE_BACKUP_URI=s3://existing-bucket/joblens/backups \
OFFSITE_BACKUP_DRY_RUN=true \
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json \
OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json \
deploy/scripts/upload_database_backup.sh
```

The dry run writes:

```text
/srv/joblens-backups/latest_offsite_backup.json
```

with `status` set to `dry_run`.

## Enable Real Uploads

After approval, use an existing bucket and set:

```bash
OFFSITE_BACKUP_URI=s3://existing-bucket/joblens/backups \
OFFSITE_BACKUP_DRY_RUN=false \
BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json \
OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json \
deploy/scripts/upload_database_backup.sh
```

Successful uploads copy:

```text
joblens_<timestamp>.dump
joblens_<timestamp>.dump.json
latest_offsite_backup.json
```

to the configured prefix. By default, the AWS CLI uses `--sse AES256` and
`--storage-class STANDARD`. Override `AWS_S3_SSE` or `AWS_S3_STORAGE_CLASS`
only after checking the bucket policy and restore requirements.

To upload after every scheduled local backup, edit the installed systemd service
or add a drop-in with:

```text
Environment=OFFSITE_BACKUP_ENABLED=true
Environment=OFFSITE_BACKUP_URI=s3://existing-bucket/joblens/backups
Environment=OFFSITE_BACKUP_DRY_RUN=false
```

## Freshness Check

Check the latest successful off-server copy:

```bash
OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json \
OFFSITE_BACKUP_MAX_AGE_HOURS=30 \
deploy/scripts/check_offsite_backup_status.sh
```

This exits nonzero if the status file is missing, not marked `succeeded`, lacks
an S3 backup URI, or is older than the configured freshness window.

When off-server copies are enabled, also enable the aggregate monitoring check:

```text
Environment=SKIP_OFFSITE_BACKUP_CHECK=false
Environment=OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json
```

## Alert Delivery

`send_operations_alert.sh` sends the JSON monitoring status file to a generic
HTTPS webhook. Test without network delivery:

```bash
ALERT_DRY_RUN=true \
ALERT_STATUS_FILE=/srv/joblens-monitoring/latest_status.json \
deploy/scripts/send_operations_alert.sh
```

Enable alert delivery from the operations monitor with a private systemd
drop-in:

```text
Environment=ALERT_ON_FAILURE=true
Environment=ALERT_WEBHOOK_URL=https://alerts.example.com/joblens
```

By default, an alert delivery failure does not hide the original monitoring
failure. Set `ALERT_FAILURES_ARE_FATAL=true` only if the service should fail
when both the monitored system and alert transport fail.

## Current Limits

- no S3 bucket or IAM principal is created by this repository
- no lifecycle policy is installed
- no automated restore drill is scheduled from the off-server copy
- no external uptime monitor is configured
- no central log aggregation is configured

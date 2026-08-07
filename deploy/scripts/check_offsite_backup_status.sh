#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-deploy/backups}"
OFFSITE_BACKUP_STATUS_FILE="${OFFSITE_BACKUP_STATUS_FILE:-${BACKUP_DIR}/latest_offsite_backup.json}"
OFFSITE_BACKUP_MAX_AGE_HOURS="${OFFSITE_BACKUP_MAX_AGE_HOURS:-30}"

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 1
  fi
}

file_modified_epoch() {
  local file_path="$1"

  if stat -c %Y "${file_path}" >/dev/null 2>&1; then
    stat -c %Y "${file_path}"
    return
  fi

  stat -f %m "${file_path}"
}

require_positive_integer OFFSITE_BACKUP_MAX_AGE_HOURS "${OFFSITE_BACKUP_MAX_AGE_HOURS}"

if [[ ! -f "${OFFSITE_BACKUP_STATUS_FILE}" ]]; then
  echo "Off-server backup status file is missing: ${OFFSITE_BACKUP_STATUS_FILE}" >&2
  exit 1
fi

if ! grep -q '"status": "succeeded"' "${OFFSITE_BACKUP_STATUS_FILE}"; then
  echo "Latest off-server backup did not succeed according to ${OFFSITE_BACKUP_STATUS_FILE}." >&2
  exit 1
fi

if ! grep -q '"backup_uri": "s3://' "${OFFSITE_BACKUP_STATUS_FILE}"; then
  echo "Off-server backup status does not include an S3 backup URI." >&2
  exit 1
fi

now_epoch="$(date +%s)"
modified_epoch="$(file_modified_epoch "${OFFSITE_BACKUP_STATUS_FILE}")"
age_hours="$(((now_epoch - modified_epoch) / 3600))"

if (( age_hours > OFFSITE_BACKUP_MAX_AGE_HOURS )); then
  echo "Latest off-server backup is stale: ${age_hours}h old." >&2
  exit 1
fi

echo "Latest off-server backup is healthy: ${OFFSITE_BACKUP_STATUS_FILE} (${age_hours}h old)."

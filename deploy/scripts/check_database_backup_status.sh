#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-deploy/backups}"
BACKUP_STATUS_FILE="${BACKUP_STATUS_FILE:-${BACKUP_DIR}/latest_backup.json}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-30}"

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

require_positive_integer BACKUP_MAX_AGE_HOURS "${BACKUP_MAX_AGE_HOURS}"

if [[ ! -f "${BACKUP_STATUS_FILE}" ]]; then
  echo "Backup status file is missing: ${BACKUP_STATUS_FILE}" >&2
  exit 1
fi

if ! grep -q '"status": "succeeded"' "${BACKUP_STATUS_FILE}"; then
  echo "Latest backup did not succeed according to ${BACKUP_STATUS_FILE}." >&2
  exit 1
fi

now_epoch="$(date +%s)"
modified_epoch="$(file_modified_epoch "${BACKUP_STATUS_FILE}")"
age_hours="$(((now_epoch - modified_epoch) / 3600))"

if (( age_hours > BACKUP_MAX_AGE_HOURS )); then
  echo "Latest successful backup is stale: ${age_hours}h old." >&2
  exit 1
fi

echo "Latest database backup is healthy: ${BACKUP_STATUS_FILE} (${age_hours}h old)."

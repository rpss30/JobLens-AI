#!/usr/bin/env bash
set -euo pipefail

INGESTION_STATUS_FILE="${INGESTION_STATUS_FILE:-deploy/ingestion/latest_ingestion_refresh.json}"
INGESTION_MAX_AGE_HOURS="${INGESTION_MAX_AGE_HOURS:-192}"

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

require_positive_integer INGESTION_MAX_AGE_HOURS "${INGESTION_MAX_AGE_HOURS}"

if [[ ! -f "${INGESTION_STATUS_FILE}" ]]; then
  echo "Ingestion refresh status file is missing: ${INGESTION_STATUS_FILE}" >&2
  exit 1
fi

if ! grep -q '"status": "succeeded"' "${INGESTION_STATUS_FILE}"; then
  echo "Latest ingestion refresh did not succeed according to ${INGESTION_STATUS_FILE}." >&2
  exit 1
fi

now_epoch="$(date +%s)"
modified_epoch="$(file_modified_epoch "${INGESTION_STATUS_FILE}")"
age_hours="$(((now_epoch - modified_epoch) / 3600))"

if (( age_hours > INGESTION_MAX_AGE_HOURS )); then
  echo "Latest successful ingestion refresh is stale: ${age_hours}h old." >&2
  exit 1
fi

echo "Latest ingestion refresh is healthy: ${INGESTION_STATUS_FILE} (${age_hours}h old)."

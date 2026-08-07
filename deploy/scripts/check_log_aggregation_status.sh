#!/usr/bin/env bash
set -euo pipefail

LOG_AGGREGATION_DIR="${LOG_AGGREGATION_DIR:-deploy/log-aggregation}"
LOG_AGGREGATION_STATUS_FILE="${LOG_AGGREGATION_STATUS_FILE:-${LOG_AGGREGATION_DIR}/latest_log_aggregation.json}"
LOG_AGGREGATION_MAX_AGE_HOURS="${LOG_AGGREGATION_MAX_AGE_HOURS:-6}"

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 2
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

require_positive_integer LOG_AGGREGATION_MAX_AGE_HOURS "${LOG_AGGREGATION_MAX_AGE_HOURS}"

if [[ ! -f "${LOG_AGGREGATION_STATUS_FILE}" ]]; then
  echo "Log aggregation status file is missing: ${LOG_AGGREGATION_STATUS_FILE}" >&2
  exit 1
fi

if ! grep -q '"status": "succeeded"' "${LOG_AGGREGATION_STATUS_FILE}"; then
  echo "Latest log aggregation did not succeed according to ${LOG_AGGREGATION_STATUS_FILE}." >&2
  exit 1
fi

now_epoch="$(date +%s)"
modified_epoch="$(file_modified_epoch "${LOG_AGGREGATION_STATUS_FILE}")"
age_hours="$(((now_epoch - modified_epoch) / 3600))"

if (( age_hours > LOG_AGGREGATION_MAX_AGE_HOURS )); then
  echo "Latest successful log aggregation is stale: ${age_hours}h old." >&2
  exit 1
fi

echo "Latest log aggregation is healthy: ${LOG_AGGREGATION_STATUS_FILE} (${age_hours}h old)."

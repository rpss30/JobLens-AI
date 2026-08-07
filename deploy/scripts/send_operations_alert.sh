#!/usr/bin/env bash
set -euo pipefail

ALERT_STATUS_FILE="${ALERT_STATUS_FILE:-${MONITOR_STATUS_FILE:-deploy/monitoring/latest_status.json}}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
ALERT_EVENT="${ALERT_EVENT:-operations_status_failed}"
ALERT_DRY_RUN="${ALERT_DRY_RUN:-false}"
ALERT_CONNECT_TIMEOUT_SECONDS="${ALERT_CONNECT_TIMEOUT_SECONDS:-5}"
ALERT_MAX_TIME_SECONDS="${ALERT_MAX_TIME_SECONDS:-15}"

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 1
  fi
}

require_positive_integer ALERT_CONNECT_TIMEOUT_SECONDS "${ALERT_CONNECT_TIMEOUT_SECONDS}"
require_positive_integer ALERT_MAX_TIME_SECONDS "${ALERT_MAX_TIME_SECONDS}"

if [[ ! -f "${ALERT_STATUS_FILE}" ]]; then
  echo "Alert status file is missing: ${ALERT_STATUS_FILE}" >&2
  exit 1
fi

if [[ "${ALERT_DRY_RUN}" == "true" ]]; then
  echo "dry run: would send ${ALERT_EVENT} alert from ${ALERT_STATUS_FILE}."
  exit 0
fi

if [[ -z "${ALERT_WEBHOOK_URL}" ]]; then
  echo "ALERT_WEBHOOK_URL is required when ALERT_DRY_RUN is false." >&2
  exit 1
fi

curl \
  --fail \
  --show-error \
  --silent \
  --connect-timeout "${ALERT_CONNECT_TIMEOUT_SECONDS}" \
  --max-time "${ALERT_MAX_TIME_SECONDS}" \
  --header "Content-Type: application/json" \
  --header "X-JobLens-Alert: ${ALERT_EVENT}" \
  --request POST \
  --data-binary @"${ALERT_STATUS_FILE}" \
  "${ALERT_WEBHOOK_URL}" \
  >/dev/null

echo "Operations alert delivered for ${ALERT_EVENT}."

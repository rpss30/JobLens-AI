#!/usr/bin/env bash
set -euo pipefail

JOBLENS_UPTIME_BASE_URL="${JOBLENS_UPTIME_BASE_URL:-${JOBLENS_HEALTH_BASE_URL:-}}"
JOBLENS_DOMAIN="${JOBLENS_DOMAIN:-}"
UPTIME_STATUS_FILE="${UPTIME_STATUS_FILE:-deploy/uptime-reports/latest_uptime_check.json}"
UPTIME_PATHS="${UPTIME_PATHS:-/healthz /api/health /ops/login/}"
UPTIME_RETRIES="${UPTIME_RETRIES:-2}"
UPTIME_DELAY_SECONDS="${UPTIME_DELAY_SECONDS:-5}"
UPTIME_TIMEOUT_SECONDS="${UPTIME_TIMEOUT_SECONDS:-10}"
SKIP_UPTIME_CHECK_IF_UNCONFIGURED="${SKIP_UPTIME_CHECK_IF_UNCONFIGURED:-true}"
ALERT_ON_FAILURE="${ALERT_ON_FAILURE:-false}"
ALERT_FAILURES_ARE_FATAL="${ALERT_FAILURES_ARE_FATAL:-false}"
CURL_BIN="${CURL_BIN:-curl}"

endpoint_paths=()
endpoint_statuses=()
endpoint_codes=()
endpoint_attempts=()
overall_status="ok"
overall_exit=0

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 1
  fi
}

record_endpoint() {
  local path="$1"
  local status="$2"
  local status_code="$3"
  local attempts="$4"

  endpoint_paths+=("${path}")
  endpoint_statuses+=("${status}")
  endpoint_codes+=("${status_code}")
  endpoint_attempts+=("${attempts}")

  if [[ "${status}" == "failed" ]]; then
    overall_status="failed"
    overall_exit=1
  fi
}

write_status_file() {
  local checked_at
  local status_dir

  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status_dir="$(dirname "${UPTIME_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${overall_status}"
    printf '  "checked_at": "%s",\n' "${checked_at}"
    printf '  "base_url": "%s",\n' "${JOBLENS_UPTIME_BASE_URL}"
    printf '  "endpoints": [\n'

    for index in "${!endpoint_paths[@]}"; do
      printf '    {"path": "%s", "status": "%s", "status_code": "%s", "attempts": %s}' \
        "${endpoint_paths[${index}]}" \
        "${endpoint_statuses[${index}]}" \
        "${endpoint_codes[${index}]}" \
        "${endpoint_attempts[${index}]}"

      if (( index < ${#endpoint_paths[@]} - 1 )); then
        printf ','
      fi

      printf '\n'
    done

    printf '  ]\n'
    printf '}\n'
  } > "${UPTIME_STATUS_FILE}.tmp"

  mv "${UPTIME_STATUS_FILE}.tmp" "${UPTIME_STATUS_FILE}"
}

send_failure_alert() {
  if [[ "${overall_status}" == "ok" || "${ALERT_ON_FAILURE}" != "true" ]]; then
    return
  fi

  if ALERT_STATUS_FILE="${UPTIME_STATUS_FILE}" \
    ALERT_EVENT="external_uptime_failed" \
    "$(dirname "${BASH_SOURCE[0]}")/send_operations_alert.sh"; then
    echo "External uptime alert delivered."
    return
  fi

  local alert_exit_code=$?
  echo "External uptime alert delivery failed with exit code ${alert_exit_code}." >&2

  if [[ "${ALERT_FAILURES_ARE_FATAL}" == "true" ]]; then
    overall_exit=1
  fi
}

check_endpoint() {
  local path="$1"
  local url="${JOBLENS_UPTIME_BASE_URL}${path}"
  local attempt
  local status_code="000"

  for attempt in $(seq 1 "${UPTIME_RETRIES}"); do
    status_code="$(
      "${CURL_BIN}" \
        --location \
        --silent \
        --output /dev/null \
        --write-out "%{http_code}" \
        --max-time "${UPTIME_TIMEOUT_SECONDS}" \
        "${url}" || true
    )"

    if [[ -z "${status_code}" ]]; then
      status_code="000"
    fi

    if [[ "${status_code}" =~ ^[23][0-9][0-9]$ ]]; then
      record_endpoint "${path}" "ok" "${status_code}" "${attempt}"
      return
    fi

    if [[ "${attempt}" != "${UPTIME_RETRIES}" ]]; then
      sleep "${UPTIME_DELAY_SECONDS}"
    fi
  done

  record_endpoint "${path}" "failed" "${status_code}" "${UPTIME_RETRIES}"
}

require_positive_integer UPTIME_RETRIES "${UPTIME_RETRIES}"
require_positive_integer UPTIME_DELAY_SECONDS "${UPTIME_DELAY_SECONDS}"
require_positive_integer UPTIME_TIMEOUT_SECONDS "${UPTIME_TIMEOUT_SECONDS}"

if [[ -z "${JOBLENS_UPTIME_BASE_URL}" && -n "${JOBLENS_DOMAIN}" ]]; then
  JOBLENS_UPTIME_BASE_URL="https://${JOBLENS_DOMAIN}"
fi

if [[ -z "${JOBLENS_UPTIME_BASE_URL}" ]]; then
  overall_status="skipped"
  write_status_file
  echo "Skipping external uptime check; set JOBLENS_UPTIME_BASE_URL or JOBLENS_DOMAIN."

  if [[ "${SKIP_UPTIME_CHECK_IF_UNCONFIGURED}" == "true" ]]; then
    exit 0
  fi

  exit 1
fi

JOBLENS_UPTIME_BASE_URL="${JOBLENS_UPTIME_BASE_URL%/}"

for path in ${UPTIME_PATHS}; do
  check_endpoint "${path}"
done

write_status_file
send_failure_alert

echo "External uptime check ${overall_status}; wrote ${UPTIME_STATUS_FILE}."
exit "${overall_exit}"

#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
EXPECTED_SERVICES="${EXPECTED_SERVICES:-caddy dashboard api django-ops db}"
MONITOR_STATUS_FILE="${MONITOR_STATUS_FILE:-deploy/monitoring/latest_status.json}"
SKIP_COMPOSE_CHECK="${SKIP_COMPOSE_CHECK:-false}"
SKIP_PUBLIC_HEALTH_CHECK="${SKIP_PUBLIC_HEALTH_CHECK:-false}"
SKIP_BACKUP_STATUS_CHECK="${SKIP_BACKUP_STATUS_CHECK:-false}"
SKIP_OFFSITE_BACKUP_CHECK="${SKIP_OFFSITE_BACKUP_CHECK:-true}"
SKIP_INGESTION_REFRESH_CHECK="${SKIP_INGESTION_REFRESH_CHECK:-false}"
SKIP_LOG_AGGREGATION_CHECK="${SKIP_LOG_AGGREGATION_CHECK:-false}"
SKIP_DISK_CHECK="${SKIP_DISK_CHECK:-false}"
ALERT_ON_FAILURE="${ALERT_ON_FAILURE:-false}"
ALERT_FAILURES_ARE_FATAL="${ALERT_FAILURES_ARE_FATAL:-false}"

check_names=()
check_statuses=()
check_exit_codes=()
overall_status="ok"
overall_exit=0

record_check() {
  local name="$1"
  local status="$2"
  local exit_code="$3"

  check_names+=("${name}")
  check_statuses+=("${status}")
  check_exit_codes+=("${exit_code}")

  if [[ "${status}" == "failed" ]]; then
    overall_status="failed"
    overall_exit=1
  fi
}

run_check() {
  local name="$1"
  shift

  echo "Running check: ${name}"

  if "$@"; then
    record_check "${name}" "ok" "0"
    return
  fi

  local exit_code=$?
  record_check "${name}" "failed" "${exit_code}"
}

compose() {
  docker compose --env-file "${DEPLOY_ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

check_compose_services() {
  local running_services

  running_services="$(compose ps --status running --services)"

  for service in ${EXPECTED_SERVICES}; do
    if ! grep -Fxq "${service}" <<< "${running_services}"; then
      echo "Compose service is not running: ${service}" >&2
      return 1
    fi
  done

  compose ps
}

run_public_health_check() {
  if [[ -z "${JOBLENS_HEALTH_BASE_URL:-}" && -z "${JOBLENS_DOMAIN:-}" ]]; then
    echo "Skipping public health check; set JOBLENS_DOMAIN or JOBLENS_HEALTH_BASE_URL."
    record_check "public_health" "skipped" "0"
    return
  fi

  run_check "public_health" "$(dirname "${BASH_SOURCE[0]}")/check_production_health.sh"
}

run_backup_status_check() {
  BACKUP_STATUS_FILE="${BACKUP_STATUS_FILE:-/srv/joblens-backups/latest_backup.json}" \
  BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-30}" \
    "$(dirname "${BASH_SOURCE[0]}")/check_database_backup_status.sh"
}

run_offsite_backup_status_check() {
  OFFSITE_BACKUP_STATUS_FILE="${OFFSITE_BACKUP_STATUS_FILE:-/srv/joblens-backups/latest_offsite_backup.json}" \
  OFFSITE_BACKUP_MAX_AGE_HOURS="${OFFSITE_BACKUP_MAX_AGE_HOURS:-30}" \
    "$(dirname "${BASH_SOURCE[0]}")/check_offsite_backup_status.sh"
}

run_ingestion_refresh_check() {
  INGESTION_STATUS_FILE="${INGESTION_STATUS_FILE:-/srv/joblens-ingestion/latest_ingestion_refresh.json}" \
  INGESTION_MAX_AGE_HOURS="${INGESTION_MAX_AGE_HOURS:-192}" \
    "$(dirname "${BASH_SOURCE[0]}")/check_ingestion_refresh_status.sh"
}

run_log_aggregation_check() {
  LOG_AGGREGATION_STATUS_FILE="${LOG_AGGREGATION_STATUS_FILE:-/srv/joblens-logs/latest_log_aggregation.json}" \
  LOG_AGGREGATION_MAX_AGE_HOURS="${LOG_AGGREGATION_MAX_AGE_HOURS:-6}" \
    "$(dirname "${BASH_SOURCE[0]}")/check_log_aggregation_status.sh"
}

run_disk_check() {
  DISK_PATHS="${DISK_PATHS:-/ /srv/joblens-backups /srv/joblens-logs}" \
  DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-80}" \
  DISK_CRITICAL_PERCENT="${DISK_CRITICAL_PERCENT:-90}" \
  SKIP_MISSING_DISK_PATHS="${SKIP_MISSING_DISK_PATHS:-false}" \
    "$(dirname "${BASH_SOURCE[0]}")/check_disk_usage.sh"
}

write_status_file() {
  local checked_at
  local status_dir

  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status_dir="$(dirname "${MONITOR_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${overall_status}"
    printf '  "checked_at": "%s",\n' "${checked_at}"
    printf '  "checks": [\n'

    for index in "${!check_names[@]}"; do
      printf '    {"name": "%s", "status": "%s", "exit_code": %s}' \
        "${check_names[${index}]}" \
        "${check_statuses[${index}]}" \
        "${check_exit_codes[${index}]}"

      if (( index < ${#check_names[@]} - 1 )); then
        printf ','
      fi

      printf '\n'
    done

    printf '  ]\n'
    printf '}\n'
  } > "${MONITOR_STATUS_FILE}.tmp"

  mv "${MONITOR_STATUS_FILE}.tmp" "${MONITOR_STATUS_FILE}"
}

send_failure_alert() {
  if [[ "${overall_status}" == "ok" || "${ALERT_ON_FAILURE}" != "true" ]]; then
    return
  fi

  if ALERT_STATUS_FILE="${MONITOR_STATUS_FILE}" \
    "$(dirname "${BASH_SOURCE[0]}")/send_operations_alert.sh"; then
    record_check "alert_delivery" "ok" "0"
    return
  else
    local alert_exit_code=$?
    record_check "alert_delivery" "failed" "${alert_exit_code}"
  fi

  if [[ "${ALERT_FAILURES_ARE_FATAL}" == "true" ]]; then
    overall_exit=1
  fi
}

if [[ "${SKIP_COMPOSE_CHECK}" == "true" ]]; then
  record_check "compose_services" "skipped" "0"
else
  run_check "compose_services" check_compose_services
fi

if [[ "${SKIP_PUBLIC_HEALTH_CHECK}" == "true" ]]; then
  record_check "public_health" "skipped" "0"
else
  run_public_health_check
fi

if [[ "${SKIP_BACKUP_STATUS_CHECK}" == "true" ]]; then
  record_check "database_backup" "skipped" "0"
else
  run_check "database_backup" run_backup_status_check
fi

if [[ "${SKIP_OFFSITE_BACKUP_CHECK}" == "true" ]]; then
  record_check "offsite_backup" "skipped" "0"
else
  run_check "offsite_backup" run_offsite_backup_status_check
fi

if [[ "${SKIP_INGESTION_REFRESH_CHECK}" == "true" ]]; then
  record_check "ingestion_refresh" "skipped" "0"
else
  run_check "ingestion_refresh" run_ingestion_refresh_check
fi

if [[ "${SKIP_LOG_AGGREGATION_CHECK}" == "true" ]]; then
  record_check "log_aggregation" "skipped" "0"
else
  run_check "log_aggregation" run_log_aggregation_check
fi

if [[ "${SKIP_DISK_CHECK}" == "true" ]]; then
  record_check "disk_usage" "skipped" "0"
else
  run_check "disk_usage" run_disk_check
fi

write_status_file
send_failure_alert
write_status_file

echo "Operations status ${overall_status}; wrote ${MONITOR_STATUS_FILE}."
exit "${overall_exit}"

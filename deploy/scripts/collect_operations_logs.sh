#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
LOG_DIR="${LOG_DIR:-deploy/logs}"
LOG_TIMESTAMP="${LOG_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_SERVICES="${LOG_SERVICES:-caddy frontend api django-ops db}"
LOG_LINES="${LOG_LINES:-300}"
INCLUDE_SYSTEMD_LOGS="${INCLUDE_SYSTEMD_LOGS:-false}"

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 1
  fi
}

compose() {
  docker compose --env-file "${DEPLOY_ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

require_positive_integer LOG_LINES "${LOG_LINES}"

snapshot_dir="${LOG_DIR}/${LOG_TIMESTAMP}"
mkdir -p "${snapshot_dir}"

compose ps > "${snapshot_dir}/compose_ps.txt"

for service in ${LOG_SERVICES}; do
  compose logs --timestamps --tail "${LOG_LINES}" "${service}" > "${snapshot_dir}/${service}.log" 2>&1 || {
    echo "Failed to collect logs for ${service}; see ${snapshot_dir}/${service}.log." >&2
  }
done

if [[ "${INCLUDE_SYSTEMD_LOGS}" == "true" ]]; then
  journalctl \
    -u joblens-ops-monitor.service \
    -u joblens-db-backup.service \
    --since "24 hours ago" \
    --no-pager > "${snapshot_dir}/systemd.log" 2>&1 || true
fi

{
  printf '{\n'
  printf '  "collected_at": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "log_dir": "%s",\n' "${snapshot_dir}"
  printf '  "services": "%s",\n' "${LOG_SERVICES}"
  printf '  "log_lines": %s,\n' "${LOG_LINES}"
  printf '  "included_systemd_logs": "%s"\n' "${INCLUDE_SYSTEMD_LOGS}"
  printf '}\n'
} > "${snapshot_dir}/manifest.json"

echo "Operations log snapshot written to ${snapshot_dir}."

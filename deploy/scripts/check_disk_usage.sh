#!/usr/bin/env bash
set -euo pipefail

DISK_PATHS="${DISK_PATHS:-/ /srv/joblens-backups}"
DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-80}"
DISK_CRITICAL_PERCENT="${DISK_CRITICAL_PERCENT:-90}"
SKIP_MISSING_DISK_PATHS="${SKIP_MISSING_DISK_PATHS:-false}"

require_percent() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]?$|^100$ ]]; then
    echo "${name} must be an integer from 1 through 100." >&2
    exit 2
  fi
}

require_percent DISK_WARN_PERCENT "${DISK_WARN_PERCENT}"
require_percent DISK_CRITICAL_PERCENT "${DISK_CRITICAL_PERCENT}"

if (( DISK_WARN_PERCENT >= DISK_CRITICAL_PERCENT )); then
  echo "DISK_WARN_PERCENT must be lower than DISK_CRITICAL_PERCENT." >&2
  exit 2
fi

overall_status="ok"
overall_exit=0

for path in ${DISK_PATHS}; do
  if [[ ! -e "${path}" ]]; then
    if [[ "${SKIP_MISSING_DISK_PATHS}" == "true" ]]; then
      echo "skipped missing disk path: ${path}"
      continue
    fi

    echo "missing disk path: ${path}" >&2
    overall_status="critical"
    overall_exit=2
    continue
  fi

  usage_percent="$(df -P "${path}" | awk 'NR == 2 {gsub("%", "", $5); print $5}')"
  available_kb="$(df -P "${path}" | awk 'NR == 2 {print $4}')"

  if (( usage_percent >= DISK_CRITICAL_PERCENT )); then
    echo "critical disk usage: ${path} ${usage_percent}% used, ${available_kb} KB available" >&2
    overall_status="critical"
    overall_exit=2
  elif (( usage_percent >= DISK_WARN_PERCENT )); then
    echo "warning disk usage: ${path} ${usage_percent}% used, ${available_kb} KB available" >&2
    if [[ "${overall_status}" != "critical" ]]; then
      overall_status="warning"
      overall_exit=1
    fi
  else
    echo "ok disk usage: ${path} ${usage_percent}% used, ${available_kb} KB available"
  fi
done

exit "${overall_exit}"

#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
LOG_AGGREGATION_DIR="${LOG_AGGREGATION_DIR:-deploy/log-aggregation}"
LOG_AGGREGATION_STATUS_FILE="${LOG_AGGREGATION_STATUS_FILE:-${LOG_AGGREGATION_DIR}/latest_log_aggregation.json}"
LOG_AGGREGATION_RUN_ID="${LOG_AGGREGATION_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_AGGREGATION_FILE="${LOG_AGGREGATION_FILE:-${LOG_AGGREGATION_DIR}/${LOG_AGGREGATION_RUN_ID}.jsonl}"
LOG_AGGREGATION_SERVICES="${LOG_AGGREGATION_SERVICES:-caddy frontend api django-ops db}"
LOG_AGGREGATION_LINES="${LOG_AGGREGATION_LINES:-400}"
LOG_AGGREGATION_RETENTION_DAYS="${LOG_AGGREGATION_RETENTION_DAYS:-14}"
INCLUDE_SYSTEMD_LOGS="${INCLUDE_SYSTEMD_LOGS:-true}"
SKIP_COMPOSE_LOGS="${SKIP_COMPOSE_LOGS:-false}"
SYSTEMD_LOG_UNITS="${SYSTEMD_LOG_UNITS:-joblens-ops-monitor.service joblens-db-backup.service joblens-ingestion-refresh.service}"
SYSTEMD_LOG_SINCE="${SYSTEMD_LOG_SINCE:-24 hours ago}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

source_types=()
source_names=()
source_statuses=()
source_line_counts=()
failure_count=0
line_count=0

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 2
  fi
}

record_source() {
  local source_type="$1"
  local source_name="$2"
  local status="$3"
  local count="$4"

  source_types+=("${source_type}")
  source_names+=("${source_name}")
  source_statuses+=("${status}")
  source_line_counts+=("${count}")
  line_count=$((line_count + count))

  if [[ "${status}" == "failed" ]]; then
    failure_count=$((failure_count + 1))
  fi
}

compose() {
  docker compose --env-file "${DEPLOY_ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

append_jsonl() {
  local source_type="$1"
  local source_name="$2"
  local raw_file="$3"
  local output_file="$4"
  local collected_at="$5"

  "${PYTHON_BIN}" - "${source_type}" "${source_name}" "${raw_file}" "${output_file}" "${collected_at}" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

source_type, source_name, raw_path, output_path, collected_at = sys.argv[1:]
timestamp_pattern = re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ][^\s]+)\s+(?P<message>.*)$")

with Path(raw_path).open(encoding="utf-8", errors="replace") as source:
    with Path(output_path).open("a", encoding="utf-8") as output:
        for line in source:
            message = line.rstrip("\n")
            observed_at = None
            match = timestamp_pattern.match(message)

            if match:
                observed_at = match.group("timestamp")
                message = match.group("message")

            output.write(
                json.dumps(
                    {
                        "collected_at": collected_at,
                        "source": source_type,
                        "name": source_name,
                        "observed_at": observed_at,
                        "message": message,
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
PY
}

count_lines() {
  local path="$1"

  wc -l < "${path}" | tr -d " "
}

write_status_file() {
  local status="$1"
  local collected_at="$2"
  local status_dir

  status_dir="$(dirname "${LOG_AGGREGATION_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${status}"
    printf '  "collected_at": "%s",\n' "${collected_at}"
    printf '  "log_file": "%s",\n' "${LOG_AGGREGATION_FILE}"
    printf '  "line_count": %s,\n' "${line_count}"
    printf '  "retention_days": %s,\n' "${LOG_AGGREGATION_RETENTION_DAYS}"
    printf '  "sources": [\n'

    for index in "${!source_names[@]}"; do
      printf '    {"type": "%s", "name": "%s", "status": "%s", "line_count": %s}' \
        "${source_types[${index}]}" \
        "${source_names[${index}]}" \
        "${source_statuses[${index}]}" \
        "${source_line_counts[${index}]}"

      if (( index < ${#source_names[@]} - 1 )); then
        printf ','
      fi

      printf '\n'
    done

    printf '  ]\n'
    printf '}\n'
  } > "${LOG_AGGREGATION_STATUS_FILE}.tmp"

  mv "${LOG_AGGREGATION_STATUS_FILE}.tmp" "${LOG_AGGREGATION_STATUS_FILE}"
}

prune_old_logs() {
  find "${LOG_AGGREGATION_DIR}" \
    -type f \
    -name "*.jsonl" \
    -mtime "+${LOG_AGGREGATION_RETENTION_DAYS}" \
    -delete
}

require_positive_integer LOG_AGGREGATION_LINES "${LOG_AGGREGATION_LINES}"
require_positive_integer LOG_AGGREGATION_RETENTION_DAYS "${LOG_AGGREGATION_RETENTION_DAYS}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "${PYTHON_BIN} is required to write structured log records." >&2
  exit 2
fi

collected_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
work_dir="$(mktemp -d)"
mkdir -p "${LOG_AGGREGATION_DIR}"
: > "${LOG_AGGREGATION_FILE}.tmp"

cleanup() {
  rm -rf "${work_dir}"
}
trap cleanup EXIT

if [[ "${SKIP_COMPOSE_LOGS}" == "true" ]]; then
  record_source "compose" "all" "skipped" "0"
else
  for service in ${LOG_AGGREGATION_SERVICES}; do
    raw_file="${work_dir}/compose-${service}.log"

    if compose logs --no-color --no-log-prefix --timestamps --tail "${LOG_AGGREGATION_LINES}" "${service}" > "${raw_file}" 2>&1; then
      append_jsonl "compose" "${service}" "${raw_file}" "${LOG_AGGREGATION_FILE}.tmp" "${collected_at}"
      record_source "compose" "${service}" "succeeded" "$(count_lines "${raw_file}")"
    else
      cat "${raw_file}" >&2
      record_source "compose" "${service}" "failed" "0"
    fi
  done
fi

if [[ "${INCLUDE_SYSTEMD_LOGS}" == "true" ]]; then
  for unit in ${SYSTEMD_LOG_UNITS}; do
    raw_file="${work_dir}/systemd-${unit}.log"

    if journalctl -u "${unit}" --since "${SYSTEMD_LOG_SINCE}" -o short-iso --no-pager > "${raw_file}" 2>&1; then
      append_jsonl "systemd" "${unit}" "${raw_file}" "${LOG_AGGREGATION_FILE}.tmp" "${collected_at}"
      record_source "systemd" "${unit}" "succeeded" "$(count_lines "${raw_file}")"
    else
      cat "${raw_file}" >&2
      record_source "systemd" "${unit}" "failed" "0"
    fi
  done
fi

mv "${LOG_AGGREGATION_FILE}.tmp" "${LOG_AGGREGATION_FILE}"
prune_old_logs

if (( failure_count > 0 )); then
  aggregation_status="failed"
else
  aggregation_status="succeeded"
fi

write_status_file "${aggregation_status}" "${collected_at}"

echo "Operations log aggregation ${aggregation_status}; wrote ${LOG_AGGREGATION_FILE}."

if (( failure_count > 0 )); then
  exit 1
fi

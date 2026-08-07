#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
INGESTION_SERVICE="${INGESTION_SERVICE:-api}"
INGESTION_OUTPUT_DIR="${INGESTION_OUTPUT_DIR:-deploy/ingestion}"
INGESTION_STATUS_FILE="${INGESTION_STATUS_FILE:-${INGESTION_OUTPUT_DIR}/latest_ingestion_refresh.json}"
INGESTION_DATASET_NAME="${INGESTION_DATASET_NAME:-canada_jobs}"
INGESTION_MAX_JOBS="${INGESTION_MAX_JOBS:-72}"
INGESTION_MAX_PER_COMPANY="${INGESTION_MAX_PER_COMPANY:-6}"
INGESTION_MAX_PER_LOCATION="${INGESTION_MAX_PER_LOCATION:-18}"
INGESTION_DELAY_SECONDS="${INGESTION_DELAY_SECONDS:-1}"
CANADA_RAW_OUTPUT_PATH="${CANADA_RAW_OUTPUT_PATH:-/app/data/raw/canada_jobs.csv}"
CANADA_SNAPSHOT_OUTPUT_PATH="${CANADA_SNAPSHOT_OUTPUT_PATH:-/app/data/processed/canada_jobs_snapshot.csv}"

RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_DIR="${INGESTION_OUTPUT_DIR}/${RUN_ID}"
CONTAINER_RUN_DIR="/tmp/joblens-ingestion/${RUN_ID}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
current_stage="preflight"

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 1
  fi
}

require_nonnegative_number() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "${name} must be zero or a positive number." >&2
    exit 1
  fi
}

compose() {
  docker compose --env-file "${DEPLOY_ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

container_exec() {
  compose exec -T "${INGESTION_SERVICE}" "$@"
}

write_status() {
  local status="$1"
  local stage="$2"
  local exit_code="$3"
  local finished_at

  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "${INGESTION_STATUS_FILE}")"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${status}"
    printf '  "stage": "%s",\n' "${stage}"
    printf '  "started_at": "%s",\n' "${STARTED_AT}"
    printf '  "finished_at": "%s",\n' "${finished_at}"
    printf '  "run_id": "%s",\n' "${RUN_ID}"
    printf '  "run_dir": "%s",\n' "${RUN_DIR}"
    printf '  "dataset_name": "%s",\n' "${INGESTION_DATASET_NAME}"
    printf '  "max_jobs": %s,\n' "${INGESTION_MAX_JOBS}"
    printf '  "exit_code": %s\n' "${exit_code}"
    printf '}\n'
  } > "${INGESTION_STATUS_FILE}.tmp"

  mv "${INGESTION_STATUS_FILE}.tmp" "${INGESTION_STATUS_FILE}"
}

copy_artifacts() {
  local artifact

  mkdir -p "${RUN_DIR}"

  for artifact in \
    canada-fetch-summary.json \
    canada-fetch-summary.md \
    canada-snapshot-summary.json \
    canada-snapshot-summary.md \
    canada-validation-summary.md; do
    compose cp "${INGESTION_SERVICE}:${CONTAINER_RUN_DIR}/${artifact}" \
      "${RUN_DIR}/${artifact}" >/dev/null 2>&1 || true
  done
}

on_exit() {
  local exit_code=$?

  if [[ "${exit_code}" -ne 0 ]]; then
    copy_artifacts
    write_status "failed" "${current_stage}" "${exit_code}"
  fi

  exit "${exit_code}"
}

trap on_exit EXIT

require_positive_integer INGESTION_MAX_JOBS "${INGESTION_MAX_JOBS}"
require_positive_integer INGESTION_MAX_PER_COMPANY "${INGESTION_MAX_PER_COMPANY}"
require_positive_integer INGESTION_MAX_PER_LOCATION "${INGESTION_MAX_PER_LOCATION}"
require_nonnegative_number INGESTION_DELAY_SECONDS "${INGESTION_DELAY_SECONDS}"

if [[ ! -f "${DEPLOY_ENV_FILE}" ]]; then
  echo "Production env file is missing: ${DEPLOY_ENV_FILE}" >&2
  exit 1
fi

mkdir -p "${RUN_DIR}"

running_services="$(compose ps --status running --services)"
for service in "${INGESTION_SERVICE}" db; do
  if ! grep -Fxq "${service}" <<< "${running_services}"; then
    echo "Compose service is not running: ${service}" >&2
    exit 1
  fi
done

current_stage="prepare"
container_exec mkdir -p "${CONTAINER_RUN_DIR}" /app/data/raw /app/data/processed

current_stage="fetch"
container_exec python scripts/fetch_canada_jobs.py \
  --output-path "${CANADA_RAW_OUTPUT_PATH}" \
  --summary-path "${CONTAINER_RUN_DIR}/canada-fetch-summary.json" \
  --summary-markdown-path "${CONTAINER_RUN_DIR}/canada-fetch-summary.md" \
  --save-run-to-db \
  --dataset-name "${INGESTION_DATASET_NAME}"
copy_artifacts

current_stage="build"
container_exec python scripts/build_canada_jobs_snapshot.py \
  --input-path "${CANADA_RAW_OUTPUT_PATH}" \
  --output-path "${CANADA_SNAPSHOT_OUTPUT_PATH}" \
  --max-jobs "${INGESTION_MAX_JOBS}" \
  --max-per-company "${INGESTION_MAX_PER_COMPANY}" \
  --max-per-location "${INGESTION_MAX_PER_LOCATION}" \
  --delay-seconds "${INGESTION_DELAY_SECONDS}" \
  --summary-path "${CONTAINER_RUN_DIR}/canada-snapshot-summary.json" \
  --summary-markdown-path "${CONTAINER_RUN_DIR}/canada-snapshot-summary.md" \
  --save-run-to-db \
  --dataset-name "${INGESTION_DATASET_NAME}"
copy_artifacts

current_stage="validate"
container_exec python scripts/validate_canada_jobs_snapshot.py \
  --candidate-path "${CANADA_SNAPSHOT_OUTPUT_PATH}" \
  --summary-path "${CONTAINER_RUN_DIR}/canada-validation-summary.md"
copy_artifacts

current_stage="seed"
container_exec python scripts/seed_database.py \
  --processed-jobs-path "${CANADA_SNAPSHOT_OUTPUT_PATH}" \
  --dataset-name "${INGESTION_DATASET_NAME}" \
  --source-type canada_snapshot

current_stage="completed"
write_status "succeeded" "${current_stage}" "0"

trap - EXIT

echo "Ingestion refresh completed; status written to ${INGESTION_STATUS_FILE}."

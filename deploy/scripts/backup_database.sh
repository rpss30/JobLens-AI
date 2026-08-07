#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-deploy/backups}"
BACKUP_LABEL="${BACKUP_LABEL:-joblens}"
BACKUP_TIMESTAMP="${BACKUP_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
BACKUP_COMPRESS_LEVEL="${BACKUP_COMPRESS_LEVEL:-6}"
BACKUP_STATUS_FILE="${BACKUP_STATUS_FILE:-${BACKUP_DIR}/latest_backup.json}"

require_positive_integer() {
  local name="$1"
  local value="$2"

  if ! [[ "${value}" =~ ^[1-9][0-9]*$ ]]; then
    echo "${name} must be a positive integer." >&2
    exit 1
  fi
}

require_compress_level() {
  if ! [[ "${BACKUP_COMPRESS_LEVEL}" =~ ^[0-9]$ ]]; then
    echo "BACKUP_COMPRESS_LEVEL must be a single digit from 0 through 9." >&2
    exit 1
  fi
}

compose() {
  docker compose --env-file "${DEPLOY_ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

checksum_file() {
  local file_path="$1"

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${file_path}" | awk '{print $1}'
    return
  fi

  shasum -a 256 "${file_path}" | awk '{print $1}'
}

file_size_bytes() {
  wc -c < "$1" | tr -d '[:space:]'
}

write_manifest() {
  local status="$1"
  local backup_file="$2"
  local manifest_file="$3"
  local finished_at
  local size_bytes="0"
  local checksum=""

  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ -f "${backup_file}" ]]; then
    size_bytes="$(file_size_bytes "${backup_file}")"
    checksum="$(checksum_file "${backup_file}")"
  fi

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${status}"
    printf '  "started_at": "%s",\n' "${STARTED_AT}"
    printf '  "finished_at": "%s",\n' "${finished_at}"
    printf '  "backup_file": "%s",\n' "${backup_file}"
    printf '  "size_bytes": %s,\n' "${size_bytes}"
    printf '  "sha256": "%s",\n' "${checksum}"
    printf '  "retention_days": %s,\n' "${BACKUP_RETENTION_DAYS}"
    printf '  "retention_count": %s\n' "${BACKUP_RETENTION_COUNT}"
    printf '}\n'
  } > "${manifest_file}.tmp"

  mv "${manifest_file}.tmp" "${manifest_file}"
  mkdir -p "$(dirname "${BACKUP_STATUS_FILE}")"
  cp "${manifest_file}" "${BACKUP_STATUS_FILE}"
}

prune_old_backups() {
  find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${BACKUP_LABEL}_*.dump" -mtime "+${BACKUP_RETENTION_DAYS}" -print |
    while IFS= read -r stale_backup; do
      rm -f "${stale_backup}" "${stale_backup}.json"
    done

  find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${BACKUP_LABEL}_*.dump" -print |
    sort -r |
    tail -n "+$((BACKUP_RETENTION_COUNT + 1))" |
    while IFS= read -r stale_backup; do
      rm -f "${stale_backup}" "${stale_backup}.json"
    done
}

require_positive_integer BACKUP_RETENTION_DAYS "${BACKUP_RETENTION_DAYS}"
require_positive_integer BACKUP_RETENTION_COUNT "${BACKUP_RETENTION_COUNT}"
require_compress_level

mkdir -p "${BACKUP_DIR}"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
backup_file="${BACKUP_DIR}/${BACKUP_LABEL}_${BACKUP_TIMESTAMP}.dump"
manifest_file="${backup_file}.json"
temporary_backup="${backup_file}.tmp"

cleanup_failed_backup() {
  local exit_code=$?

  if [[ "${exit_code}" -ne 0 ]]; then
    rm -f "${temporary_backup}"
    write_manifest "failed" "${backup_file}" "${manifest_file}"
  fi

  exit "${exit_code}"
}

trap cleanup_failed_backup EXIT

compose exec -T db sh -c \
  "pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --format=custom --compress=${BACKUP_COMPRESS_LEVEL} --no-owner --no-privileges" \
  > "${temporary_backup}"

mv "${temporary_backup}" "${backup_file}"
write_manifest "succeeded" "${backup_file}" "${manifest_file}"
prune_old_backups

trap - EXIT

echo "Database backup written to ${backup_file}."
echo "Backup status written to ${BACKUP_STATUS_FILE}."

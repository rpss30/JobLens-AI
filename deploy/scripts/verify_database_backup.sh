#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_FILE="${BACKUP_FILE:-}"
RESTORE_VERIFY_DATABASE="${RESTORE_VERIFY_DATABASE:-joblens_restore_check_$(date -u +%Y%m%dT%H%M%SZ)}"
KEEP_RESTORE_CHECK_DATABASE="${KEEP_RESTORE_CHECK_DATABASE:-false}"

require_backup_file() {
  if [[ -z "${BACKUP_FILE}" ]]; then
    echo "Set BACKUP_FILE to the dump file that should be verified." >&2
    exit 1
  fi

  if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "Backup file does not exist: ${BACKUP_FILE}" >&2
    exit 1
  fi
}

compose() {
  docker compose --env-file "${DEPLOY_ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

cleanup_verify_database() {
  local exit_code=$?

  if [[ "${KEEP_RESTORE_CHECK_DATABASE}" != "true" ]]; then
    compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh "${RESTORE_VERIFY_DATABASE}" >/dev/null 2>&1 || true
  fi

  exit "${exit_code}"
}

require_backup_file
trap cleanup_verify_database EXIT

compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh "${RESTORE_VERIFY_DATABASE}" >/dev/null
compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "${RESTORE_VERIFY_DATABASE}"

compose exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$1" --no-owner --no-privileges --exit-on-error' \
  sh "${RESTORE_VERIFY_DATABASE}" < "${BACKUP_FILE}"

compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -c "select count(*) from information_schema.tables;"' \
  sh "${RESTORE_VERIFY_DATABASE}" >/dev/null

echo "Backup restore verification passed for ${BACKUP_FILE}."

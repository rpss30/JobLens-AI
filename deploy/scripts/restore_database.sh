#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_FILE="${BACKUP_FILE:-}"
CONFIRM_RESTORE="${CONFIRM_RESTORE:-no}"
DRY_RUN="${DRY_RUN:-yes}"
SKIP_RESTORE_VERIFY="${SKIP_RESTORE_VERIFY:-false}"
STOP_APP_SERVICES="${STOP_APP_SERVICES:-true}"
SKIP_PUBLIC_HEALTH_CHECK="${SKIP_PUBLIC_HEALTH_CHECK:-false}"

require_backup_file() {
  if [[ -z "${BACKUP_FILE}" ]]; then
    echo "Set BACKUP_FILE to the dump file that should be restored." >&2
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

print_restore_plan() {
  echo "Database restore plan"
  echo "- backup file: ${BACKUP_FILE}"
  echo "- compose file: ${COMPOSE_FILE}"
  echo "- env file: ${DEPLOY_ENV_FILE}"
  echo "- dry run: ${DRY_RUN}"
  echo "- verify first: $([[ "${SKIP_RESTORE_VERIFY}" == "true" ]] && echo "no" || echo "yes")"
  echo "- stop app services: ${STOP_APP_SERVICES}"
}

require_backup_file
print_restore_plan

if [[ "${DRY_RUN}" != "no" ]]; then
  echo "Dry run only. Set DRY_RUN=no and CONFIRM_RESTORE=yes to apply."
  exit 0
fi

if [[ "${CONFIRM_RESTORE}" != "yes" ]]; then
  echo "Refusing to restore without CONFIRM_RESTORE=yes." >&2
  exit 1
fi

if [[ "${SKIP_RESTORE_VERIFY}" != "true" ]]; then
  BACKUP_FILE="${BACKUP_FILE}" DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE}" COMPOSE_FILE="${COMPOSE_FILE}" \
    "$(dirname "${BASH_SOURCE[0]}")/verify_database_backup.sh"
fi

if [[ "${STOP_APP_SERVICES}" == "true" ]]; then
  compose stop dashboard api django-ops
fi

compose exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --exit-on-error' \
  < "${BACKUP_FILE}"

compose up -d

if [[ "${SKIP_PUBLIC_HEALTH_CHECK}" != "true" ]]; then
  if [[ -n "${JOBLENS_HEALTH_BASE_URL:-}" || -n "${JOBLENS_DOMAIN:-}" ]]; then
    "$(dirname "${BASH_SOURCE[0]}")/check_production_health.sh"
  else
    echo "Skipping public health checks; set JOBLENS_DOMAIN or JOBLENS_HEALTH_BASE_URL to enable them."
  fi
fi

echo "Database restore completed from ${BACKUP_FILE}."

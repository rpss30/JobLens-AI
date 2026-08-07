#!/usr/bin/env bash
set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:-}"
DEPLOY_USER="${DEPLOY_USER:-}"
DEPLOY_PATH="${DEPLOY_PATH:-}"
DEPLOY_ROLLBACK_REF="${DEPLOY_ROLLBACK_REF:-}"
DEPLOY_SSH_PORT="${DEPLOY_SSH_PORT:-22}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.production}"
DEPLOY_SSH_KEY_PATH="${DEPLOY_SSH_KEY_PATH:-}"
SKIP_PUBLIC_HEALTH_CHECK="${SKIP_PUBLIC_HEALTH_CHECK:-false}"

require_env() {
  local name="$1"
  local value="$2"

  if [[ -z "${value}" ]]; then
    echo "Required environment variable is missing: ${name}" >&2
    exit 1
  fi
}

shell_quote() {
  printf "%q" "$1"
}

ssh_command() {
  local remote="${DEPLOY_USER}@${DEPLOY_HOST}"
  local ssh_args=(-p "${DEPLOY_SSH_PORT}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

  if [[ -n "${DEPLOY_SSH_KEY_PATH}" ]]; then
    ssh_args+=(-i "${DEPLOY_SSH_KEY_PATH}")
  fi

  ssh "${ssh_args[@]}" "${remote}" "$@"
}

require_env DEPLOY_HOST "${DEPLOY_HOST}"
require_env DEPLOY_USER "${DEPLOY_USER}"
require_env DEPLOY_PATH "${DEPLOY_PATH}"

remote_env=(
  "DEPLOY_PATH=$(shell_quote "${DEPLOY_PATH}")"
  "DEPLOY_ROLLBACK_REF=$(shell_quote "${DEPLOY_ROLLBACK_REF}")"
  "DEPLOY_ENV_FILE=$(shell_quote "${DEPLOY_ENV_FILE}")"
)

ssh_command "${remote_env[*]} bash -s" <<'REMOTE_ROLLBACK'
set -euo pipefail

cd "${DEPLOY_PATH}"

rollback_ref="${DEPLOY_ROLLBACK_REF}"

if [[ -z "${rollback_ref}" ]]; then
  if [[ ! -f .deploy/previous_revision ]]; then
    echo "No rollback ref supplied and .deploy/previous_revision is missing." >&2
    exit 1
  fi

  rollback_ref="$(cat .deploy/previous_revision)"
fi

git fetch --prune origin
git checkout --force "${rollback_ref}"

docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml config -q
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml build
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml up -d
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml ps

echo "Rolled back application code to ${rollback_ref}."
echo "Database migrations were not downgraded automatically."
REMOTE_ROLLBACK

if [[ "${SKIP_PUBLIC_HEALTH_CHECK}" != "true" ]]; then
  if [[ -n "${JOBLENS_HEALTH_BASE_URL:-}" || -n "${JOBLENS_DOMAIN:-}" ]]; then
    "$(dirname "${BASH_SOURCE[0]}")/check_production_health.sh"
  else
    echo "Skipping public health checks; set JOBLENS_DOMAIN or JOBLENS_HEALTH_BASE_URL to enable them."
  fi
fi

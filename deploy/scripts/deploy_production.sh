#!/usr/bin/env bash
set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:-}"
DEPLOY_USER="${DEPLOY_USER:-}"
DEPLOY_PATH="${DEPLOY_PATH:-}"
DEPLOY_REF="${DEPLOY_REF:-origin/main}"
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
  "DEPLOY_REF=$(shell_quote "${DEPLOY_REF}")"
  "DEPLOY_ENV_FILE=$(shell_quote "${DEPLOY_ENV_FILE}")"
)

remote_log="$(mktemp)"
trap 'rm -f "${remote_log}"' EXIT

ssh_command "${remote_env[*]} bash -s" <<'REMOTE_DEPLOY' | tee "${remote_log}"
set -euo pipefail

cd "${DEPLOY_PATH}"
mkdir -p .deploy

previous_revision="$(git rev-parse HEAD)"
printf '%s\n' "${previous_revision}" > .deploy/previous_revision

git fetch --prune origin
git checkout --force "${DEPLOY_REF}"

docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml config -q
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml build
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml up -d db

# This script reaches the server as standard input to "bash -s", so the shell is
# still reading the remaining lines from stdin while it runs. "compose run"
# attaches the container to stdin by default, which makes it swallow the rest of
# this script: the deploy would then stop silently after the first migration and
# still exit 0. "-T" and "< /dev/null" keep stdin with the shell that needs it.
# Any command added below that might read stdin needs the same treatment.
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml run --rm -T api alembic upgrade head < /dev/null
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml run --rm -T django-ops python -m django_ops.manage migrate < /dev/null
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml run --rm -T django-ops python -m django_ops.manage bootstrap_ops_roles < /dev/null

docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml up -d
docker compose --env-file "${DEPLOY_ENV_FILE}" -f docker-compose.prod.yml ps

# Every deploy leaves the previous image generation dangling and adds to the
# build cache, which fills the disk over time on a small server. Prune after the
# stack is up, and never fail the deploy over cleanup: dangling images are
# untagged, so nothing a running container depends on can be removed here.
docker image prune -f || true
docker builder prune -f --filter until=168h || true
docker system df

echo "REMOTE_DEPLOY_COMPLETE"
REMOTE_DEPLOY

# A remote block that ends early still exits 0, which once let a deploy report
# success while the stack was never restarted. The health checks cannot catch
# that, because the old containers are still up and healthy. Require the marker
# the remote block prints as its last line.
if ! grep -q '^REMOTE_DEPLOY_COMPLETE$' "${remote_log}"; then
  echo "Remote deploy ended before completing; treating this as a failed deploy." >&2
  exit 1
fi

if [[ "${SKIP_PUBLIC_HEALTH_CHECK}" != "true" ]]; then
  if [[ -n "${JOBLENS_HEALTH_BASE_URL:-}" || -n "${JOBLENS_DOMAIN:-}" ]]; then
    "$(dirname "${BASH_SOURCE[0]}")/check_production_health.sh"
  else
    echo "Skipping public health checks; set JOBLENS_DOMAIN or JOBLENS_HEALTH_BASE_URL to enable them."
  fi
fi

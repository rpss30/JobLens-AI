#!/usr/bin/env bash
set -euo pipefail

JOBLENS_HEALTH_BASE_URL="${JOBLENS_HEALTH_BASE_URL:-}"
JOBLENS_DOMAIN="${JOBLENS_DOMAIN:-}"
HEALTH_RETRIES="${HEALTH_RETRIES:-10}"
HEALTH_DELAY_SECONDS="${HEALTH_DELAY_SECONDS:-6}"

if [[ -z "${JOBLENS_HEALTH_BASE_URL}" ]]; then
  if [[ -z "${JOBLENS_DOMAIN}" ]]; then
    echo "Set JOBLENS_HEALTH_BASE_URL or JOBLENS_DOMAIN." >&2
    exit 1
  fi

  JOBLENS_HEALTH_BASE_URL="https://${JOBLENS_DOMAIN}"
fi

JOBLENS_HEALTH_BASE_URL="${JOBLENS_HEALTH_BASE_URL%/}"

check_url() {
  local path="$1"
  local url="${JOBLENS_HEALTH_BASE_URL}${path}"

  curl --fail --show-error --silent --max-time 10 "${url}" >/dev/null
}

for attempt in $(seq 1 "${HEALTH_RETRIES}"); do
  if check_url "/healthz" \
      && check_url "/api/health" \
      && check_url "/ops/login/"; then
    echo "Production health checks passed for ${JOBLENS_HEALTH_BASE_URL}."
    exit 0
  fi

  if [[ "${attempt}" == "${HEALTH_RETRIES}" ]]; then
    break
  fi

  sleep "${HEALTH_DELAY_SECONDS}"
done

echo "Production health checks failed for ${JOBLENS_HEALTH_BASE_URL}." >&2
exit 1

#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.production}"
AUDIT_STATUS_FILE="${AUDIT_STATUS_FILE:-deploy/secret-audits/latest_secret_audit.json}"
ALLOW_TRACKED_ENV_FILE="${ALLOW_TRACKED_ENV_FILE:-false}"
ALLOW_PUBLIC_ENV_FILE="${ALLOW_PUBLIC_ENV_FILE:-false}"

required_keys=(
  POSTGRES_PASSWORD
  DATABASE_URL
  JOBLENS_DOMAIN
  CADDY_ACME_EMAIL
  JOBLENS_CORS_ORIGINS
  DJANGO_SECRET_KEY
  DJANGO_ALLOWED_HOSTS
  DJANGO_CSRF_TRUSTED_ORIGINS
)

optional_secret_keys=(
  GROQ_API_KEY
  GEMINI_API_KEY
)

failures=()
warnings=()

add_failure() {
  failures+=("$1")
}

add_warning() {
  warnings+=("$1")
}

file_mode() {
  local file_path="$1"

  if stat -c %a "${file_path}" >/dev/null 2>&1; then
    stat -c %a "${file_path}"
    return
  fi

  stat -f %Lp "${file_path}"
}

env_value() {
  local key="$1"
  local line

  line="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n 1 || true)"

  if [[ -z "${line}" ]]; then
    return 1
  fi

  printf '%s\n' "${line#*=}"
}

has_key() {
  local key="$1"

  grep -Eq "^${key}=" "${ENV_FILE}"
}

value_looks_placeholder() {
  local value="$1"

  [[ -z "${value}" ]] && return 0
  [[ "${value}" == *"replace-with"* ]] && return 0
  [[ "${value}" == *"example.com"* ]] && return 0
  [[ "${value}" == *"changeme"* ]] && return 0
  [[ "${value}" == *"placeholder"* ]] && return 0
  [[ "${value}" == *"localhost"* ]] && return 0
  [[ "${value}" == *"127.0.0.1"* ]] && return 0

  return 1
}

json_array() {
  local values=("$@")
  local index

  printf '['

  for index in "${!values[@]}"; do
    printf '"%s"' "${values[${index}]}"

    if (( index < ${#values[@]} - 1 )); then
      printf ', '
    fi
  done

  printf ']'
}

write_status_file() {
  local status="$1"
  local checked_at
  local status_dir

  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status_dir="$(dirname "${AUDIT_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${status}"
    printf '  "checked_at": "%s",\n' "${checked_at}"
    printf '  "env_file": "%s",\n' "${ENV_FILE}"
    printf '  "failures": '
    if (( ${#failures[@]} == 0 )); then
      printf '[]'
    else
      json_array "${failures[@]}"
    fi
    printf ',\n'
    printf '  "warnings": '
    if (( ${#warnings[@]} == 0 )); then
      printf '[]'
    else
      json_array "${warnings[@]}"
    fi
    printf '\n'
    printf '}\n'
  } > "${AUDIT_STATUS_FILE}.tmp"

  mv "${AUDIT_STATUS_FILE}.tmp" "${AUDIT_STATUS_FILE}"
}

if [[ ! -f "${ENV_FILE}" ]]; then
  add_failure "env file is missing"
  write_status_file "failed"
  echo "Secret configuration audit failed; ${ENV_FILE} is missing." >&2
  exit 1
fi

if git ls-files --error-unmatch "${ENV_FILE}" >/dev/null 2>&1; then
  if [[ "${ALLOW_TRACKED_ENV_FILE}" != "true" ]]; then
    add_failure "env file is tracked by Git"
  fi
fi

mode="$(file_mode "${ENV_FILE}")"
mode_value=$((8#${mode}))

if (( (mode_value & 077) != 0 )); then
  if [[ "${ALLOW_PUBLIC_ENV_FILE}" != "true" ]]; then
    add_failure "env file permissions allow group or other access"
  fi
fi

for key in "${required_keys[@]}"; do
  if ! has_key "${key}"; then
    add_failure "${key} is missing"
    continue
  fi

  value="$(env_value "${key}")"

  if value_looks_placeholder "${value}"; then
    add_failure "${key} is empty or still uses a placeholder value"
  fi
done

for key in "${optional_secret_keys[@]}"; do
  if ! has_key "${key}" || [[ -z "$(env_value "${key}")" ]]; then
    add_warning "${key} is not configured"
  fi
done

if (( ${#failures[@]} > 0 )); then
  write_status_file "failed"
  echo "Secret configuration audit failed; see ${AUDIT_STATUS_FILE} for key names only." >&2
  exit 1
fi

write_status_file "succeeded"
echo "Secret configuration audit passed for ${ENV_FILE}; no secret values were printed."

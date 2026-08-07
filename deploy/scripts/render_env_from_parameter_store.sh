#!/usr/bin/env bash
set -euo pipefail

PARAMETER_STORE_PATH="${PARAMETER_STORE_PATH:-/joblens/production}"
ENV_TEMPLATE="${ENV_TEMPLATE:-.env.production.example}"
ENV_FILE="${ENV_FILE:-.env.production}"
PARAMETER_STORE_STATUS_FILE="${PARAMETER_STORE_STATUS_FILE:-deploy/secret-audits/latest_parameter_store_env.json}"
PARAMETER_STORE_AUDIT_STATUS_FILE="${PARAMETER_STORE_AUDIT_STATUS_FILE:-deploy/secret-audits/latest_parameter_store_secret_audit.json}"
PARAMETER_STORE_OVERWRITE="${PARAMETER_STORE_OVERWRITE:-false}"
PARAMETER_STORE_DRY_RUN="${PARAMETER_STORE_DRY_RUN:-false}"
RUN_SECRET_AUDIT="${RUN_SECRET_AUDIT:-true}"
AWS_CLI="${AWS_CLI:-aws}"
AWS_REGION="${AWS_REGION:-}"

if [[ "${PARAMETER_STORE_PATH}" != /* ]]; then
  echo "PARAMETER_STORE_PATH must be an absolute Parameter Store path." >&2
  exit 1
fi

if [[ ! -f "${ENV_TEMPLATE}" ]]; then
  echo "Environment template is missing: ${ENV_TEMPLATE}" >&2
  exit 1
fi

if [[ -f "${ENV_FILE}" && "${PARAMETER_STORE_OVERWRITE}" != "true" && "${PARAMETER_STORE_DRY_RUN}" != "true" ]]; then
  echo "Refusing to overwrite ${ENV_FILE}; set PARAMETER_STORE_OVERWRITE=true." >&2
  exit 1
fi

env_dir="$(dirname "${ENV_FILE}")"
status_dir="$(dirname "${PARAMETER_STORE_STATUS_FILE}")"
mkdir -p "${env_dir}" "${status_dir}"

parameters_json="$(mktemp)"
rendered_env=""
render_status_tmp="$(mktemp "${PARAMETER_STORE_STATUS_FILE}.tmp.XXXXXX")"

cleanup() {
  rm -f "${parameters_json}"

  if [[ -n "${rendered_env}" ]]; then
    rm -f "${rendered_env}"
  fi

  rm -f "${render_status_tmp}"
}

trap cleanup EXIT

aws_args=(
  ssm
  get-parameters-by-path
  --path "${PARAMETER_STORE_PATH}"
  --with-decryption
  --recursive
  --output json
)

if [[ -n "${AWS_REGION}" ]]; then
  aws_args+=(--region "${AWS_REGION}")
fi

"${AWS_CLI}" "${aws_args[@]}" > "${parameters_json}"

if [[ "${PARAMETER_STORE_DRY_RUN}" != "true" ]]; then
  rendered_env="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
  chmod 600 "${rendered_env}"
fi

python - "${parameters_json}" "${ENV_TEMPLATE}" "${rendered_env}" "${render_status_tmp}" <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

parameters_path = Path(sys.argv[1])
template_path = Path(sys.argv[2])
env_output_path = Path(sys.argv[3]) if sys.argv[3] else None
status_output_path = Path(sys.argv[4])

parameter_store_path = os.environ["PARAMETER_STORE_PATH"].rstrip("/")
env_file = os.environ["ENV_FILE"]
dry_run = os.environ["PARAMETER_STORE_DRY_RUN"] == "true"

defaultable_keys = {
    "COMPOSE_PROJECT_NAME",
    "JOBLENS_IMAGE_TAG",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "JOBLENS_API_ROOT_PATH",
    "JOBLENS_RATE_LIMIT_ENABLED",
    "JOBLENS_ANALYZE_RATE_LIMIT",
    "JOBLENS_RATE_LIMIT_WINDOW_SECONDS",
    "GROQ_MODEL",
    "DJANGO_SESSION_COOKIE_SECURE",
    "DJANGO_CSRF_COOKIE_SECURE",
    "DJANGO_SECURE_SSL_REDIRECT",
    "DJANGO_SESSION_COOKIE_AGE",
    "API_WORKERS",
    "DJANGO_WORKERS",
}

blank_optional_keys = {
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
}

key_pattern = re.compile(r"^([A-Z0-9_]+)=(.*)$")


def write_status(status: str, **extra: object) -> None:
    payload = {
        "status": status,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "parameter_store_path": parameter_store_path,
        "env_file": env_file,
        **extra,
    }
    status_output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def env_line(key: str, value: str) -> str:
    if "\n" in value or "\r" in value or "\0" in value:
        raise ValueError(f"{key} contains a newline or null byte")
    return f"{key}={value}"


aws_payload = json.loads(parameters_path.read_text(encoding="utf-8"))
parameters: dict[str, str] = {}
duplicates: list[str] = []

for parameter in aws_payload.get("Parameters", []):
    name = str(parameter.get("Name", ""))
    if not name.startswith(f"{parameter_store_path}/"):
        continue

    key = name.rsplit("/", 1)[-1]
    if key in parameters:
        duplicates.append(key)
        continue

    parameters[key] = str(parameter.get("Value", ""))

rendered_lines: list[str] = []
rendered_keys: list[str] = []
defaulted_keys: list[str] = []
blank_keys: list[str] = []
template_keys: list[str] = []
missing_keys: list[str] = []

for raw_line in template_path.read_text(encoding="utf-8").splitlines():
    match = key_pattern.match(raw_line)

    if not match:
        rendered_lines.append(raw_line)
        continue

    key, template_value = match.groups()
    template_keys.append(key)

    if key in parameters:
        rendered_lines.append(env_line(key, parameters[key]))
        rendered_keys.append(key)
    elif key in blank_optional_keys and template_value == "":
        rendered_lines.append(f"{key}=")
        blank_keys.append(key)
    elif key in defaultable_keys:
        rendered_lines.append(raw_line)
        defaulted_keys.append(key)
    else:
        rendered_lines.append(raw_line)
        missing_keys.append(key)

unused_parameter_keys = sorted(set(parameters) - set(template_keys))

if duplicates or missing_keys:
    write_status(
        "failed",
        rendered_keys=sorted(rendered_keys),
        defaulted_keys=sorted(defaulted_keys),
        blank_keys=sorted(blank_keys),
        missing_keys=sorted(missing_keys),
        duplicate_keys=sorted(duplicates),
        unused_parameter_keys=unused_parameter_keys,
        dry_run=dry_run,
    )
    sys.exit(1)

if env_output_path is not None:
    env_output_path.write_text("\n".join(rendered_lines) + "\n", encoding="utf-8")

write_status(
    "dry_run" if dry_run else "succeeded",
    rendered_keys=sorted(rendered_keys),
    defaulted_keys=sorted(defaulted_keys),
    blank_keys=sorted(blank_keys),
    missing_keys=[],
    duplicate_keys=[],
    unused_parameter_keys=unused_parameter_keys,
    dry_run=dry_run,
)
PY

mv "${render_status_tmp}" "${PARAMETER_STORE_STATUS_FILE}"

if [[ "${PARAMETER_STORE_DRY_RUN}" == "true" ]]; then
  echo "Parameter Store env render dry run succeeded for ${PARAMETER_STORE_PATH}; no secret values were printed."
  exit 0
fi

mv "${rendered_env}" "${ENV_FILE}"
rendered_env=""
chmod 600 "${ENV_FILE}"

if [[ "${RUN_SECRET_AUDIT}" == "true" ]]; then
  ENV_FILE="${ENV_FILE}" \
  AUDIT_STATUS_FILE="${PARAMETER_STORE_AUDIT_STATUS_FILE}" \
    "$(dirname "${BASH_SOURCE[0]}")/audit_secret_configuration.sh"
fi

echo "Rendered ${ENV_FILE} from Parameter Store path ${PARAMETER_STORE_PATH}; no secret values were printed."

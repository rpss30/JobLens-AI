#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.production}"
PROVIDER_KEYS_TO_ROTATE="${PROVIDER_KEYS_TO_ROTATE:-GROQ_API_KEY GEMINI_API_KEY}"
PROVIDER_KEY_ROTATION_DRY_RUN="${PROVIDER_KEY_ROTATION_DRY_RUN:-true}"
CONFIRM_PROVIDER_KEY_ROTATION="${CONFIRM_PROVIDER_KEY_ROTATION:-no}"
PROVIDER_KEY_ROTATION_TIMESTAMP="${PROVIDER_KEY_ROTATION_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
PROVIDER_KEY_ROTATION_BACKUP_DIR="${PROVIDER_KEY_ROTATION_BACKUP_DIR:-deploy/secret-audits/provider-key-rotation-backups}"
PROVIDER_KEY_ROTATION_STATUS_FILE="${PROVIDER_KEY_ROTATION_STATUS_FILE:-deploy/secret-audits/latest_provider_key_rotation.json}"
PROVIDER_KEY_ROTATION_AUDIT_STATUS_FILE="${PROVIDER_KEY_ROTATION_AUDIT_STATUS_FILE:-deploy/secret-audits/latest_provider_key_rotation_audit.json}"
RUN_SECRET_AUDIT="${RUN_SECRET_AUDIT:-true}"
ALLOW_PUBLIC_ENV_FILE="${ALLOW_PUBLIC_ENV_FILE:-false}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "${PYTHON_BIN} is required for provider key rotation." >&2
  exit 2
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  status_dir="$(dirname "${PROVIDER_KEY_ROTATION_STATUS_FILE}")"
  mkdir -p "${status_dir}"
  {
    printf '{\n'
    printf '  "status": "failed",\n'
    printf '  "env_file": "%s",\n' "${ENV_FILE}"
    printf '  "failure": "env file is missing"\n'
    printf '}\n'
  } > "${PROVIDER_KEY_ROTATION_STATUS_FILE}"
  echo "Provider key rotation failed; ${ENV_FILE} is missing." >&2
  exit 1
fi

if [[ "${PROVIDER_KEY_ROTATION_DRY_RUN}" != "true" && "${CONFIRM_PROVIDER_KEY_ROTATION}" != "yes" ]]; then
  status_dir="$(dirname "${PROVIDER_KEY_ROTATION_STATUS_FILE}")"
  mkdir -p "${status_dir}"
  {
    printf '{\n'
    printf '  "status": "failed",\n'
    printf '  "env_file": "%s",\n' "${ENV_FILE}"
    printf '  "failure": "confirmation is required"\n'
    printf '}\n'
  } > "${PROVIDER_KEY_ROTATION_STATUS_FILE}"
  echo "Refusing to rotate provider keys without CONFIRM_PROVIDER_KEY_ROTATION=yes." >&2
  exit 1
fi

env_dir="$(dirname "${ENV_FILE}")"
status_dir="$(dirname "${PROVIDER_KEY_ROTATION_STATUS_FILE}")"
backup_file="${PROVIDER_KEY_ROTATION_BACKUP_DIR}/$(basename "${ENV_FILE}").${PROVIDER_KEY_ROTATION_TIMESTAMP}.bak"
tmp_env=""
mkdir -p "${env_dir}" "${status_dir}" "${PROVIDER_KEY_ROTATION_BACKUP_DIR}"

if [[ "${PROVIDER_KEY_ROTATION_DRY_RUN}" != "true" ]]; then
  tmp_env="$(mktemp "${env_dir}/.provider-key-rotation.XXXXXX")"
  chmod 600 "${tmp_env}"
fi

status_tmp="$(mktemp "${PROVIDER_KEY_ROTATION_STATUS_FILE}.tmp.XXXXXX")"

cleanup() {
  if [[ -n "${tmp_env}" ]]; then
    rm -f "${tmp_env}"
  fi

  rm -f "${status_tmp}"
}

trap cleanup EXIT

rotation_exit=0

PROVIDER_KEYS_TO_ROTATE="${PROVIDER_KEYS_TO_ROTATE}" \
PROVIDER_KEY_ROTATION_DRY_RUN="${PROVIDER_KEY_ROTATION_DRY_RUN}" \
PROVIDER_KEY_ROTATION_TIMESTAMP="${PROVIDER_KEY_ROTATION_TIMESTAMP}" \
  "${PYTHON_BIN}" - "${ENV_FILE}" "${tmp_env}" "${status_tmp}" "${backup_file}" <<'PY' || rotation_exit=$?
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

env_path = Path(sys.argv[1])
output_path = Path(sys.argv[2]) if sys.argv[2] else None
status_path = Path(sys.argv[3])
backup_path = Path(sys.argv[4])

keys_to_rotate = os.environ["PROVIDER_KEYS_TO_ROTATE"].split()
dry_run = os.environ["PROVIDER_KEY_ROTATION_DRY_RUN"] == "true"
rotation_timestamp = os.environ["PROVIDER_KEY_ROTATION_TIMESTAMP"]

line_pattern = re.compile(r"^([A-Z0-9_]+)=(.*)$")
raw_lines = env_path.read_text(encoding="utf-8").splitlines()
values: dict[str, str] = {}

for raw_line in raw_lines:
    match = line_pattern.match(raw_line)
    if match:
        values[match.group(1)] = match.group(2)

rotated_keys: list[str] = []
missing_staged_keys: list[str] = []
unchanged_keys: list[str] = []
invalid_values: list[str] = []

for key in keys_to_rotate:
    next_key = f"{key}_NEXT"
    next_value = values.get(next_key, "")

    if not next_value:
        missing_staged_keys.append(next_key)
        continue

    if any(character in next_value for character in "\n\r\0"):
        invalid_values.append(next_key)
        continue

    if values.get(key, "") == next_value:
        unchanged_keys.append(key)
        continue

    rotated_keys.append(key)


def write_status(status: str, **extra: object) -> None:
    payload = {
        "status": status,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "env_file": str(env_path),
        "dry_run": dry_run,
        "rotation_timestamp": rotation_timestamp,
        "keys_requested": sorted(keys_to_rotate),
        "rotated_keys": sorted(rotated_keys),
        "missing_staged_keys": sorted(missing_staged_keys),
        "unchanged_keys": sorted(unchanged_keys),
        "invalid_values": sorted(invalid_values),
        "backup_file": "" if dry_run else str(backup_path),
        "secret_values_printed": False,
        **extra,
    }
    status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if invalid_values:
    write_status("failed", failure="staged key contains an invalid character")
    sys.exit(1)

if not rotated_keys:
    write_status("failed", failure="no staged provider keys were available to promote")
    sys.exit(1)

if dry_run:
    write_status("dry_run")
    sys.exit(0)

new_lines: list[str] = []
seen_keys: set[str] = set()

for raw_line in raw_lines:
    match = line_pattern.match(raw_line)

    if not match:
        new_lines.append(raw_line)
        continue

    key = match.group(1)
    seen_keys.add(key)

    if key in rotated_keys:
        new_lines.append(f"{key}={values[f'{key}_NEXT']}")
    elif key in {f"{rotated_key}_NEXT" for rotated_key in rotated_keys}:
        new_lines.append(f"{key}=")
    else:
        new_lines.append(raw_line)

for key in rotated_keys:
    next_key = f"{key}_NEXT"

    if key not in seen_keys:
        new_lines.append(f"{key}={values[next_key]}")

    if next_key not in seen_keys:
        new_lines.append(f"{next_key}=")

backup_path.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(env_path, backup_path)
backup_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

assert output_path is not None
output_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
write_status("succeeded")
PY

mv "${status_tmp}" "${PROVIDER_KEY_ROTATION_STATUS_FILE}"

if [[ "${rotation_exit}" -ne 0 ]]; then
  exit "${rotation_exit}"
fi

if [[ "${PROVIDER_KEY_ROTATION_DRY_RUN}" == "true" ]]; then
  echo "Provider key rotation dry run succeeded for ${ENV_FILE}; no secret values were printed."
  exit 0
fi

mv "${tmp_env}" "${ENV_FILE}"
tmp_env=""
chmod 600 "${ENV_FILE}"

if [[ "${RUN_SECRET_AUDIT}" == "true" ]]; then
  ENV_FILE="${ENV_FILE}" \
  AUDIT_STATUS_FILE="${PROVIDER_KEY_ROTATION_AUDIT_STATUS_FILE}" \
  ALLOW_PUBLIC_ENV_FILE="${ALLOW_PUBLIC_ENV_FILE}" \
    "$(dirname "${BASH_SOURCE[0]}")/audit_secret_configuration.sh"
fi

echo "Promoted staged provider keys in ${ENV_FILE}; no secret values were printed."

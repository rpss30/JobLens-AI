#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-deploy/backups}"
BACKUP_STATUS_FILE="${BACKUP_STATUS_FILE:-${BACKUP_DIR}/latest_backup.json}"
OFFSITE_BACKUP_URI="${OFFSITE_BACKUP_URI:-}"
OFFSITE_BACKUP_PROVIDER="${OFFSITE_BACKUP_PROVIDER:-s3}"
OFFSITE_BACKUP_STATUS_FILE="${OFFSITE_BACKUP_STATUS_FILE:-${BACKUP_DIR}/latest_offsite_backup.json}"
OFFSITE_BACKUP_DRY_RUN="${OFFSITE_BACKUP_DRY_RUN:-true}"
AWS_CLI="${AWS_CLI:-aws}"
AWS_S3_SSE="${AWS_S3_SSE:-AES256}"
AWS_S3_STORAGE_CLASS="${AWS_S3_STORAGE_CLASS:-STANDARD}"

require_s3_uri() {
  if [[ -z "${OFFSITE_BACKUP_URI}" ]]; then
    echo "OFFSITE_BACKUP_URI is required, for example s3://existing-bucket/joblens/backups." >&2
    exit 1
  fi

  if [[ "${OFFSITE_BACKUP_URI}" != s3://* ]]; then
    echo "OFFSITE_BACKUP_URI must start with s3://." >&2
    exit 1
  fi
}

json_string_value() {
  local key="$1"
  local file_path="$2"

  sed -n "s/.*\"${key}\": \"\\([^\"]*\\)\".*/\\1/p" "${file_path}" | head -n 1
}

s3_copy() {
  local source_path="$1"
  local destination_uri="$2"
  local command=("${AWS_CLI}" s3 cp "${source_path}" "${destination_uri}" "--only-show-errors")

  if [[ -n "${AWS_S3_SSE}" ]]; then
    command+=("--sse" "${AWS_S3_SSE}")
  fi

  if [[ -n "${AWS_S3_STORAGE_CLASS}" ]]; then
    command+=("--storage-class" "${AWS_S3_STORAGE_CLASS}")
  fi

  if [[ "${OFFSITE_BACKUP_DRY_RUN}" == "true" ]]; then
    printf 'dry run:'
    printf ' %q' "${command[@]}"
    printf '\n'
    return
  fi

  "${command[@]}"
}

write_offsite_status() {
  local status="$1"
  local finished_at
  local status_dir

  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status_dir="$(dirname "${OFFSITE_BACKUP_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${status}"
    printf '  "provider": "%s",\n' "${OFFSITE_BACKUP_PROVIDER}"
    printf '  "started_at": "%s",\n' "${STARTED_AT}"
    printf '  "finished_at": "%s",\n' "${finished_at}"
    printf '  "backup_file": "%s",\n' "${backup_file}"
    printf '  "backup_uri": "%s",\n' "${remote_backup_uri}"
    printf '  "manifest_uri": "%s",\n' "${remote_manifest_uri}"
    printf '  "status_uri": "%s",\n' "${remote_status_uri}"
    printf '  "dry_run": %s\n' "${dry_run_json}"
    printf '}\n'
  } > "${OFFSITE_BACKUP_STATUS_FILE}.tmp"

  mv "${OFFSITE_BACKUP_STATUS_FILE}.tmp" "${OFFSITE_BACKUP_STATUS_FILE}"
}

require_s3_uri

if [[ "${OFFSITE_BACKUP_PROVIDER}" != "s3" ]]; then
  echo "Unsupported OFFSITE_BACKUP_PROVIDER: ${OFFSITE_BACKUP_PROVIDER}" >&2
  exit 1
fi

if [[ ! -f "${BACKUP_STATUS_FILE}" ]]; then
  echo "Backup status file is missing: ${BACKUP_STATUS_FILE}" >&2
  exit 1
fi

if ! grep -q '"status": "succeeded"' "${BACKUP_STATUS_FILE}"; then
  echo "Refusing off-server upload because the latest local backup did not succeed." >&2
  exit 1
fi

backup_file="$(json_string_value "backup_file" "${BACKUP_STATUS_FILE}")"

if [[ -z "${backup_file}" || ! -f "${backup_file}" ]]; then
  echo "Backup file from ${BACKUP_STATUS_FILE} is missing: ${backup_file}" >&2
  exit 1
fi

manifest_file="${backup_file}.json"

if [[ ! -f "${manifest_file}" ]]; then
  echo "Backup manifest is missing: ${manifest_file}" >&2
  exit 1
fi

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
remote_base_uri="${OFFSITE_BACKUP_URI%/}"
remote_backup_uri="${remote_base_uri}/$(basename "${backup_file}")"
remote_manifest_uri="${remote_base_uri}/$(basename "${manifest_file}")"
remote_status_uri="${remote_base_uri}/latest_offsite_backup.json"
dry_run_json="false"

if [[ "${OFFSITE_BACKUP_DRY_RUN}" == "true" ]]; then
  dry_run_json="true"
fi

cleanup_failed_upload() {
  local exit_code=$?

  if [[ "${exit_code}" -ne 0 ]]; then
    write_offsite_status "failed"
  fi

  exit "${exit_code}"
}

trap cleanup_failed_upload EXIT

s3_copy "${backup_file}" "${remote_backup_uri}"
s3_copy "${manifest_file}" "${remote_manifest_uri}"

if [[ "${OFFSITE_BACKUP_DRY_RUN}" == "true" ]]; then
  write_offsite_status "dry_run"
else
  write_offsite_status "succeeded"
  s3_copy "${OFFSITE_BACKUP_STATUS_FILE}" "${remote_status_uri}"
fi

trap - EXIT

echo "Off-server backup status written to ${OFFSITE_BACKUP_STATUS_FILE}."

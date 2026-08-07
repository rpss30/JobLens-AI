#!/usr/bin/env bash
set -euo pipefail

SECURITY_SCAN_REPORT_DIR="${SECURITY_SCAN_REPORT_DIR:-deploy/security-reports}"
SECURITY_SCAN_STATUS_FILE="${SECURITY_SCAN_STATUS_FILE:-${SECURITY_SCAN_REPORT_DIR}/latest_security_scan.json}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-requirements.txt}"
SOURCE_PATHS="${SOURCE_PATHS:-src django_ops scripts deploy}"
RUN_PIP_AUDIT="${RUN_PIP_AUDIT:-true}"
RUN_BANDIT="${RUN_BANDIT:-true}"
RUN_TRIVY_IMAGE_SCAN="${RUN_TRIVY_IMAGE_SCAN:-false}"
BUILD_IMAGE_BEFORE_TRIVY="${BUILD_IMAGE_BEFORE_TRIVY:-false}"
PIP_AUDIT_BIN="${PIP_AUDIT_BIN:-pip-audit}"
BANDIT_BIN="${BANDIT_BIN:-bandit}"
TRIVY_BIN="${TRIVY_BIN:-trivy}"
SECURITY_SCAN_IMAGE_REF="${SECURITY_SCAN_IMAGE_REF:-joblens-security-scan:local}"
TRIVY_SEVERITY="${TRIVY_SEVERITY:-HIGH,CRITICAL}"
TRIVY_IGNORE_UNFIXED="${TRIVY_IGNORE_UNFIXED:-true}"

check_names=()
check_statuses=()
check_exit_codes=()
overall_status="passed"
overall_exit=0

mkdir -p "${SECURITY_SCAN_REPORT_DIR}"

record_check() {
  local name="$1"
  local status="$2"
  local exit_code="$3"

  check_names+=("${name}")
  check_statuses+=("${status}")
  check_exit_codes+=("${exit_code}")

  if [[ "${status}" == "failed" ]]; then
    overall_status="failed"
    overall_exit=1
  fi
}

run_check() {
  local name="$1"
  local exit_code
  shift

  echo "Running security scan: ${name}"

  set +e
  "$@"
  exit_code=$?
  set -e

  if [[ "${exit_code}" -eq 0 ]]; then
    record_check "${name}" "ok" "0"
    return
  fi

  record_check "${name}" "failed" "${exit_code}"
}

write_status_file() {
  local checked_at
  local status_dir

  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status_dir="$(dirname "${SECURITY_SCAN_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${overall_status}"
    printf '  "checked_at": "%s",\n' "${checked_at}"
    printf '  "report_dir": "%s",\n' "${SECURITY_SCAN_REPORT_DIR}"
    printf '  "checks": [\n'

    for index in "${!check_names[@]}"; do
      printf '    {"name": "%s", "status": "%s", "exit_code": %s}' \
        "${check_names[${index}]}" \
        "${check_statuses[${index}]}" \
        "${check_exit_codes[${index}]}"

      if (( index < ${#check_names[@]} - 1 )); then
        printf ','
      fi

      printf '\n'
    done

    printf '  ]\n'
    printf '}\n'
  } > "${SECURITY_SCAN_STATUS_FILE}.tmp"

  mv "${SECURITY_SCAN_STATUS_FILE}.tmp" "${SECURITY_SCAN_STATUS_FILE}"
}

run_pip_audit() {
  local scanner_exit=0

  if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
    echo "Requirements file is missing: ${REQUIREMENTS_FILE}" >&2
    return 1
  fi

  "${PIP_AUDIT_BIN}" \
    -r "${REQUIREMENTS_FILE}" \
    --progress-spinner off \
    --format json \
    --output "${SECURITY_SCAN_REPORT_DIR}/pip-audit.json" || scanner_exit=$?

  return "${scanner_exit}"
}

run_bandit_scan() {
  local source_path_args=()
  local scanner_exit=0

  read -r -a source_path_args <<< "${SOURCE_PATHS}"

  "${BANDIT_BIN}" \
    -q \
    -r "${source_path_args[@]}" \
    -x "*/__pycache__/*,*/venv/*,*/.venv/*" \
    -f json \
    -o "${SECURITY_SCAN_REPORT_DIR}/bandit.json" || scanner_exit=$?

  return "${scanner_exit}"
}

run_trivy_image_scan() {
  local trivy_args=()
  local scanner_exit=0

  if [[ "${BUILD_IMAGE_BEFORE_TRIVY}" == "true" ]]; then
    docker build -t "${SECURITY_SCAN_IMAGE_REF}" . || return $?
  fi

  trivy_args=(
    image
    --exit-code 1
    --severity "${TRIVY_SEVERITY}"
    --format json
    --output "${SECURITY_SCAN_REPORT_DIR}/trivy-image.json"
  )

  if [[ "${TRIVY_IGNORE_UNFIXED}" == "true" ]]; then
    trivy_args+=(--ignore-unfixed)
  fi

  trivy_args+=("${SECURITY_SCAN_IMAGE_REF}")

  "${TRIVY_BIN}" "${trivy_args[@]}" || scanner_exit=$?

  return "${scanner_exit}"
}

if [[ "${RUN_PIP_AUDIT}" == "true" ]]; then
  run_check "pip_audit" run_pip_audit
else
  record_check "pip_audit" "skipped" "0"
fi

if [[ "${RUN_BANDIT}" == "true" ]]; then
  run_check "bandit" run_bandit_scan
else
  record_check "bandit" "skipped" "0"
fi

if [[ "${RUN_TRIVY_IMAGE_SCAN}" == "true" ]]; then
  run_check "trivy_image" run_trivy_image_scan
else
  record_check "trivy_image" "skipped" "0"
fi

write_status_file

echo "Security scans ${overall_status}; wrote ${SECURITY_SCAN_STATUS_FILE}."
exit "${overall_exit}"

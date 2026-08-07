#!/usr/bin/env bash
set -euo pipefail

READINESS_STATUS_FILE="${READINESS_STATUS_FILE:-deploy/readiness/latest_readiness.json}"
STRICT_READINESS="${STRICT_READINESS:-false}"
RUN_COMPOSE_CONFIG="${RUN_COMPOSE_CONFIG:-false}"
RUN_SECRET_AUDIT="${RUN_SECRET_AUDIT:-false}"
RUN_PARAMETER_STORE_RENDER_CHECK="${RUN_PARAMETER_STORE_RENDER_CHECK:-false}"
RUN_BACKUP_STATUS_CHECK="${RUN_BACKUP_STATUS_CHECK:-false}"
RUN_OFFSITE_BACKUP_STATUS_CHECK="${RUN_OFFSITE_BACKUP_STATUS_CHECK:-false}"
RUN_OPERATIONS_STATUS_CHECK="${RUN_OPERATIONS_STATUS_CHECK:-false}"
RUN_TERRAFORM_VALIDATE="${RUN_TERRAFORM_VALIDATE:-false}"
ENV_FILE="${ENV_FILE:-.env.production}"

check_names=()
check_statuses=()
check_messages=()
failure_count=0
warning_count=0

record_check() {
  local name="$1"
  local status="$2"
  local message="$3"

  check_names+=("${name}")
  check_statuses+=("${status}")
  check_messages+=("${message}")

  case "${status}" in
    failed)
      failure_count=$((failure_count + 1))
      ;;
    warning)
      warning_count=$((warning_count + 1))
      ;;
  esac
}

require_file() {
  local path="$1"

  if [[ -f "${path}" ]]; then
    record_check "file:${path}" "ok" "required file exists"
  else
    record_check "file:${path}" "failed" "required file is missing"
  fi
}

require_executable() {
  local path="$1"

  if [[ -x "${path}" ]]; then
    record_check "executable:${path}" "ok" "required script is executable"
  else
    record_check "executable:${path}" "failed" "required script is missing or not executable"
  fi
}

require_ignored() {
  local path="$1"

  if git check-ignore --no-index --quiet "${path}"; then
    record_check "ignored:${path}" "ok" "path is ignored by Git"
  else
    record_check "ignored:${path}" "failed" "path is not ignored by Git"
  fi
}

run_optional_check() {
  local name="$1"
  local enabled="$2"
  shift 2

  if [[ "${enabled}" != "true" ]]; then
    record_check "${name}" "skipped" "optional check disabled"
    return
  fi

  if "$@"; then
    record_check "${name}" "ok" "optional check passed"
  else
    record_check "${name}" "failed" "optional check failed"
  fi
}

check_compose_config() {
  docker compose --env-file .env.production.example -f docker-compose.prod.yml config -q
}

check_secret_audit() {
  ENV_FILE="${ENV_FILE}" AUDIT_STATUS_FILE="${READINESS_STATUS_FILE}.secret-audit.json" \
    deploy/scripts/audit_secret_configuration.sh
}

check_parameter_store_render() {
  PARAMETER_STORE_DRY_RUN=true \
  PARAMETER_STORE_STATUS_FILE="${READINESS_STATUS_FILE}.parameter-store-env.json" \
    deploy/scripts/render_env_from_parameter_store.sh
}

check_backup_status() {
  deploy/scripts/check_database_backup_status.sh
}

check_offsite_backup_status() {
  deploy/scripts/check_offsite_backup_status.sh
}

check_operations_status() {
  deploy/scripts/check_operations_status.sh
}

check_lightsail_terraform_validate() {
  terraform -chdir=deploy/lightsail/terraform init -backend=false -input=false >/dev/null
  terraform -chdir=deploy/lightsail/terraform validate >/dev/null
}

check_forbidden_cloud_provisioning() {
  local combined_text
  local forbidden_commands=(
    "terraform apply"
    "aws lightsail create-instances"
    "aws ecs create-service"
    "aws rds create-db-instance"
    "aws elbv2 create-load-balancer"
    "aws ec2 create-nat-gateway"
    "aws route53 create-hosted-zone"
  )
  local command

  combined_text="$(
    {
      cat .github/workflows/deploy-production.yml
      find deploy/scripts -maxdepth 1 -type f -name "*.sh" ! -name "check_production_readiness.sh" -exec cat {} +
    } 2>/dev/null
  )"

  for command in "${forbidden_commands[@]}"; do
    if grep -Fqi "${command}" <<< "${combined_text}"; then
      record_check "cloud-provisioning:${command}" "failed" "forbidden cloud provisioning command is present"
      return
    fi
  done

  record_check "cloud-provisioning" "ok" "no forbidden cloud provisioning commands found in deployment automation"
}

write_status_file() {
  local status="$1"
  local checked_at
  local status_dir
  local index

  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status_dir="$(dirname "${READINESS_STATUS_FILE}")"
  mkdir -p "${status_dir}"

  {
    printf '{\n'
    printf '  "status": "%s",\n' "${status}"
    printf '  "checked_at": "%s",\n' "${checked_at}"
    printf '  "failure_count": %s,\n' "${failure_count}"
    printf '  "warning_count": %s,\n' "${warning_count}"
    printf '  "checks": [\n'

    for index in "${!check_names[@]}"; do
      printf '    {"name": "%s", "status": "%s", "message": "%s"}' \
        "${check_names[${index}]}" \
        "${check_statuses[${index}]}" \
        "${check_messages[${index}]}"

      if (( index < ${#check_names[@]} - 1 )); then
        printf ','
      fi

      printf '\n'
    done

    printf '  ]\n'
    printf '}\n'
  } > "${READINESS_STATUS_FILE}.tmp"

  mv "${READINESS_STATUS_FILE}.tmp" "${READINESS_STATUS_FILE}"
}

required_files=(
  docker-compose.prod.yml
  .env.production.example
  deploy/caddy/Caddyfile
  .github/workflows/deploy-production.yml
  docs/production-compose.md
  docs/production-deployment.md
  docs/server-hardening.md
  docs/database-backups.md
  docs/operations-monitoring.md
  docs/offsite-backups-alerts.md
  docs/parameter-store-secrets.md
  docs/secret-rotation.md
  docs/security.md
  docs/lightsail-deployment-plan.md
  deploy/lightsail/resource-plan.example.json
  deploy/lightsail/terraform/README.md
  deploy/lightsail/terraform/main.tf
  deploy/lightsail/terraform/outputs.tf
  deploy/lightsail/terraform/terraform.tfvars.example
  deploy/lightsail/terraform/variables.tf
  deploy/lightsail/terraform/versions.tf
  docs/production-ingestion.md
  deploy/server/systemd/joblens-ingestion-refresh.service
  deploy/server/systemd/joblens-ingestion-refresh.timer
)

required_scripts=(
  deploy/scripts/deploy_production.sh
  deploy/scripts/rollback_production.sh
  deploy/scripts/check_production_health.sh
  deploy/scripts/backup_database.sh
  deploy/scripts/verify_database_backup.sh
  deploy/scripts/check_database_backup_status.sh
  deploy/scripts/upload_database_backup.sh
  deploy/scripts/check_offsite_backup_status.sh
  deploy/scripts/send_operations_alert.sh
  deploy/scripts/check_operations_status.sh
  deploy/scripts/check_disk_usage.sh
  deploy/scripts/audit_secret_configuration.sh
  deploy/scripts/render_env_from_parameter_store.sh
  deploy/scripts/run_ingestion_refresh.sh
  deploy/scripts/check_ingestion_refresh_status.sh
)

for path in "${required_files[@]}"; do
  require_file "${path}"
done

for path in "${required_scripts[@]}"; do
  require_executable "${path}"
done

require_ignored ".env.production"
require_ignored "deploy/backups/example.dump"
require_ignored "deploy/ingestion/latest_ingestion_refresh.json"
require_ignored "deploy/logs/example.log"
require_ignored "deploy/monitoring/latest_status.json"
require_ignored "deploy/readiness/latest_readiness.json"
require_ignored "deploy/secret-audits/latest_secret_audit.json"
require_ignored "deploy/lightsail/production-inventory.json"
require_ignored "deploy/lightsail/deployment-evidence/example.json"
require_ignored "deploy/lightsail/terraform/.terraform/example"
require_ignored "deploy/lightsail/terraform/terraform.tfvars"
require_ignored "deploy/lightsail/terraform/reviewed.tfplan"
require_ignored "deploy/lightsail/terraform/terraform.tfstate"
check_forbidden_cloud_provisioning

if [[ -f "${ENV_FILE}" ]]; then
  record_check "env-file:${ENV_FILE}" "ok" "production env file exists"
else
  record_check "env-file:${ENV_FILE}" "warning" "production env file is not present in this checkout"
fi

run_optional_check "compose-config" "${RUN_COMPOSE_CONFIG}" check_compose_config
run_optional_check "secret-audit" "${RUN_SECRET_AUDIT}" check_secret_audit
run_optional_check "parameter-store-render" "${RUN_PARAMETER_STORE_RENDER_CHECK}" check_parameter_store_render
run_optional_check "backup-status" "${RUN_BACKUP_STATUS_CHECK}" check_backup_status
run_optional_check "offsite-backup-status" "${RUN_OFFSITE_BACKUP_STATUS_CHECK}" check_offsite_backup_status
run_optional_check "operations-status" "${RUN_OPERATIONS_STATUS_CHECK}" check_operations_status
run_optional_check "lightsail-terraform-validate" "${RUN_TERRAFORM_VALIDATE}" check_lightsail_terraform_validate

if (( failure_count > 0 )); then
  readiness_status="failed"
elif (( warning_count > 0 )); then
  readiness_status="warning"
else
  readiness_status="passed"
fi

write_status_file "${readiness_status}"

echo "Production readiness ${readiness_status}; wrote ${READINESS_STATUS_FILE}."

if (( failure_count > 0 )); then
  exit 1
fi

if [[ "${STRICT_READINESS}" == "true" && "${readiness_status}" != "passed" ]]; then
  exit 1
fi

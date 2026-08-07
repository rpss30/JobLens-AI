#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-joblens}"
SSH_ALLOWED_CIDR="${SSH_ALLOWED_CIDR:-}"
SSH_PORT="${SSH_PORT:-22}"
CONFIRM_APPLY="${CONFIRM_APPLY:-no}"
DRY_RUN="${DRY_RUN:-yes}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_CONFIG_SOURCE="${SSH_CONFIG_SOURCE:-${SCRIPT_DIR}/sshd_config.d/99-joblens-hardening.conf}"
DOCKER_DAEMON_SOURCE="${DOCKER_DAEMON_SOURCE:-${SCRIPT_DIR}/docker-daemon.example.json}"

log() {
  printf '%s\n' "$*"
}

run_cmd() {
  log "+ $*"

  if [[ "${DRY_RUN}" != "yes" ]]; then
    "$@"
  fi
}

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    log "Run this script with sudo or as root."
    exit 1
  fi
}

require_apply_confirmation() {
  if [[ "${CONFIRM_APPLY}" != "yes" ]]; then
    log "Set CONFIRM_APPLY=yes to apply host changes."
    log "Defaulting to a dry run keeps SSH/firewall changes reviewable."
    exit 1
  fi
}

require_ssh_source() {
  if [[ -z "${SSH_ALLOWED_CIDR}" ]]; then
    log "Set SSH_ALLOWED_CIDR to the trusted source range for SSH."
    log "Example: SSH_ALLOWED_CIDR=203.0.113.10/32"
    exit 1
  fi
}

install_packages() {
  run_cmd apt-get update
  run_cmd apt-get install -y --no-install-recommends ufw unattended-upgrades ca-certificates curl
}

configure_app_user() {
  if id -u "${APP_USER}" >/dev/null 2>&1; then
    log "User ${APP_USER} already exists."
  else
    run_cmd adduser --disabled-password --gecos "" "${APP_USER}"
  fi

  if getent group docker >/dev/null 2>&1; then
    run_cmd usermod -aG docker "${APP_USER}"
  else
    log "Docker group not found; install Docker before adding ${APP_USER} to it."
  fi
}

configure_firewall() {
  run_cmd ufw --force reset
  run_cmd ufw default deny incoming
  run_cmd ufw default allow outgoing
  run_cmd ufw allow 80/tcp
  run_cmd ufw allow 443/tcp
  run_cmd ufw allow from "${SSH_ALLOWED_CIDR}" to any port "${SSH_PORT}" proto tcp
  run_cmd ufw --force enable
  run_cmd ufw status verbose
}

configure_ssh() {
  run_cmd install -d -m 0755 /etc/ssh/sshd_config.d
  run_cmd install -m 0644 "${SSH_CONFIG_SOURCE}" /etc/ssh/sshd_config.d/99-joblens-hardening.conf
  run_cmd sshd -t
  run_cmd systemctl reload ssh
}

configure_docker_logging() {
  run_cmd install -d -m 0755 /etc/docker

  if [[ ! -f /etc/docker/daemon.json ]]; then
    run_cmd install -m 0644 "${DOCKER_DAEMON_SOURCE}" /etc/docker/daemon.json
    run_cmd systemctl restart docker
  else
    log "/etc/docker/daemon.json already exists; merge deploy/server/docker-daemon.example.json manually."
  fi
}

configure_unattended_upgrades() {
  run_cmd systemctl enable unattended-upgrades
  run_cmd systemctl restart unattended-upgrades
}

main() {
  if [[ "${DRY_RUN}" != "yes" ]]; then
    require_root
    require_apply_confirmation
  fi

  require_ssh_source

  log "Host hardening plan"
  log "- app user: ${APP_USER}"
  log "- SSH source: ${SSH_ALLOWED_CIDR}"
  log "- SSH port: ${SSH_PORT}"
  log "- dry run: ${DRY_RUN}"

  install_packages
  configure_app_user
  configure_firewall
  configure_ssh
  configure_docker_logging
  configure_unattended_upgrades

  log "Host hardening steps completed."
}

main "$@"

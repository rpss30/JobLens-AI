from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
HARDEN_SCRIPT = ROOT_DIR / "deploy" / "server" / "harden_host.sh"
SSH_CONFIG = ROOT_DIR / "deploy" / "server" / "sshd_config.d" / "99-joblens-hardening.conf"
DOCKER_DAEMON = ROOT_DIR / "deploy" / "server" / "docker-daemon.example.json"
HARDENING_DOC = ROOT_DIR / "docs" / "server-hardening.md"


def test_host_hardening_script_is_apply_gated_and_executable():
    script_text = HARDEN_SCRIPT.read_text()
    mode = HARDEN_SCRIPT.stat().st_mode

    assert mode & stat.S_IXUSR
    assert "CONFIRM_APPLY" in script_text
    assert "DRY_RUN" in script_text
    assert "require_apply_confirmation" in script_text
    assert "SSH_ALLOWED_CIDR" in script_text
    assert "ufw allow from \"${SSH_ALLOWED_CIDR}\"" in script_text
    assert "ufw allow 80/tcp" in script_text
    assert "ufw allow 443/tcp" in script_text
    assert "ufw allow 5432" not in script_text
    assert "sshd -t" in script_text


def test_host_hardening_script_dry_run_does_not_require_root():
    result = subprocess.run(
        [str(HARDEN_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "SSH_ALLOWED_CIDR": "203.0.113.10/32",
        },
        text=True,
    )

    assert "Host hardening plan" in result.stdout
    assert "dry run: yes" in result.stdout
    assert "+ ufw default deny incoming" in result.stdout
    assert "+ ufw allow from 203.0.113.10/32" in result.stdout


def test_ssh_hardening_disables_password_and_root_login():
    ssh_config = SSH_CONFIG.read_text()

    assert "PasswordAuthentication no" in ssh_config
    assert "PermitRootLogin no" in ssh_config
    assert "PubkeyAuthentication yes" in ssh_config
    assert "KbdInteractiveAuthentication no" in ssh_config
    assert "X11Forwarding no" in ssh_config
    assert "MaxAuthTries 3" in ssh_config


def test_docker_daemon_example_configures_log_rotation():
    docker_config = json.loads(DOCKER_DAEMON.read_text())

    assert docker_config["log-driver"] == "json-file"
    assert docker_config["log-opts"] == {
        "max-size": "10m",
        "max-file": "5",
    }
    assert docker_config["live-restore"] is True


def test_server_hardening_runbook_covers_apply_and_recovery_steps():
    runbook = HARDENING_DOC.read_text().lower()

    assert "confirm_apply=yes" in runbook
    assert "ssh_allowed_cidr" in runbook
    assert "dry run" in runbook
    assert "keep the current ssh session open" in runbook
    assert "recovery" in runbook
    assert "provider console" in runbook
    assert "postgresql" not in runbook.partition("allows only:")[2].split("##", 1)[0]

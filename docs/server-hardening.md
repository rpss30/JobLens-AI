# Server Hardening Runbook

This runbook covers host-level hardening for the low-cost single-server
production path. It does not create cloud resources, change DNS, deploy new
application releases, or start the application stack.

Use it after the server exists, Docker is installed, and you have confirmed SSH
key access.

## Files

```text
deploy/server/harden_host.sh
deploy/server/sshd_config.d/99-joblens-hardening.conf
deploy/server/docker-daemon.example.json
```

The hardening script defaults to dry-run mode and refuses to apply changes
unless `CONFIRM_APPLY=yes` is set. It also requires `SSH_ALLOWED_CIDR` so SSH is
not opened broadly by accident.

## What It Configures

- installs `ufw`, `unattended-upgrades`, `ca-certificates`, and `curl`
- creates a deployment user when `APP_USER` does not already exist
- adds the deployment user to the Docker group when that group exists
- resets UFW and allows only:
  - outbound traffic
  - inbound TCP 80
  - inbound TCP 443
  - inbound SSH from `SSH_ALLOWED_CIDR`
- installs an SSH drop-in that disables password login and root login
- validates SSH configuration with `sshd -t` before reloading SSH
- installs Docker daemon log rotation only when `/etc/docker/daemon.json` does
  not already exist
- enables unattended operating-system security updates

## Preflight Checklist

Before applying:

- keep the current SSH session open
- open a second SSH session and confirm key-based login works
- confirm you know the server provider console or recovery access path
- confirm the provider firewall allows TCP 80 and 443
- restrict provider-firewall SSH access to the same source range when possible
- confirm Docker is installed if the deployment user should be added to the
  Docker group
- decide the trusted SSH source range, such as `203.0.113.10/32`

Do not apply from an unstable network or before key-based SSH is verified.

## Dry Run

Run a dry run first:

```bash
sudo SSH_ALLOWED_CIDR=203.0.113.10/32 deploy/server/harden_host.sh
```

The script prints the commands it would run without changing the host.

## Apply

Apply only after reviewing the dry run:

```bash
sudo SSH_ALLOWED_CIDR=203.0.113.10/32 CONFIRM_APPLY=yes DRY_RUN=no deploy/server/harden_host.sh
```

Optional variables:

```bash
APP_USER=joblens
SSH_PORT=22
```

## Verify

After applying, verify the host from the still-open SSH session:

```bash
sudo ufw status verbose
sudo sshd -t
systemctl status ssh --no-pager
systemctl status unattended-upgrades --no-pager
docker info --format '{{json .LoggingDriver}}'
```

Then open a new SSH session from the allowed source range before closing the
original session.

## Recovery Notes

If SSH access is lost:

- use the provider console or recovery mode
- disable or adjust UFW from the console
- remove or edit `/etc/ssh/sshd_config.d/99-joblens-hardening.conf`
- run `sshd -t` before restarting SSH
- restore provider firewall SSH access only long enough to recover

Keep recovery access procedures documented before applying host changes.

## Current Limits

This runbook does not provision the server, install Docker, configure DNS, or
install the database backup timer. Application deployment is covered separately
in [production-deployment.md](production-deployment.md), and backup operations
are covered in [database-backups.md](database-backups.md).

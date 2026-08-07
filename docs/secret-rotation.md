# Secret Rotation Runbook

This runbook covers production secret handling for the low-cost single-server
JobLens deployment. It documents how to audit, rotate, and replace secrets
without creating cloud resources.

## Files

```text
.env.production.example
deploy/scripts/audit_secret_configuration.sh
docs/secret-rotation.md
```

Production runtime secrets live in the server-side `.env.production` file. That
file must stay outside Git, have private permissions, and be readable only by
the deployment user.

## Secret Inventory

Runtime secrets and sensitive values:

| Value | Stored In | Used By | Rotation Impact |
| --- | --- | --- | --- |
| `POSTGRES_PASSWORD` | `.env.production` | PostgreSQL, `DATABASE_URL` | Requires updating the database role password and restarting app services. |
| `DATABASE_URL` | `.env.production` | FastAPI, Streamlit, Django, Alembic | Must match the current database password. |
| `DJANGO_SECRET_KEY` | `.env.production` | Django operations service | Existing sessions may be invalidated after rotation. |
| `GROQ_API_KEY` | `.env.production` when configured | Skill extraction scripts | Revoke and replace through the provider account. |
| `GEMINI_API_KEY` | `.env.production` when configured | Optional skill extraction | Revoke and replace through the provider account. |

Deployment secrets stored in GitHub Actions encrypted secrets:

| Secret | Purpose |
| --- | --- |
| `PRODUCTION_SSH_KEY` | Private key used by the deployment workflow. |
| `PRODUCTION_SSH_HOST` | Server host or IP for deployment. |
| `PRODUCTION_SSH_USER` | Restricted deployment user. |
| `PRODUCTION_DEPLOY_PATH` | Repository checkout path on the server. |
| `PRODUCTION_DOMAIN` | Public health-check domain. |
| `PRODUCTION_HEALTH_BASE_URL` | Optional explicit health-check base URL. |

`JOBLENS_DOMAIN`, `CADDY_ACME_EMAIL`, `DJANGO_ALLOWED_HOSTS`, and
`DJANGO_CSRF_TRUSTED_ORIGINS` are configuration values rather than passwords,
but incorrect values can break routing, TLS, or operations login.

## Audit Before Rotation

Run the local audit before and after changing runtime secrets:

```bash
ENV_FILE=.env.production \
AUDIT_STATUS_FILE=/srv/joblens-monitoring/latest_secret_audit.json \
deploy/scripts/audit_secret_configuration.sh
```

The audit checks:

- `.env.production` exists
- the env file is not tracked by Git
- group and other permissions are disabled
- required production keys are present
- obvious placeholders such as `replace-with`, `example.com`, `localhost`, and
  empty values are not still present

The audit prints and records key names only; no secret values are written to
stdout, stderr, or the audit status file.

The audit does not validate whether a secret is live at the provider or whether
a GitHub Actions encrypted secret exists. Validate those through the provider
or GitHub UI before a planned rotation.

## Runtime Secret Rotation Order

Use this order for planned runtime secret rotations:

1. Announce a maintenance window if the deployment is public.
2. Run and verify a fresh database backup.
3. Copy the current `.env.production` to a local root-only or deployment-user-only recovery copy outside Git.
4. Generate the replacement secret.
5. Update `.env.production` and keep permissions at `0600`.
6. Apply any provider-side or database-side credential change.
7. Run `audit_secret_configuration.sh`.
8. Restart affected services with Docker Compose.
9. Run `check_operations_status.sh`.
10. Remove any temporary recovery copy after the new secret is verified.

Do not paste production secrets into issue trackers, pull requests, chat logs,
or shell commands that will be saved in history.

## PostgreSQL Password Rotation

Run a backup first:

```bash
BACKUP_DIR=/srv/joblens-backups deploy/scripts/backup_database.sh
BACKUP_FILE=/srv/joblens-backups/<backup-file>.dump deploy/scripts/verify_database_backup.sh
```

Generate a new password on the server:

```bash
python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

Update both `POSTGRES_PASSWORD` and the password portion of `DATABASE_URL` in
`.env.production`.

Then change the database role password inside PostgreSQL. Avoid leaving the
password in shell history; use a secure terminal and clear any temporary shell
variables after use.

Restart the application services:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d db
docker compose --env-file .env.production -f docker-compose.prod.yml up -d dashboard api django-ops
```

Verify:

```bash
deploy/scripts/audit_secret_configuration.sh
deploy/scripts/check_operations_status.sh
```

## Django Secret Key Rotation

Generate a new key:

```bash
python - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
```

Replace `DJANGO_SECRET_KEY` in `.env.production`, then restart Django:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d django-ops
```

Operations users may need to log in again after rotation.

## Provider API Key Rotation

For `GROQ_API_KEY` and `GEMINI_API_KEY`:

1. Create the replacement key in the provider account.
2. Update `.env.production`.
3. Restart only services or scripts that need the provider key.
4. Run the relevant ingestion or extraction workflow in a controlled test.
5. Revoke the old provider key after the replacement is verified.

If the key was exposed, revoke the old key first and accept the temporary
extraction outage while the replacement is installed.

## Deployment SSH Key Rotation

For `PRODUCTION_SSH_KEY`:

1. Generate a new deployment key pair on a trusted workstation.
2. Add the new public key to the deployment user's `authorized_keys` on the server.
3. Update the `PRODUCTION_SSH_KEY` GitHub Actions encrypted secret with the new private key.
4. Run the manual deployment workflow with `skip_public_health_check=true` only if public routing is unavailable.
5. Remove the old public key from `authorized_keys` after the new key is verified.

Keep the deployment user restricted and do not reuse personal SSH keys for
automation.

## Emergency Replacement

If a production secret may be exposed:

1. Revoke the exposed provider key or disable the exposed SSH key immediately.
2. Rotate database and Django secrets if the env file may be exposed.
3. Force operations users to log in again after `DJANGO_SECRET_KEY` rotation.
4. Run the secret audit, operations status check, and a targeted application smoke test.
5. Search repository history and open pull requests for accidental secret commits.
6. Document what was exposed, when rotation completed, and what follow-up is needed.

Do not rely on deleting a file from the latest commit if a real secret reached
Git history. Treat it as exposed and rotate it.

## Current Limits

- no automatic GitHub secret validation
- no provider API key validity check
- no secret manager integration
- no automatic password rotation
- no historical secret scanning beyond local Git checks

A managed secret store can be considered later, but only with cost notes and
explicit approval before any paid resource is created.

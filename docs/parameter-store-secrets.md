# Parameter Store Secrets

This runbook covers rendering the production `.env.production` file from an
existing AWS Systems Manager Parameter Store path. The script reads parameters
only. It does not create parameters, modify parameters, create IAM roles, or
provision cloud resources.

## Files

```text
deploy/scripts/render_env_from_parameter_store.sh
deploy/scripts/audit_secret_configuration.sh
.env.production.example
docs/parameter-store-secrets.md
```

## Parameter Layout

Use one existing path per environment:

```text
/joblens/production/POSTGRES_PASSWORD
/joblens/production/DATABASE_URL
/joblens/production/JOBLENS_DOMAIN
/joblens/production/CADDY_ACME_EMAIL
/joblens/production/JOBLENS_CORS_ORIGINS
/joblens/production/DJANGO_SECRET_KEY
/joblens/production/DJANGO_ALLOWED_HOSTS
/joblens/production/DJANGO_CSRF_TRUSTED_ORIGINS
/joblens/production/GROQ_API_KEY
/joblens/production/GROQ_API_KEY_NEXT
/joblens/production/GEMINI_API_KEY
/joblens/production/GEMINI_API_KEY_NEXT
```

The renderer uses the final path segment as the env key. Values not stored in
Parameter Store can safely come from `.env.production.example` when they are
non-secret defaults such as worker counts, root paths, rate-limit defaults, or
cookie flags. Optional provider keys may remain blank.

## IAM Scope

Use a least-privilege IAM policy for the server or deployment user. It should
allow only read access to the approved parameter path:

```text
ssm:GetParametersByPath
```

with decryption allowed only for the KMS key used by those parameters, if a
customer-managed key is used. Do not grant write actions such as
`ssm:PutParameter` to the runtime env rendering role.

## Dry Run

Run a read-only validation without writing `.env.production`:

```bash
PARAMETER_STORE_PATH=/joblens/production \
PARAMETER_STORE_DRY_RUN=true \
PARAMETER_STORE_STATUS_FILE=/srv/joblens-monitoring/latest_parameter_store_env.json \
deploy/scripts/render_env_from_parameter_store.sh
```

The script calls `aws ssm get-parameters-by-path --with-decryption` and relies
on the AWS CLI's normal pagination behavior.

The dry run writes a key-name only status file:

```text
/srv/joblens-monitoring/latest_parameter_store_env.json
```

It reports rendered, defaulted, blank, missing, duplicate, and unused key names.
No secret values are printed or written to the status file.

## Render Production Env

After the path and permissions have been approved:

```bash
PARAMETER_STORE_PATH=/joblens/production \
PARAMETER_STORE_OVERWRITE=true \
ENV_FILE=.env.production \
PARAMETER_STORE_STATUS_FILE=/srv/joblens-monitoring/latest_parameter_store_env.json \
PARAMETER_STORE_AUDIT_STATUS_FILE=/srv/joblens-monitoring/latest_secret_audit.json \
deploy/scripts/render_env_from_parameter_store.sh
```

The script writes `.env.production` atomically, sets mode `0600`, and then runs
`audit_secret_configuration.sh` by default. Set `RUN_SECRET_AUDIT=false` only
when debugging the renderer in isolation.

Set `AWS_REGION` when the server's default AWS configuration does not already
select the correct region.

## Rotation Workflow

For planned runtime secret rotation:

1. For provider keys, write the replacement into the existing `*_NEXT` parameter.
2. Run `render_env_from_parameter_store.sh` on the server.
3. Run `rotate_provider_keys.sh` in dry-run mode.
4. Promote the staged provider key with `CONFIRM_PROVIDER_KEY_ROTATION=yes`.
5. Confirm `audit_secret_configuration.sh` passes.
6. Restart only the affected Compose services.
7. Run `check_operations_status.sh`.
8. Remove any temporary local recovery copy after the replacement is verified.

Provider-side creation and revocation still happen in the provider account.

## Current Limits

- no parameters, IAM policies, KMS keys, or cloud resources are created
- no GitHub Actions secret validation is performed
- no provider API key validity check is performed
- no provider-side key creation or revocation is performed
- no secret history or version rollback workflow is implemented beyond the
  provider's native Parameter Store version history

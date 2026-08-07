# Security and Privacy

JobLens AI is a portfolio project, not a multi-tenant SaaS product. The current
security posture focuses on practical controls that protect the public demo,
avoid leaking private inputs, and make deployment assumptions explicit.

## Runtime Controls

- FastAPI uses a CORS allowlist instead of allowing all origins.
- Unhandled FastAPI exceptions return a generic `Internal server error.` message.
- Dashboard database failures show safe user-facing messages and write technical
  details to application logs.
- The expensive `/analyze` endpoint has a per-process in-memory rate limiter.
- Pydantic request schemas bound candidate inputs, including 50 current skills,
  20 target roles, 80 characters per list item, 200 characters for search text,
  120 characters for dataset names and locations, and 12,000 characters for
  pasted resume text.
- CSV uploads are limited to `.csv` files, 2 MB, 5,000 rows, and the required
  `title`, `company`, `location`, `description`, and `experience_level` columns.
- The Django operations portal requires an authenticated, active staff user in
  an operations group before showing internal pipeline data.
- Django operations logout is POST-only and protected by CSRF middleware.
- Django operations sessions use HTTP-only cookies with `SameSite=Lax`; secure
  cookies are enabled by default when `DJANGO_DEBUG=false`.
- The production Docker Compose stack keeps PostgreSQL on an internal Docker
  network and publishes no app or database ports directly.
- Caddy is the only public production Compose service. It publishes ports 80 and
  443, redirects HTTP to HTTPS, adds security headers, and routes `/api/*`,
  `/ops/*`, and dashboard traffic to internal services.
- The server hardening runbook restricts host firewall ingress to HTTP, HTTPS,
  and SSH from an explicit trusted source range; disables SSH password and root
  login; and enables Docker log rotation.

## Environment Variables

Use environment variables or a secret manager for runtime configuration. Do not
commit `.env` files.

```env
DATABASE_URL=postgresql+psycopg://localhost:5432/joblens_ai
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
JOBLENS_CORS_ORIGINS=http://localhost:8501,http://localhost:8502,http://127.0.0.1:8501,http://127.0.0.1:8502
JOBLENS_API_ROOT_PATH=
JOBLENS_RATE_LIMIT_ENABLED=true
JOBLENS_ANALYZE_RATE_LIMIT=60
JOBLENS_RATE_LIMIT_WINDOW_SECONDS=60
DJANGO_SECRET_KEY=
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_SESSION_COOKIE_AGE=28800
```

`JOBLENS_CORS_ORIGINS` should be set to the dashboard origins that are allowed
to call the API. In AWS, use the ALB or custom-domain origin instead of local
development URLs.

For the single-server production Compose path, copy
`.env.production.example` to `.env.production`, replace every placeholder
secret, and keep the file readable only by the deployment user.
The `.gitignore` rules ignore `.env.*` files while keeping committed example
templates available.

The production deployment workflow uses GitHub Actions encrypted secrets only
for SSH and routing values such as `PRODUCTION_SSH_HOST`,
`PRODUCTION_SSH_USER`, `PRODUCTION_SSH_KEY`, `PRODUCTION_DEPLOY_PATH`, and
`PRODUCTION_DOMAIN`. Application runtime secrets remain on the server unless a
separately approved secret store is added.

See [server-hardening.md](server-hardening.md) before applying host firewall or
SSH changes. Keep an active SSH session and a recovery-console path available
until a new key-based login has been verified.

See [production-deployment.md](production-deployment.md) for the manual
deployment and rollback workflow. The deployment automation updates an existing
server and creates no cloud resources.

See [database-backups.md](database-backups.md) for local PostgreSQL backup,
restore validation, and gated restore procedures. Backup dumps contain
application data and should be stored outside the repository with permissions
limited to the deployment user.

See [offsite-backups-alerts.md](offsite-backups-alerts.md) before enabling
off-server backup upload or webhook alert delivery. Destination credentials and
webhook URLs should stay in private server-side configuration.

See [operations-monitoring.md](operations-monitoring.md) for local health,
backup freshness, off-server backup checks, disk usage, alert delivery, and log
snapshot checks. Monitoring status files and log snapshots should stay outside
Git and remain readable only by the deployment user.

See [secret-rotation.md](secret-rotation.md) for runtime secret inventory,
`.env.production` auditing, planned rotation order, deployment SSH key
rotation, and emergency replacement steps.

See [parameter-store-secrets.md](parameter-store-secrets.md) for rendering
`.env.production` from an existing Parameter Store path without printing secret
values.

See [security-scanning.md](security-scanning.md) for dependency, static Python,
and container image scans used before production releases.

See [production-readiness.md](production-readiness.md) for the pre-deployment
checklist covering cost guardrails, server prerequisites, secret audit,
database backups, monitoring, and post-deploy verification.

## Resume Privacy

Resume text is analyzed in memory for a single request. The API and dashboard do
not persist raw resume text to PostgreSQL, saved analysis history, generated
reports, or logs. Analysis outputs may contain derived skills, experience areas,
project keywords, matched skills, missing skills, and fit explanations.

Users should avoid pasting highly sensitive personal data into a public demo.
This project currently has no authentication, account isolation, or encrypted
per-user storage.

## Upload Safety

Uploaded datasets are treated as untrusted input. The dashboard validates file
metadata before parsing, rejects non-CSV extensions, rejects empty or oversized
files, parses malformed rows strictly, validates required columns, and rejects
blank required values. Uploaded datasets can be persisted only when PostgreSQL is
available.

## AWS Recommendations

- Store `DATABASE_URL` and optional API keys in AWS Secrets Manager or AWS
  Systems Manager Parameter Store. See
  [parameter-store-secrets.md](parameter-store-secrets.md) for the read-only
  Parameter Store env render workflow.
- Use least-privilege ECS task roles scoped to only the AWS APIs the task
  actually needs.
- Keep RDS in private subnets and allow inbound traffic only from the ECS
  service security group.
- Send application logs to CloudWatch, but do not log request bodies, pasted
  resume text, or uploaded CSV contents.
- Put TLS in front of any public deployment with an ACM certificate and an ALB or
  CloudFront distribution.
- Consider AWS WAF or ALB-level throttling for a public demo with meaningful
  traffic.

## Current Tradeoffs

- The rate limiter is in memory, so limits are per process and reset on restart.
  A distributed limiter backed by Redis or an API gateway would be needed for
  horizontally scaled production traffic.
- The project has no login system. This keeps the portfolio demo easy to try,
  but it means saved public dashboard/API data should be treated as demo data
  unless account-level ownership checks are added. The internal Django
  operations portal now has staff authentication, but it is not yet a complete
  user-account system for the public demo.
- CSV upload checks reduce accidental misuse and oversized inputs, but they are
  not a malware scanner or full data-loss-prevention system.

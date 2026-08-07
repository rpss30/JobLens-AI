# Security Scanning

This runbook covers local and CI security scanning for JobLens. It checks
Python dependencies, Python source patterns, and the production Docker image. It
does not deploy the app, publish images, create cloud resources, or contact live
application services.

## Files

```text
.github/workflows/security-scan.yml
deploy/scripts/run_security_scans.sh
docs/security-scanning.md
```

Generated reports are written under:

```text
deploy/security-reports/
```

That directory is ignored by Git.

## Local Scans

Install scanner tools in your development environment:

```bash
python -m pip install pip-audit bandit
```

Run dependency and static Python scans:

```bash
deploy/scripts/run_security_scans.sh
```

The script writes:

```text
deploy/security-reports/pip-audit.json
deploy/security-reports/bandit.json
deploy/security-reports/latest_security_scan.json
```

It exits nonzero when an enabled scanner fails, finds blocking issues, or is not
installed.

## Container Image Scan

To include the production image scan locally, install Trivy and run:

```bash
BUILD_IMAGE_BEFORE_TRIVY=true \
RUN_TRIVY_IMAGE_SCAN=true \
SECURITY_SCAN_IMAGE_REF=joblens-security-scan:local \
deploy/scripts/run_security_scans.sh
```

The Trivy image scan fails on unfixed `HIGH` and `CRITICAL` findings by default
and writes:

```text
deploy/security-reports/trivy-image.json
```

Tune severity only when there is a written exception with a target follow-up
date:

```bash
TRIVY_SEVERITY=CRITICAL deploy/scripts/run_security_scans.sh
```

## CI Workflow

The `Security Scan` workflow runs on pull requests, pushes to `main`, and manual
dispatches.

It has two jobs:

| Job | Checks |
| --- | --- |
| `python-security` | installs `pip-audit` and `bandit`, then runs `run_security_scans.sh` without the image scan |
| `container-security` | builds the application image locally and scans it with Trivy |

Both jobs upload JSON reports as artifacts. Reports are meant for review and
triage, not for committing to the repository.

## Triage

Dependency finding:

- confirm the affected package is actually installed by `requirements.txt`
- update the direct dependency when possible
- document any transitive dependency exception with the upstream package that
  must release a fix

Static finding:

- inspect the exact file and line in the Bandit report
- fix hardcoded secret, subprocess, shell, file-permission, or unsafe parsing
  issues where applicable
- suppress only after documenting why the finding is a false positive

Container finding:

- rebuild from the current `python:3.12-slim` base image
- update system or Python dependencies when possible
- keep the finding open if the fixed base image is not available yet

## Current Limits

- scanner vulnerability databases are downloaded at scan time
- no SARIF upload to repository security dashboards is configured
- no automatic dependency update pull requests are created
- no image is pushed to a registry by the scan workflow
- no runtime penetration testing is performed by the security scan workflow

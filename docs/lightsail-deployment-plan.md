# Lightsail Deployment Plan

This is a plan-only deployment guide for the low-cost single-server JobLens AI
production path. It creates no cloud resources and must remain planning
documentation until explicit approval is given for a specific resource list and
monthly budget.

Pricing was checked on 2026-08-07 against the official AWS Lightsail pricing
pages. Recheck pricing before provisioning because instance bundles, network
allowances, and snapshot prices can change.

## Files

```text
docs/lightsail-deployment-plan.md
deploy/lightsail/resource-plan.example.json
deploy/lightsail/terraform
```

The example JSON file is safe to commit because every resource is marked as not
created. A real production inventory should be stored privately and must not be
committed.

The Terraform template in `deploy/lightsail/terraform` is also safe to commit
and validate locally. It defines the planned Lightsail resources, but it has no
remote backend, committed state, credentials, or approved apply step.

## Recommended Baseline

Use one Amazon Lightsail Linux/Unix instance with a public IPv4 address:

| Option | Monthly cost | Memory | vCPU | Disk | Transfer | Use |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Small | $12 | 2 GB | 2 | 60 GB SSD | 3 TB | Baseline for the first production demo |
| Medium | $24 | 4 GB | 2 | 80 GB SSD | 4 TB | Fallback if memory pressure appears |

The $12 plan is the smallest defensible target for the current Compose stack
because the server runs Caddy, Streamlit, FastAPI, Django operations, and
PostgreSQL together. The $5 and $7 public IPv4 bundles are useful for tiny apps,
but they leave little memory headroom for this stack and can make PostgreSQL or
Python workers brittle under refreshes, migrations, or repeated demo traffic.

Do not add a managed database, load balancer, NAT gateway, container service, or
object storage bucket in this plan. Those move the project out of the intended
low-cost single-server shape and require separate approval.

## Planned Resources

| Resource | Purpose | Monthly cost | Charging note | Teardown |
| --- | --- | ---: | --- | --- |
| Lightsail Linux/Unix instance | Runs Docker Compose production stack | $12 baseline, $24 fallback | Charges while allocated | Stop and delete the instance after backup |
| Static IPv4 address | Stable DNS target | $0 while attached | $0.005/hour if left unattached for more than one hour | Detach and delete after instance deletion |
| Existing DNS A record | Points subdomain to static IPv4 | $0 in this plan | Uses existing DNS provider or existing zone | Remove or repoint record |
| Local Docker volumes | PostgreSQL and Caddy persistence | Included in instance disk | Lost when the instance is deleted unless backed up | Delete after verified backup |
| Optional manual snapshot | Recovery point before major changes | $0.05/GB-month | Roughly $1/month for 20 GB of used snapshot data | Delete stale snapshots |

Minimum planned monthly cost is $12 before snapshots. A practical first month
with one small manual snapshot should land around $13 to $15, depending on used
snapshot storage. The 4 GB fallback path starts at $24 before snapshots.

## Approval Gate

Before provisioning, record:

- approved monthly budget
- AWS Budget or equivalent billing guardrail
- billing alert thresholds and recipients
- exact AWS account and region
- production domain or subdomain
- chosen bundle size
- whether a manual snapshot is approved
- teardown owner and target teardown date for trial deployments

Do not run these commands or equivalent console actions without explicit
approval:

```text
aws lightsail create-instances
aws lightsail allocate-static-ip
aws lightsail attach-static-ip
aws route53 create-hosted-zone
aws s3 mb
terraform apply
```

## Terraform Template

The optional Terraform template tracks the same bounded resource set as this
plan: one Lightsail instance, one static IPv4 address, an attachment between
them, and instance firewall rules for SSH, HTTP, and HTTPS. It does not create
DNS, RDS, S3, ECS, load balancers, NAT gateways, or external monitoring.

Local validation is allowed before approval:

```bash
terraform -chdir=deploy/lightsail/terraform fmt -check
terraform -chdir=deploy/lightsail/terraform init -backend=false
terraform -chdir=deploy/lightsail/terraform validate
```

`terraform plan` requires explicit approval because it can contact the target
AWS account and produce reviewed resource changes. `terraform apply` requires a
second explicit approval for the exact plan and cost.

## Provisioning Checklist

Use this checklist only after approval:

1. Confirm billing alerts and budget guardrails are active.
2. Create the approved Lightsail Linux/Unix instance in the approved region.
3. Attach one static IPv4 address to the instance.
4. Add or update the existing DNS A record for the production subdomain.
5. Install Docker Engine and Docker Compose on the server.
6. Apply the host hardening steps in `docs/server-hardening.md`.
7. Copy `.env.production` to the server with mode `0600`.
8. Run the secret audit against `.env.production`.
9. Validate `docker-compose.prod.yml` with the production environment file.
10. Create and verify the first local PostgreSQL backup.
11. Install the systemd timer templates for backups and monitoring.
12. Run the production readiness checker in strict mode.
13. Trigger the deployment workflow.
14. Verify dashboard, API, operations login, backups, and status checks.
15. Update the private production inventory with resource identifiers and URLs.

## Teardown Checklist

Before deleting resources, create and verify any backup that must survive the
teardown. Then:

1. Stop public traffic or put up a maintenance notice.
2. Create a final PostgreSQL backup if data must be retained.
3. Stop the Compose stack on the instance.
4. Delete the Lightsail instance.
5. Delete the static IPv4 address so it cannot become an unattached hourly cost.
6. Delete stale manual snapshots.
7. Remove or repoint the DNS A record.
8. Delete any off-server backup bucket only if one was separately approved later.
9. Check the Lightsail console for remaining instances, static IPs, snapshots,
   disks, DNS zones, databases, load balancers, container services, and buckets.
10. Check billing the next day for unexpected continuing charges.

## Evidence To Keep Privately

Keep these outside Git:

- instance name, ARN, region, and public IPv4 address
- DNS record and provider
- snapshot names and retention decision
- deployment user and SSH key fingerprint
- backup location and latest restore verification time
- production URLs
- monthly cost estimate and approval note

Use `deploy/lightsail/resource-plan.example.json` as the template, then store
the filled inventory in a private note or ignored local file.

## Current Limits

- no Lightsail resources are provisioned by this repository work
- no production URL exists for this plan
- no off-server backup storage is included
- no external uptime alerting is included
- no managed secret store is included
- no Terraform state, backend, or apply approval is included

## Sources

- AWS Lightsail pricing: <https://aws.amazon.com/lightsail/pricing/>
- AWS Lightsail instance bundles: <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html>
- AWS Lightsail billing FAQ: <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-frequently-asked-questions-faq-billing-and-account-management.html>

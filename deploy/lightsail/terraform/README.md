# Lightsail Terraform Template

This directory contains a Terraform template for the approved low-cost
single-server Lightsail target described in `docs/lightsail-deployment-plan.md`.
It is intentionally small: one Linux/Unix instance, one attached static IPv4
address, and Lightsail firewall rules for SSH, HTTP, and HTTPS.

The template is safe to validate locally, but it must not be applied until the
approval gate in `docs/lightsail-deployment-plan.md` is complete.

## Local Validation

```bash
terraform -chdir=deploy/lightsail/terraform fmt -check
terraform -chdir=deploy/lightsail/terraform init -backend=false
terraform -chdir=deploy/lightsail/terraform validate
```

`init -backend=false` downloads provider metadata and plugins locally. It does
not create cloud resources.

## Planning After Approval

After budget approval, copy the example variables and replace placeholders:

```bash
cp deploy/lightsail/terraform/terraform.tfvars.example deploy/lightsail/terraform/terraform.tfvars
```

Before planning, verify the current Lightsail blueprint and bundle IDs:

```text
aws lightsail get-blueprints
aws lightsail get-bundles
```

Then run a reviewed plan only:

```bash
terraform -chdir=deploy/lightsail/terraform plan -out=tfplan
```

Do not apply this plan by running `terraform apply` until the user has
explicitly approved the exact resource changes and monthly cost.

## Resources Covered

| Resource | Terraform resource |
| --- | --- |
| Linux/Unix instance | `aws_lightsail_instance.app` |
| Static IPv4 address | `aws_lightsail_static_ip.app` |
| Static IPv4 attachment | `aws_lightsail_static_ip_attachment.app` |
| Instance firewall ports | `aws_lightsail_instance_public_ports.app` |

The template does not create DNS zones, managed databases, load balancers,
object storage buckets, NAT gateways, container services, or external monitors.

## Security Notes

- SSH is limited to `ssh_cidrs`; the example uses documentation-only CIDR
  `203.0.113.10/32`.
- HTTP and HTTPS are public because Caddy owns web ingress.
- PostgreSQL, FastAPI, Django operations, and Next.js ports stay private to
  Docker Compose.
- Required tags are applied through AWS provider `default_tags`.

## Private Files

These files are intentionally ignored:

```text
deploy/lightsail/terraform/terraform.tfvars
deploy/lightsail/terraform/*.tfplan
deploy/lightsail/terraform/*.tfstate
deploy/lightsail/terraform/.terraform/
```

Do not commit real account IDs, public IPs, key pair names, SSH source ranges,
plan files, state files, or deployment evidence.

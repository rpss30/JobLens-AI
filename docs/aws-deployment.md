# AWS Deployment Guide

This guide describes the AWS deployment used for JobLens AI. The repository
includes repeatable shell helpers for the container image, network and database
foundation, database seed task, and ECS service. It is not a replacement for
declarative infrastructure such as Terraform or CloudFormation.

## Deployment status

The deployed architecture is:

```text
GitHub repo
   |
   v
Docker image --> Amazon ECR
   |
   v
Application Load Balancer
   |
   +--> Default routes --> Streamlit :8501
   +--> API paths      --> FastAPI :8000
   |
   v
One Amazon ECS Fargate task
   |
   v
Private Amazon RDS for PostgreSQL
```

One task runs both web processes from the same image. This keeps the portfolio
deployment smaller than two independent services while preserving separate
health checks and routing for the dashboard and API. The current listener uses
HTTP for a temporary demo; a long-lived public deployment should add an ACM
certificate and an HTTPS listener.

## AWS resources

Create these resources in one AWS Region, for example `us-east-1` or
`ca-central-1`:

| Resource | Purpose |
| --- | --- |
| Amazon ECR repository | Stores the JobLens AI Docker image. |
| Amazon RDS for PostgreSQL | Stores saved datasets and analysis runs. |
| ECS cluster and service | Runs one Fargate task with Streamlit and FastAPI. |
| Application Load Balancer | Routes dashboard and API requests to separate container ports. |
| ECS VPC networking | Allows the application task to reach private RDS. |
| Security groups | Restrict application access to the ALB and PostgreSQL access to the task. |
| AWS Secrets Manager | Injects `DATABASE_URL` into the task without storing it in source control. |
| CloudWatch Logs | Captures both application processes in one retained log group. |

## Runtime configuration

The ECS task uses one image and starts both processes with:

```bash
/app/scripts/start_aws_services.sh
```

Required environment variables:

```env
PYTHONPATH=/app
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<rds-endpoint>:5432/joblens_ai
```

Keep `DATABASE_URL` in AWS Secrets Manager or AWS Systems Manager Parameter
Store. The task definition loads the `database_url` JSON key from the
`joblens/database` secret.

Do not set ingestion or LLM API keys unless those optional scripts are being
run in the deployed environment.

## 1. Build and push the image to ECR

Install and configure the AWS CLI, then set local shell variables:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=<your-account-id>
export ECR_REPOSITORY=joblens-ai
export IMAGE_TAG=$(git rev-parse --short HEAD)
export IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
```

Create the ECR repository once:

```bash
aws ecr create-repository \
  --repository-name $ECR_REPOSITORY \
  --region $AWS_REGION
```

Authenticate Docker to ECR:

```bash
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

Build and push the image:

```bash
docker build --platform linux/amd64 -t $ECR_REPOSITORY:$IMAGE_TAG .
docker tag $ECR_REPOSITORY:$IMAGE_TAG $IMAGE_URI
docker push $IMAGE_URI
```

The repository also includes a helper that creates the ECR repository when
needed, builds the Linux AMD64 image, and pushes both the Git commit tag and
`latest`:

```bash
AWS_PROFILE=joblens-deployer \
AWS_REGION=ca-central-1 \
./scripts/publish_aws_image.sh
```

For repeated deployments, tag the same image as `latest` if the AWS service is
configured to track the `latest` tag:

```bash
docker tag $ECR_REPOSITORY:$IMAGE_TAG \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
```

## 2. Create the RDS PostgreSQL database

Create an Amazon RDS PostgreSQL instance:

- Engine: PostgreSQL
- Database name: `joblens_ai`
- Public access: `No` for production-style deployment
- Storage encryption: enabled
- Backups: enabled
- Deletion protection: enabled for long-lived environments, disabled for short demos

Security group setup:

- Create an app service security group, for example `joblens-app-sg`.
- Create an RDS security group, for example `joblens-rds-sg`.
- Allow inbound PostgreSQL traffic on port `5432` to `joblens-rds-sg` only from
  `joblens-app-sg`.

The app only needs the RDS endpoint, database name, username, and password in
the `DATABASE_URL`.

The repository helper provisions the default-VPC security groups, private RDS
instance, ECS cluster, execution role, log groups, and Secrets Manager value:

```bash
AWS_PROFILE=joblens-deployer \
AWS_REGION=ca-central-1 \
./scripts/provision_aws_foundation.sh
```

## 3. Initialize and seed the database

The database tables are created by Alembic migrations:

```bash
alembic upgrade head
```

The sample dataset is seeded by:

```bash
python -m scripts.seed_database
```

The seed command also runs `alembic upgrade head`, which is useful for one-off
Fargate seed tasks. Running migrations explicitly first is still recommended
when you are operating the database manually.

For a private RDS instance, run those commands from a trusted network path that
can reach the database:

- an EC2 bastion or admin instance in the same VPC,
- a one-off ECS task in the same VPC,
- or a temporary local IP allowlist during setup if the database is configured
  for public access, removed immediately after seeding.

Example:

```bash
export DATABASE_URL='postgresql+psycopg://<db_user>:<db_password>@<rds-endpoint>:5432/joblens_ai'
alembic upgrade head
python -m scripts.seed_database
```

Expected result:

```text
Seeded <number> processed jobs into PostgreSQL.
```

For the private RDS instance, run the included one-off Fargate seed task:

```bash
AWS_PROFILE=joblens-deployer \
AWS_REGION=ca-central-1 \
./scripts/seed_aws_database.sh
```

## 4. Deploy the combined ECS Fargate service

Deploy the current image tag:

```bash
AWS_PROFILE=joblens-deployer \
AWS_REGION=ca-central-1 \
IMAGE_TAG=$(git rev-parse --short HEAD) \
./scripts/deploy_aws_service.sh
```

The deployment helper:

- creates an internet-facing ALB and HTTP listener,
- creates dashboard and API target groups,
- routes API paths such as `/health`, `/datasets`, and `/analyze` to port `8000`,
- sends all other paths to Streamlit on port `8501`,
- allows the ALB to reach only the application ports,
- registers an X86_64 Fargate task definition,
- injects the private RDS URL from Secrets Manager,
- deploys one desired task with rollback enabled,
- and waits for the API health check to pass.

The script is safe to rerun for a new image. It reuses the existing networking
and load-balancer resources and creates a new task definition revision.

## 5. Optional managed-service alternatives

Existing AWS accounts with App Runner access can still deploy two services from
the same image, one for Streamlit and one for FastAPI. New accounts can also use
ECS Express Mode. Those options are simpler in the console but generally run
more always-on service and load-balancer capacity than this one-task demo.

## 6. Verify the deployment

The deployment helper prints one ALB base URL. API health check:

```bash
curl http://<load-balancer-url>/health
```

Expected response:

```json
{"status":"ok"}
```

List saved datasets:

```bash
curl http://<load-balancer-url>/datasets
```

Analyze the seeded sample dataset:

```bash
curl -X POST http://<load-balancer-url>/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "sample_jobs",
    "current_skills": ["Python", "SQL", "Pandas"],
    "target_roles": ["Data Scientist"],
    "location": "Any",
    "experience_level": "Entry Level",
    "top_n": 5
  }'
```

Dashboard verification:

1. Open the load balancer base URL.
2. Turn on PostgreSQL mode.
3. Choose `sample_jobs`.
4. Run an analysis.
5. Confirm dataset selection, saved analysis runs, Markdown export, and PDF
   export still work.

## 7. Operational checklist

Before sharing a deployed AWS demo:

- Confirm RDS is not publicly accessible.
- Confirm the application task security group is the only group allowed to reach RDS.
- Store database credentials in Secrets Manager or Parameter Store.
- Keep the RDS instance small for demos.
- Enable CloudWatch logs for both application processes.
- Use a predictable service name and tag resources with `Project=JobLensAI`.
- Set AWS Budgets or billing alerts.
- Document the deployed URLs in a private note, not in the public repo if the
  environment is temporary.

## 8. Teardown checklist

For temporary demos, remove resources in this order:

1. Scale the ECS service to zero, then delete it.
2. Delete the ALB listener, ALB, and both target groups.
3. Delete the RDS instance after taking any snapshot you want to keep.
4. Delete old ECR images or the ECR repository.
5. Delete unused security groups and IAM roles.
6. Confirm CloudWatch log groups are removed or have retention configured.

## References

- AWS App Runner availability change: https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html
- AWS App Runner source image services: https://docs.aws.amazon.com/apprunner/latest/dg/service-source-image.html
- AWS App Runner VPC connectors: https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html
- AWS App Runner image configuration: https://docs.aws.amazon.com/apprunner/latest/api/API_ImageConfiguration.html
- Amazon ECR image lifecycle: https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html
- Amazon RDS for PostgreSQL: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html
- Amazon ECS Express Mode: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html

# AWS Deployment Guide

This guide describes a production-style AWS deployment path for JobLens AI.
It is intended as portfolio documentation, not a fully automated Terraform or
CloudFormation deployment.

## Deployment status

The recommended architecture for the original project roadmap is:

```text
GitHub repo
   |
   v
Docker image
   |
   v
Amazon ECR
   |
   +--> Web service: Streamlit dashboard
   |
   +--> Web service: FastAPI backend
   |
   v
Amazon RDS for PostgreSQL
```

AWS App Runner was the simplest fit for this style of deployment because it can
run a web service directly from a container image in Amazon ECR. However, AWS
now states that App Runner is no longer open to new customers. Existing App
Runner customers can keep using it, but new AWS accounts should use Amazon ECS
Express Mode or ECS on Fargate instead.

Use this guide in one of two ways:

| AWS account status | Recommended path |
| --- | --- |
| Existing account with App Runner access | Use the App Runner + RDS path below. |
| New AWS account without App Runner access | Use the same ECR image and RDS database, but deploy the containers with ECS Express Mode or ECS Fargate. |

The current live demo can remain on Streamlit Cloud. The AWS path is a
resume-ready deployment plan that shows how the same system would run with a
managed container platform and managed PostgreSQL.

## AWS resources

Create these resources in one AWS Region, for example `us-east-1` or
`ca-central-1`:

| Resource | Purpose |
| --- | --- |
| Amazon ECR repository | Stores the JobLens AI Docker image. |
| Amazon RDS for PostgreSQL | Stores saved datasets and analysis runs. |
| App Runner or ECS service: `joblens-dashboard` | Runs Streamlit on port `8501`. |
| App Runner or ECS service: `joblens-api` | Runs FastAPI on port `8000`. |
| VPC connector or ECS VPC networking | Allows the app services to reach private RDS. |
| Security groups | Restrict PostgreSQL access to only the app service security group. |
| CloudWatch Logs | Captures container logs for both web services. |

## Runtime configuration

Use one image for both services. Override the start command per service.

Dashboard service:

```bash
streamlit run src/dashboard/app.py --server.address=0.0.0.0 --server.port=8501
```

API service:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Required environment variables:

```env
PYTHONPATH=/app
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<rds-endpoint>:5432/joblens_ai
```

Keep `DATABASE_URL` in AWS Secrets Manager or AWS Systems Manager Parameter
Store for a real deployment. App Runner supports referencing secrets and
parameters as runtime environment variables. ECS task definitions can also load
secrets into container environment variables.

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

## 3. Initialize and seed the database

The database tables are created by:

```bash
python -m src.database.init_db
```

The sample dataset is seeded by:

```bash
python -m scripts.seed_database
```

For a private RDS instance, run those commands from a trusted network path that
can reach the database:

- an EC2 bastion or admin instance in the same VPC,
- a one-off ECS task in the same VPC,
- or a temporary local IP allowlist during setup if the database is configured
  for public access, removed immediately after seeding.

Example:

```bash
export DATABASE_URL='postgresql+psycopg://<db_user>:<db_password>@<rds-endpoint>:5432/joblens_ai'
python -m src.database.init_db
python -m scripts.seed_database
```

Expected result:

```text
Database tables created successfully.
Seeded <number> processed jobs into PostgreSQL.
```

## 4. Deploy with App Runner, if available

Use this path only if the AWS account already has App Runner access.

Create an App Runner VPC connector:

- Select private subnets in the same VPC as RDS.
- Attach `joblens-app-sg`.
- Point RDS inbound rules at `joblens-app-sg`.

Important networking note: when App Runner uses a VPC connector, outbound
traffic goes through the selected VPC. If the app later needs public internet
or AWS API access from runtime code, add NAT Gateway access or VPC endpoints.
The current dashboard/API runtime primarily needs RDS.

Create the API service:

- Source: container registry
- Provider: Amazon ECR
- Image: `$IMAGE_URI`
- Port: `8000`
- Start command:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

- Environment variables:
  - `PYTHONPATH=/app`
  - `DATABASE_URL=<secret or parameter reference>`
- Health check protocol: HTTP
- Health check path: `/health`
- Outgoing network traffic: custom VPC connector

Create the dashboard service:

- Source: container registry
- Provider: Amazon ECR
- Image: `$IMAGE_URI`
- Port: `8501`
- Start command:

```bash
streamlit run src/dashboard/app.py --server.address=0.0.0.0 --server.port=8501
```

- Environment variables:
  - `PYTHONPATH=/app`
  - `DATABASE_URL=<secret or parameter reference>`
- Health check protocol: TCP
- Outgoing network traffic: custom VPC connector

## 5. ECS Express Mode fallback for new AWS accounts

For new AWS accounts that cannot create App Runner services, use Amazon ECS
Express Mode with the same ECR image and RDS database.

Carry over these settings from the App Runner plan:

| Service | Container port | Command | Health check |
| --- | --- | --- | --- |
| `joblens-dashboard` | `8501` | Streamlit command above | `/` or TCP/load balancer default |
| `joblens-api` | `8000` | Uvicorn command above | `/health` |

ECS Express Mode creates a Fargate-backed ECS service with a load balancer,
TLS, auto scaling, monitoring, and networking defaults. Use private networking
and security groups so the service can connect to RDS without exposing the
database publicly.

If ECS Express Mode does not expose every runtime override needed in the
console, use standard ECS on Fargate with two task definitions or two services
from the same image.

## 6. Verify the deployment

API health check:

```bash
curl https://<api-service-url>/health
```

Expected response:

```json
{"status":"ok"}
```

List saved datasets:

```bash
curl https://<api-service-url>/datasets
```

Analyze the seeded sample dataset:

```bash
curl -X POST https://<api-service-url>/analyze \
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

1. Open the dashboard service URL.
2. Turn on PostgreSQL mode.
3. Choose `sample_jobs`.
4. Run an analysis.
5. Confirm dataset selection, saved analysis runs, Markdown export, and PDF
   export still work.

## 7. Operational checklist

Before sharing a deployed AWS demo:

- Confirm RDS is not publicly accessible.
- Confirm the app service is the only security group allowed to reach RDS.
- Store database credentials in Secrets Manager or Parameter Store.
- Keep the RDS instance small for demos.
- Enable CloudWatch logs for both services.
- Use a predictable service name and tag resources with `Project=JobLensAI`.
- Set AWS Budgets or billing alerts.
- Document the deployed URLs in a private note, not in the public repo if the
  environment is temporary.

## 8. Teardown checklist

For temporary demos, remove resources in this order:

1. Delete the dashboard service.
2. Delete the API service.
3. Delete the App Runner VPC connector or ECS service resources.
4. Delete the RDS instance after taking any snapshot you want to keep.
5. Delete old ECR images or the ECR repository.
6. Delete unused security groups.
7. Confirm CloudWatch log groups are removed or have retention configured.

## References

- AWS App Runner availability change: https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html
- AWS App Runner source image services: https://docs.aws.amazon.com/apprunner/latest/dg/service-source-image.html
- AWS App Runner VPC connectors: https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html
- AWS App Runner image configuration: https://docs.aws.amazon.com/apprunner/latest/api/API_ImageConfiguration.html
- Amazon ECR image lifecycle: https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html
- Amazon RDS for PostgreSQL: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html
- Amazon ECS Express Mode: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html

#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-joblens-deployer}"
AWS_REGION="${AWS_REGION:-ca-central-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws --profile "${AWS_PROFILE}" sts get-caller-identity --query Account --output text)}"
ECS_CLUSTER="${ECS_CLUSTER:-joblens-cluster}"
TASK_FAMILY="${TASK_FAMILY:-joblens-database-seed}"
TASK_EXECUTION_ROLE="${TASK_EXECUTION_ROLE:-joblens-ecs-task-execution-role}"
DB_SECRET_NAME="${DB_SECRET_NAME:-joblens/database}"
IMAGE_URI="${IMAGE_URI:-${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/joblens-ai:latest}"

aws_cli() {
    aws --profile "${AWS_PROFILE}" --region "${AWS_REGION}" "$@"
}

VPC_ID="$(
    aws_cli ec2 describe-vpcs \
        --filters Name=is-default,Values=true \
        --query 'Vpcs[0].VpcId' \
        --output text
)"

APP_SECURITY_GROUP_ID="$(
    aws_cli ec2 describe-security-groups \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=group-name,Values=joblens-app-sg \
        --query 'SecurityGroups[0].GroupId' \
        --output text
)"

SUBNETS_CSV="$(
    aws_cli ec2 describe-subnets \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=default-for-az,Values=true \
        --query 'join(`,`, Subnets[].SubnetId)' \
        --output text
)"

TASK_EXECUTION_ROLE_ARN="$(
    aws_cli iam get-role \
        --role-name "${TASK_EXECUTION_ROLE}" \
        --query 'Role.Arn' \
        --output text
)"

DB_SECRET_ARN="$(
    aws_cli secretsmanager describe-secret \
        --secret-id "${DB_SECRET_NAME}" \
        --query ARN \
        --output text
)"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

cat > "${TMP_DIR}/task-definition.json" <<JSON
{
  "family": "${TASK_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "${TASK_EXECUTION_ROLE_ARN}",
  "runtimePlatform": {
    "cpuArchitecture": "X86_64",
    "operatingSystemFamily": "LINUX"
  },
  "containerDefinitions": [
    {
      "name": "joblens-seed",
      "image": "${IMAGE_URI}",
      "essential": true,
      "command": ["python", "-m", "scripts.seed_database"],
      "environment": [
        {
          "name": "PYTHONPATH",
          "value": "/app"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "${DB_SECRET_ARN}:database_url::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/joblens-seed",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "seed"
        }
      }
    }
  ],
  "tags": [
    {
      "key": "Project",
      "value": "JobLensAI"
    }
  ]
}
JSON

TASK_DEFINITION_ARN="$(
    aws_cli ecs register-task-definition \
        --cli-input-json "file://${TMP_DIR}/task-definition.json" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text
)"

TASK_ARN="$(
    aws_cli ecs run-task \
        --cluster "${ECS_CLUSTER}" \
        --launch-type FARGATE \
        --task-definition "${TASK_DEFINITION_ARN}" \
        --network-configuration \
            "awsvpcConfiguration={subnets=[${SUBNETS_CSV}],securityGroups=[${APP_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
        --tags "key=Project,value=JobLensAI" \
        --query 'tasks[0].taskArn' \
        --output text
)"

if [[ -z "${TASK_ARN}" || "${TASK_ARN}" == "None" ]]; then
    echo "The ECS seed task could not be started." >&2
    exit 1
fi

echo "Waiting for the database seed task to finish..."
aws_cli ecs wait tasks-stopped \
    --cluster "${ECS_CLUSTER}" \
    --tasks "${TASK_ARN}"

TASK_RESULT="$(
    aws_cli ecs describe-tasks \
        --cluster "${ECS_CLUSTER}" \
        --tasks "${TASK_ARN}" \
        --query 'tasks[0].containers[0].[exitCode,reason]' \
        --output text
)"

EXIT_CODE="$(printf '%s\n' "${TASK_RESULT}" | awk '{print $1}')"

if [[ "${EXIT_CODE}" != "0" ]]; then
    echo "Database seed task failed: ${TASK_RESULT}" >&2
    echo "Check CloudWatch log group /ecs/joblens-seed for details." >&2
    exit 1
fi

echo "Database tables and sample dataset were seeded successfully."

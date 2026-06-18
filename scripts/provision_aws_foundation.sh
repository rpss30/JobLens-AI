#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-joblens-deployer}"
AWS_REGION="${AWS_REGION:-ca-central-1}"
PROJECT_TAG="${PROJECT_TAG:-JobLensAI}"
ECS_CLUSTER="${ECS_CLUSTER:-joblens-cluster}"
DB_INSTANCE_IDENTIFIER="${DB_INSTANCE_IDENTIFIER:-joblens-postgres}"
DB_SUBNET_GROUP="${DB_SUBNET_GROUP:-joblens-db-subnet-group}"
DB_SECRET_NAME="${DB_SECRET_NAME:-joblens/database}"
DB_NAME="${DB_NAME:-joblens_ai}"
DB_USERNAME="${DB_USERNAME:-joblens_admin}"
DB_INSTANCE_CLASS="${DB_INSTANCE_CLASS:-db.t4g.micro}"
TASK_EXECUTION_ROLE="${TASK_EXECUTION_ROLE:-joblens-ecs-task-execution-role}"
INFRASTRUCTURE_ROLE="${INFRASTRUCTURE_ROLE:-joblens-ecs-infrastructure-role}"

aws_cli() {
    aws --profile "${AWS_PROFILE}" --region "${AWS_REGION}" "$@"
}

create_role_if_missing() {
    local role_name="$1"
    local trust_policy_file="$2"

    if ! aws_cli iam get-role --role-name "${role_name}" >/dev/null 2>&1; then
        aws_cli iam create-role \
            --role-name "${role_name}" \
            --assume-role-policy-document "file://${trust_policy_file}" \
            --tags "Key=Project,Value=${PROJECT_TAG}" \
            >/dev/null
    fi
}

VPC_ID="$(
    aws_cli ec2 describe-vpcs \
        --filters Name=is-default,Values=true \
        --query 'Vpcs[0].VpcId' \
        --output text
)"

if [[ -z "${VPC_ID}" || "${VPC_ID}" == "None" ]]; then
    echo "No default VPC was found in ${AWS_REGION}." >&2
    exit 1
fi

SUBNET_IDS=()
while IFS= read -r subnet_id; do
    if [[ -n "${subnet_id}" ]]; then
        SUBNET_IDS+=("${subnet_id}")
    fi
done < <(
    aws_cli ec2 describe-subnets \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=default-for-az,Values=true \
        --query 'Subnets[].SubnetId' \
        --output text \
        | tr '\t' '\n'
)

if (( ${#SUBNET_IDS[@]} < 2 )); then
    echo "At least two default subnets are required for RDS." >&2
    exit 1
fi

APP_SECURITY_GROUP_ID="$(
    aws_cli ec2 describe-security-groups \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=group-name,Values=joblens-app-sg \
        --query 'SecurityGroups[0].GroupId' \
        --output text
)"

if [[ -z "${APP_SECURITY_GROUP_ID}" || "${APP_SECURITY_GROUP_ID}" == "None" ]]; then
    APP_SECURITY_GROUP_ID="$(
        aws_cli ec2 create-security-group \
            --group-name joblens-app-sg \
            --description "JobLens ECS application tasks" \
            --vpc-id "${VPC_ID}" \
            --tag-specifications \
                "ResourceType=security-group,Tags=[{Key=Project,Value=${PROJECT_TAG}}]" \
            --query GroupId \
            --output text
    )"
fi

RDS_SECURITY_GROUP_ID="$(
    aws_cli ec2 describe-security-groups \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=group-name,Values=joblens-rds-sg \
        --query 'SecurityGroups[0].GroupId' \
        --output text
)"

if [[ -z "${RDS_SECURITY_GROUP_ID}" || "${RDS_SECURITY_GROUP_ID}" == "None" ]]; then
    RDS_SECURITY_GROUP_ID="$(
        aws_cli ec2 create-security-group \
            --group-name joblens-rds-sg \
            --description "JobLens PostgreSQL access from ECS tasks" \
            --vpc-id "${VPC_ID}" \
            --tag-specifications \
                "ResourceType=security-group,Tags=[{Key=Project,Value=${PROJECT_TAG}}]" \
            --query GroupId \
            --output text
    )"
fi

INGRESS_ERROR_FILE="${TMPDIR:-/tmp}/joblens-rds-ingress-error.txt"
if ! aws_cli ec2 authorize-security-group-ingress \
        --group-id "${RDS_SECURITY_GROUP_ID}" \
        --protocol tcp \
        --port 5432 \
        --source-group "${APP_SECURITY_GROUP_ID}" \
        >/dev/null 2>"${INGRESS_ERROR_FILE}"; then
    if ! grep -q "InvalidPermission.Duplicate" "${INGRESS_ERROR_FILE}"; then
        cat "${INGRESS_ERROR_FILE}" >&2
        exit 1
    fi
fi
rm -f "${INGRESS_ERROR_FILE}"

if ! aws_cli rds describe-db-subnet-groups \
    --db-subnet-group-name "${DB_SUBNET_GROUP}" \
    >/dev/null 2>&1; then
    aws_cli rds create-db-subnet-group \
        --db-subnet-group-name "${DB_SUBNET_GROUP}" \
        --db-subnet-group-description "JobLens PostgreSQL subnet group" \
        --subnet-ids "${SUBNET_IDS[@]}" \
        --tags "Key=Project,Value=${PROJECT_TAG}" \
        >/dev/null
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

cat > "${TMP_DIR}/ecs-task-trust.json" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON

cat > "${TMP_DIR}/ecs-infrastructure-trust.json" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON

create_role_if_missing "${TASK_EXECUTION_ROLE}" "${TMP_DIR}/ecs-task-trust.json"
create_role_if_missing "${INFRASTRUCTURE_ROLE}" "${TMP_DIR}/ecs-infrastructure-trust.json"

aws_cli iam attach-role-policy \
    --role-name "${TASK_EXECUTION_ROLE}" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws_cli iam attach-role-policy \
    --role-name "${INFRASTRUCTURE_ROLE}" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices

if ! aws_cli ecs describe-clusters \
    --clusters "${ECS_CLUSTER}" \
    --query 'clusters[?status==`ACTIVE`]' \
    --output text \
    | grep -q .; then
    aws_cli ecs create-cluster \
        --cluster-name "${ECS_CLUSTER}" \
        --tags "key=Project,value=${PROJECT_TAG}" \
        >/dev/null
fi

for log_group in /ecs/joblens-api /ecs/joblens-dashboard /ecs/joblens-seed; do
    if ! aws_cli logs describe-log-groups \
        --log-group-name-prefix "${log_group}" \
        --query "logGroups[?logGroupName=='${log_group}']" \
        --output text \
        | grep -q .; then
        aws_cli logs create-log-group \
            --log-group-name "${log_group}" \
            --tags "Project=${PROJECT_TAG}"
    fi

    aws_cli logs put-retention-policy \
        --log-group-name "${log_group}" \
        --retention-in-days 14
done

SECRET_ARN="$(
    aws_cli secretsmanager describe-secret \
        --secret-id "${DB_SECRET_NAME}" \
        --query ARN \
        --output text \
        2>/dev/null || true
)"

if [[ -z "${SECRET_ARN}" || "${SECRET_ARN}" == "None" ]]; then
    DB_PASSWORD="$(
        aws_cli secretsmanager get-random-password \
            --password-length 32 \
            --exclude-punctuation \
            --query RandomPassword \
            --output text
    )"

    SECRET_JSON="$(
        DB_USERNAME="${DB_USERNAME}" \
        DB_PASSWORD="${DB_PASSWORD}" \
        python3 -c \
            'import json, os; print(json.dumps({"username": os.environ["DB_USERNAME"], "password": os.environ["DB_PASSWORD"]}))'
    )"

    SECRET_ARN="$(
        aws_cli secretsmanager create-secret \
            --name "${DB_SECRET_NAME}" \
            --description "JobLens PostgreSQL credentials and connection URL" \
            --secret-string "${SECRET_JSON}" \
            --tags "Key=Project,Value=${PROJECT_TAG}" \
            --query ARN \
            --output text
    )"
else
    DB_PASSWORD="$(
        aws_cli secretsmanager get-secret-value \
            --secret-id "${DB_SECRET_NAME}" \
            --query SecretString \
            --output text \
        | python3 -c 'import json, sys; print(json.load(sys.stdin)["password"])'
    )"
fi

cat > "${TMP_DIR}/secret-access-policy.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "${SECRET_ARN}"
    }
  ]
}
JSON

aws_cli iam put-role-policy \
    --role-name "${TASK_EXECUTION_ROLE}" \
    --policy-name JobLensDatabaseSecretAccess \
    --policy-document "file://${TMP_DIR}/secret-access-policy.json"

if ! aws_cli rds describe-db-instances \
    --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}" \
    >/dev/null 2>&1; then
    aws_cli rds create-db-instance \
        --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}" \
        --db-name "${DB_NAME}" \
        --engine postgres \
        --db-instance-class "${DB_INSTANCE_CLASS}" \
        --allocated-storage 20 \
        --storage-type gp3 \
        --storage-encrypted \
        --master-username "${DB_USERNAME}" \
        --master-user-password "${DB_PASSWORD}" \
        --vpc-security-group-ids "${RDS_SECURITY_GROUP_ID}" \
        --db-subnet-group-name "${DB_SUBNET_GROUP}" \
        --backup-retention-period 1 \
        --no-multi-az \
        --no-publicly-accessible \
        --no-deletion-protection \
        --auto-minor-version-upgrade \
        --tags "Key=Project,Value=${PROJECT_TAG}" \
        >/dev/null
fi

echo "Waiting for ${DB_INSTANCE_IDENTIFIER} to become available..."
aws_cli rds wait db-instance-available \
    --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}"

DB_HOST="$(
    aws_cli rds describe-db-instances \
        --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}" \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text
)"

DATABASE_URL="postgresql+psycopg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}"

SECRET_JSON="$(
    DB_USERNAME="${DB_USERNAME}" \
    DB_PASSWORD="${DB_PASSWORD}" \
    DB_HOST="${DB_HOST}" \
    DB_NAME="${DB_NAME}" \
    DATABASE_URL="${DATABASE_URL}" \
    python3 -c \
        'import json, os; print(json.dumps({"username": os.environ["DB_USERNAME"], "password": os.environ["DB_PASSWORD"], "host": os.environ["DB_HOST"], "port": 5432, "dbname": os.environ["DB_NAME"], "database_url": os.environ["DATABASE_URL"]}))'
)"

aws_cli secretsmanager put-secret-value \
    --secret-id "${DB_SECRET_NAME}" \
    --secret-string "${SECRET_JSON}" \
    >/dev/null

echo "AWS foundation is ready."
echo "VPC: ${VPC_ID}"
echo "App security group: ${APP_SECURITY_GROUP_ID}"
echo "RDS security group: ${RDS_SECURITY_GROUP_ID}"
echo "Database endpoint: ${DB_HOST}"
echo "Database secret ARN: ${SECRET_ARN}"
echo "ECS cluster: ${ECS_CLUSTER}"

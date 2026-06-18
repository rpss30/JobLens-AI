#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-joblens-deployer}"
AWS_REGION="${AWS_REGION:-ca-central-1}"
PROJECT_TAG="${PROJECT_TAG:-JobLensAI}"
ECS_CLUSTER="${ECS_CLUSTER:-joblens-cluster}"
ECS_SERVICE="${ECS_SERVICE:-joblens-service}"
TASK_FAMILY="${TASK_FAMILY:-joblens-service}"
TASK_EXECUTION_ROLE="${TASK_EXECUTION_ROLE:-joblens-ecs-task-execution-role}"
DB_SECRET_NAME="${DB_SECRET_NAME:-joblens/database}"
ECR_REPOSITORY="${ECR_REPOSITORY:-joblens-ai}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ALB_NAME="${ALB_NAME:-joblens-alb}"
ALB_SECURITY_GROUP="${ALB_SECURITY_GROUP:-joblens-alb-sg}"
DASHBOARD_TARGET_GROUP="${DASHBOARD_TARGET_GROUP:-joblens-dashboard-tg}"
API_TARGET_GROUP="${API_TARGET_GROUP:-joblens-api-tg}"
APP_SECURITY_GROUP="${APP_SECURITY_GROUP:-joblens-app-sg}"
DESIRED_COUNT="${DESIRED_COUNT:-1}"

aws_cli() {
    aws --profile "${AWS_PROFILE}" --region "${AWS_REGION}" "$@"
}

authorize_ingress() {
    local group_id="$1"
    local protocol="$2"
    local port="$3"
    local source_flag="$4"
    local source_value="$5"
    local error_file="$6"

    if ! aws_cli ec2 authorize-security-group-ingress \
            --group-id "${group_id}" \
            --protocol "${protocol}" \
            --port "${port}" \
            "${source_flag}" "${source_value}" \
            >/dev/null 2>"${error_file}"; then
        if ! grep -q "InvalidPermission.Duplicate" "${error_file}"; then
            cat "${error_file}" >&2
            exit 1
        fi
    fi
}

create_target_group() {
    local target_group_name="$1"
    local port="$2"
    local health_check_path="$3"
    local target_group_arn=""

    target_group_arn="$(
        aws_cli elbv2 describe-target-groups \
            --names "${target_group_name}" \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text \
            2>/dev/null || true
    )"

    if [[ -z "${target_group_arn}" || "${target_group_arn}" == "None" ]]; then
        target_group_arn="$(
            aws_cli elbv2 create-target-group \
                --name "${target_group_name}" \
                --protocol HTTP \
                --port "${port}" \
                --target-type ip \
                --vpc-id "${VPC_ID}" \
                --health-check-protocol HTTP \
                --health-check-path "${health_check_path}" \
                --health-check-interval-seconds 30 \
                --health-check-timeout-seconds 5 \
                --healthy-threshold-count 2 \
                --unhealthy-threshold-count 3 \
                --matcher HttpCode=200 \
                --tags "Key=Project,Value=${PROJECT_TAG}" \
                --query 'TargetGroups[0].TargetGroupArn' \
                --output text
        )"
    fi

    aws_cli elbv2 modify-target-group-attributes \
        --target-group-arn "${target_group_arn}" \
        --attributes Key=deregistration_delay.timeout_seconds,Value=30 \
        >/dev/null

    printf '%s\n' "${target_group_arn}"
}

upsert_listener_rule() {
    local priority="$1"
    local conditions_file="$2"
    local rule_arn=""

    rule_arn="$(
        aws_cli elbv2 describe-rules \
            --listener-arn "${LISTENER_ARN}" \
            --query "Rules[?Priority=='${priority}'].RuleArn | [0]" \
            --output text
    )"

    if [[ -z "${rule_arn}" || "${rule_arn}" == "None" ]]; then
        aws_cli elbv2 create-rule \
            --listener-arn "${LISTENER_ARN}" \
            --priority "${priority}" \
            --conditions "file://${conditions_file}" \
            --actions "file://${TMP_DIR}/api-forward-action.json" \
            >/dev/null
    else
        aws_cli elbv2 modify-rule \
            --rule-arn "${rule_arn}" \
            --conditions "file://${conditions_file}" \
            --actions "file://${TMP_DIR}/api-forward-action.json" \
            >/dev/null
    fi
}

for command_name in aws curl python3; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Required command is not installed: ${command_name}" >&2
        exit 1
    fi
done

AWS_ACCOUNT_ID="$(
    aws_cli sts get-caller-identity \
        --query Account \
        --output text
)"
IMAGE_URI="${IMAGE_URI:-${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}}"

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
    echo "At least two default subnets are required for the load balancer." >&2
    exit 1
fi

SUBNETS_CSV="$(IFS=,; printf '%s' "${SUBNET_IDS[*]}")"

APP_SECURITY_GROUP_ID="$(
    aws_cli ec2 describe-security-groups \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=group-name,Values="${APP_SECURITY_GROUP}" \
        --query 'SecurityGroups[0].GroupId' \
        --output text
)"

if [[ -z "${APP_SECURITY_GROUP_ID}" || "${APP_SECURITY_GROUP_ID}" == "None" ]]; then
    echo "Application security group ${APP_SECURITY_GROUP} was not found." >&2
    echo "Run scripts/provision_aws_foundation.sh first." >&2
    exit 1
fi

ALB_SECURITY_GROUP_ID="$(
    aws_cli ec2 describe-security-groups \
        --filters \
            Name=vpc-id,Values="${VPC_ID}" \
            Name=group-name,Values="${ALB_SECURITY_GROUP}" \
        --query 'SecurityGroups[0].GroupId' \
        --output text
)"

if [[ -z "${ALB_SECURITY_GROUP_ID}" || "${ALB_SECURITY_GROUP_ID}" == "None" ]]; then
    ALB_SECURITY_GROUP_ID="$(
        aws_cli ec2 create-security-group \
            --group-name "${ALB_SECURITY_GROUP}" \
            --description "Public HTTP access for JobLens" \
            --vpc-id "${VPC_ID}" \
            --tag-specifications \
                "ResourceType=security-group,Tags=[{Key=Project,Value=${PROJECT_TAG}}]" \
            --query GroupId \
            --output text
    )"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

authorize_ingress \
    "${ALB_SECURITY_GROUP_ID}" tcp 80 \
    --cidr 0.0.0.0/0 \
    "${TMP_DIR}/alb-ingress-error.txt"
authorize_ingress \
    "${APP_SECURITY_GROUP_ID}" tcp 8501 \
    --source-group "${ALB_SECURITY_GROUP_ID}" \
    "${TMP_DIR}/dashboard-ingress-error.txt"
authorize_ingress \
    "${APP_SECURITY_GROUP_ID}" tcp 8000 \
    --source-group "${ALB_SECURITY_GROUP_ID}" \
    "${TMP_DIR}/api-ingress-error.txt"

LOG_GROUP="/ecs/${ECS_SERVICE}"
if ! aws_cli logs describe-log-groups \
    --log-group-name-prefix "${LOG_GROUP}" \
    --query "logGroups[?logGroupName=='${LOG_GROUP}']" \
    --output text \
    | grep -q .; then
    aws_cli logs create-log-group \
        --log-group-name "${LOG_GROUP}" \
        --tags "Project=${PROJECT_TAG}"
fi

aws_cli logs put-retention-policy \
    --log-group-name "${LOG_GROUP}" \
    --retention-in-days 14

LOAD_BALANCER_ARN="$(
    aws_cli elbv2 describe-load-balancers \
        --names "${ALB_NAME}" \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text \
        2>/dev/null || true
)"

if [[ -z "${LOAD_BALANCER_ARN}" || "${LOAD_BALANCER_ARN}" == "None" ]]; then
    LOAD_BALANCER_ARN="$(
        aws_cli elbv2 create-load-balancer \
            --name "${ALB_NAME}" \
            --type application \
            --scheme internet-facing \
            --ip-address-type ipv4 \
            --subnets "${SUBNET_IDS[@]}" \
            --security-groups "${ALB_SECURITY_GROUP_ID}" \
            --tags "Key=Project,Value=${PROJECT_TAG}" \
            --query 'LoadBalancers[0].LoadBalancerArn' \
            --output text
    )"
fi

echo "Waiting for ${ALB_NAME} to become available..."
aws_cli elbv2 wait load-balancer-available \
    --load-balancer-arns "${LOAD_BALANCER_ARN}"

LOAD_BALANCER_DNS="$(
    aws_cli elbv2 describe-load-balancers \
        --load-balancer-arns "${LOAD_BALANCER_ARN}" \
        --query 'LoadBalancers[0].DNSName' \
        --output text
)"

DASHBOARD_TARGET_GROUP_ARN="$(
    create_target_group \
        "${DASHBOARD_TARGET_GROUP}" \
        8501 \
        /_stcore/health
)"
API_TARGET_GROUP_ARN="$(
    create_target_group \
        "${API_TARGET_GROUP}" \
        8000 \
        /health
)"

LISTENER_ARN="$(
    aws_cli elbv2 describe-listeners \
        --load-balancer-arn "${LOAD_BALANCER_ARN}" \
        --query 'Listeners[?Port==`80`].ListenerArn | [0]' \
        --output text
)"

if [[ -z "${LISTENER_ARN}" || "${LISTENER_ARN}" == "None" ]]; then
    LISTENER_ARN="$(
        aws_cli elbv2 create-listener \
            --load-balancer-arn "${LOAD_BALANCER_ARN}" \
            --protocol HTTP \
            --port 80 \
            --default-actions \
                "Type=forward,TargetGroupArn=${DASHBOARD_TARGET_GROUP_ARN}" \
            --query 'Listeners[0].ListenerArn' \
            --output text
    )"
else
    aws_cli elbv2 modify-listener \
        --listener-arn "${LISTENER_ARN}" \
        --default-actions \
            "Type=forward,TargetGroupArn=${DASHBOARD_TARGET_GROUP_ARN}" \
        >/dev/null
fi

cat > "${TMP_DIR}/api-forward-action.json" <<JSON
[
  {
    "Type": "forward",
    "TargetGroupArn": "${API_TARGET_GROUP_ARN}"
  }
]
JSON

cat > "${TMP_DIR}/api-paths-primary.json" <<'JSON'
[
  {
    "Field": "path-pattern",
    "PathPatternConfig": {
      "Values": [
        "/health",
        "/docs*",
        "/redoc*",
        "/openapi.json",
        "/datasets*"
      ]
    }
  }
]
JSON

cat > "${TMP_DIR}/api-paths-secondary.json" <<'JSON'
[
  {
    "Field": "path-pattern",
    "PathPatternConfig": {
      "Values": [
        "/analysis-runs*",
        "/analyze"
      ]
    }
  }
]
JSON

upsert_listener_rule 10 "${TMP_DIR}/api-paths-primary.json"
upsert_listener_rule 20 "${TMP_DIR}/api-paths-secondary.json"

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
      "name": "joblens-app",
      "image": "${IMAGE_URI}",
      "essential": true,
      "command": ["/app/scripts/start_aws_services.sh"],
      "portMappings": [
        {
          "name": "dashboard",
          "containerPort": 8501,
          "hostPort": 8501,
          "protocol": "tcp"
        },
        {
          "name": "api",
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
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
          "awslogs-group": "${LOG_GROUP}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "service"
        }
      }
    }
  ],
  "tags": [
    {
      "key": "Project",
      "value": "${PROJECT_TAG}"
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

SERVICE_ARN="$(
    aws_cli ecs describe-services \
        --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}" \
        --query 'services[?status!=`INACTIVE`].serviceArn | [0]' \
        --output text
)"

NETWORK_CONFIGURATION="awsvpcConfiguration={subnets=[${SUBNETS_CSV}],securityGroups=[${APP_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"

if [[ -z "${SERVICE_ARN}" || "${SERVICE_ARN}" == "None" ]]; then
    aws_cli ecs create-service \
        --cluster "${ECS_CLUSTER}" \
        --service-name "${ECS_SERVICE}" \
        --task-definition "${TASK_DEFINITION_ARN}" \
        --desired-count "${DESIRED_COUNT}" \
        --launch-type FARGATE \
        --platform-version LATEST \
        --network-configuration "${NETWORK_CONFIGURATION}" \
        --load-balancers \
            "targetGroupArn=${DASHBOARD_TARGET_GROUP_ARN},containerName=joblens-app,containerPort=8501" \
            "targetGroupArn=${API_TARGET_GROUP_ARN},containerName=joblens-app,containerPort=8000" \
        --health-check-grace-period-seconds 120 \
        --deployment-configuration \
            "maximumPercent=200,minimumHealthyPercent=0,deploymentCircuitBreaker={enable=true,rollback=true}" \
        --propagate-tags SERVICE \
        --tags "key=Project,value=${PROJECT_TAG}" \
        >/dev/null
else
    aws_cli ecs update-service \
        --cluster "${ECS_CLUSTER}" \
        --service "${ECS_SERVICE}" \
        --task-definition "${TASK_DEFINITION_ARN}" \
        --desired-count "${DESIRED_COUNT}" \
        --network-configuration "${NETWORK_CONFIGURATION}" \
        --load-balancers \
            "targetGroupArn=${DASHBOARD_TARGET_GROUP_ARN},containerName=joblens-app,containerPort=8501" \
            "targetGroupArn=${API_TARGET_GROUP_ARN},containerName=joblens-app,containerPort=8000" \
        --health-check-grace-period-seconds 120 \
        --deployment-configuration \
            "maximumPercent=200,minimumHealthyPercent=0,deploymentCircuitBreaker={enable=true,rollback=true}" \
        --force-new-deployment \
        >/dev/null
fi

echo "Waiting for ${ECS_SERVICE} to become stable..."
aws_cli ecs wait services-stable \
    --cluster "${ECS_CLUSTER}" \
    --services "${ECS_SERVICE}"

DASHBOARD_URL="http://${LOAD_BALANCER_DNS}"
API_HEALTH_URL="${DASHBOARD_URL}/health"

for attempt in {1..20}; do
    if curl --fail --silent \
        "${API_HEALTH_URL}" \
        | grep -q '"status":"ok"'; then
        break
    fi

    if (( attempt == 20 )); then
        echo "The service is stable, but the API health check did not pass." >&2
        exit 1
    fi

    sleep 10
done

echo "JobLens AWS service is ready."
echo "Dashboard: ${DASHBOARD_URL}"
echo "API health: ${API_HEALTH_URL}"
echo "API docs: ${DASHBOARD_URL}/docs"

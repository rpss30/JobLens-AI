#!/usr/bin/env bash

set -euo pipefail

AWS_REGION="${AWS_REGION:-ca-central-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-joblens-ai}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

for command_name in aws docker git; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Required command is not installed: ${command_name}" >&2
        exit 1
    fi
done

AWS_ACCOUNT_ID="$(
    aws sts get-caller-identity \
        --query Account \
        --output text \
        --region "${AWS_REGION}"
)"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
LATEST_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

if ! aws ecr describe-repositories \
    --repository-names "${ECR_REPOSITORY}" \
    --region "${AWS_REGION}" \
    >/dev/null 2>&1; then
    aws ecr create-repository \
        --repository-name "${ECR_REPOSITORY}" \
        --image-scanning-configuration scanOnPush=true \
        --region "${AWS_REGION}" \
        >/dev/null
fi

aws ecr get-login-password --region "${AWS_REGION}" \
    | docker login \
        --username AWS \
        --password-stdin "${ECR_REGISTRY}"

docker build \
    --platform linux/amd64 \
    --tag "${IMAGE_URI}" \
    .

docker tag "${IMAGE_URI}" "${LATEST_IMAGE_URI}"
docker push "${IMAGE_URI}"
docker push "${LATEST_IMAGE_URI}"

echo "Published image: ${IMAGE_URI}"
echo "Published latest tag: ${LATEST_IMAGE_URI}"

#!/usr/bin/env bash
# Tag the local image and push it to AWS ECR.
# Requires: AWS CLI configured, image already built with build.sh.
# Usage:
#   ./scripts/push_ecr.sh
#   TAG=abc123 AWS_REGION=us-east-1 ./scripts/push_ecr.sh
set -euo pipefail

REGION="${AWS_REGION:-eu-west-1}"
PROJECT="rag-course"
TAG="${TAG:-latest}"

# Resolve the AWS account ID dynamically — no hardcoding.
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_URI="${REGISTRY}/${PROJECT}"

echo "→ Logging in to ECR (${REGISTRY})..."
aws ecr get-login-password --region "${REGION}" | \
  podman login --username AWS --password-stdin "${REGISTRY}"

echo "→ Tagging ${PROJECT}:${TAG} → ${ECR_URI}:${TAG}..."
podman tag "${PROJECT}:${TAG}" "${ECR_URI}:${TAG}"

echo "→ Pushing..."
podman push "${ECR_URI}:${TAG}"

echo "✓ Pushed: ${ECR_URI}:${TAG}"

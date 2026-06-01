#!/usr/bin/env bash
# SSH into the EC2 instance, pull the latest image, and restart the service.
# Run this after push_ecr.sh to deploy a new version.
# Usage:
#   EC2_HOST=1.2.3.4 ./scripts/deploy.sh
#   EC2_HOST=1.2.3.4 TAG=abc123 SSH_KEY=~/.ssh/mykey.pem ./scripts/deploy.sh
set -euo pipefail

EC2_HOST="${EC2_HOST:?ERROR: set EC2_HOST to the public IP of your EC2 instance}"
SSH_KEY="${SSH_KEY:-./rag-course-key.pem}"
REGION="${AWS_REGION:-eu-west-1}"
PROJECT="rag-course"
TAG="${TAG:-latest}"

echo "→ Deploying ${PROJECT}:${TAG} to ${EC2_HOST}..."

# All commands run remotely on EC2 via SSH.
# The heredoc is executed in a single SSH session.
ssh -i "${SSH_KEY}" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=15 \
    "ec2-user@${EC2_HOST}" \
    bash << REMOTE
set -euo pipefail

ACCOUNT_ID=\$(aws sts get-caller-identity --query Account --output text)
REGISTRY="\${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_URI="\${REGISTRY}/${PROJECT}"

echo "  → Logging in to ECR..."
aws ecr get-login-password --region "${REGION}" | \
  podman login --username AWS --password-stdin "\${REGISTRY}"

echo "  → Pulling \${ECR_URI}:${TAG}..."
podman pull "\${ECR_URI}:${TAG}"

echo "  → Restarting systemd service..."
sudo systemctl restart ${PROJECT}

echo "  → Service status:"
sudo systemctl status ${PROJECT} --no-pager --lines=5
REMOTE

echo "✓ Deploy complete. API: http://${EC2_HOST}:8000"

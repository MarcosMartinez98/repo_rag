#!/usr/bin/env bash
# Deletes ALL AWS resources created by create_infrastructure.sh.
# Run this when you're done to avoid any unexpected charges.
#
# Usage:
#   AWS_REGION=eu-west-1 ./infra/destroy_infrastructure.sh
set -euo pipefail

REGION="${AWS_REGION:-eu-west-1}"
PROJECT="rag-course"
KEY_PAIR_NAME="${PROJECT}-key"
SG_NAME="${PROJECT}-sg"

echo "============================================================"
echo " ⚠️  Destroying ALL ${PROJECT} AWS resources in ${REGION}"
echo "============================================================"
echo "  Press Ctrl+C within 5 seconds to cancel..."
sleep 5

# ── 1. Terminate EC2 instances ────────────────────────────────────────────────
echo ""
echo "[1/6] Terminating EC2 instances..."
INSTANCE_IDS=$(aws ec2 describe-instances \
  --region "${REGION}" \
  --filters \
    "Name=tag:Name,Values=${PROJECT}" \
    "Name=instance-state-name,Values=running,stopped,stopping" \
  --query "Reservations[].Instances[].InstanceId" \
  --output text)

if [ -n "${INSTANCE_IDS}" ]; then
  aws ec2 terminate-instances \
    --instance-ids ${INSTANCE_IDS} \
    --region "${REGION}" \
    --output text > /dev/null
  echo "  Waiting for instances to terminate..."
  aws ec2 wait instance-terminated \
    --instance-ids ${INSTANCE_IDS} \
    --region "${REGION}"
  echo "  Terminated: ${INSTANCE_IDS}"
else
  echo "  No running instances found."
fi

# ── 2. Delete security group ──────────────────────────────────────────────────
# Must wait until instances are terminated before deleting their security group.
echo ""
echo "[2/6] Deleting security group..."
aws ec2 delete-security-group \
  --group-name "${SG_NAME}" \
  --region "${REGION}" 2>/dev/null && echo "  Deleted." || echo "  Not found."

# ── 3. Delete key pair ────────────────────────────────────────────────────────
echo ""
echo "[3/6] Deleting key pair..."
aws ec2 delete-key-pair \
  --key-name "${KEY_PAIR_NAME}" \
  --region "${REGION}" 2>/dev/null && echo "  Deleted from AWS." || echo "  Not found in AWS."
rm -f "${KEY_PAIR_NAME}.pem" && echo "  Removed local .pem file." || true

# ── 4. Delete ECR repository (and all images inside) ─────────────────────────
echo ""
echo "[4/6] Deleting ECR repository..."
aws ecr delete-repository \
  --repository-name "${PROJECT}" \
  --region "${REGION}" \
  --force 2>/dev/null && echo "  Deleted." || echo "  Not found."

# ── 5. Delete SSM parameters ──────────────────────────────────────────────────
echo ""
echo "[5/6] Deleting SSM parameters..."
aws ssm delete-parameter \
  --name "/${PROJECT}/cohere_api_key" \
  --region "${REGION}" 2>/dev/null && echo "  Deleted." || echo "  Not found."

# ── 6. Delete IAM role and instance profile ───────────────────────────────────
echo ""
echo "[6/6] Cleaning up IAM..."
aws iam remove-role-from-instance-profile \
  --instance-profile-name "${PROJECT}-ec2-profile" \
  --role-name "${PROJECT}-ec2-role" 2>/dev/null || true

aws iam delete-instance-profile \
  --instance-profile-name "${PROJECT}-ec2-profile" 2>/dev/null || true

aws iam detach-role-policy \
  --role-name "${PROJECT}-ec2-role" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" 2>/dev/null || true

aws iam detach-role-policy \
  --role-name "${PROJECT}-ec2-role" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess" 2>/dev/null || true

aws iam delete-role \
  --role-name "${PROJECT}-ec2-role" 2>/dev/null && echo "  IAM role deleted." || echo "  Role not found."

echo ""
echo "============================================================"
echo " ✓  All ${PROJECT} resources deleted. No more charges."
echo "============================================================"

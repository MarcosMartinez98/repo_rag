#!/usr/bin/env bash
# Provisions all AWS resources needed to run the RAG Course API.
# Everything created here stays within the AWS Free Tier.
#
# What gets created:
#   - ECR repository           (stores the container image, 500MB free)
#   - IAM role + profile       (lets EC2 pull from ECR and read SSM)
#   - EC2 key pair             (SSH access to the instance)
#   - Security group           (opens port 22 for SSH, 8000 for the API)
#   - SSM Parameter Store      (stores COHERE_API_KEY securely, free standard tier)
#   - EC2 t2.micro             (runs the container, 750h/month free for 12 months)
#
# Prerequisites:
#   - AWS CLI installed and configured (aws configure)
#   - COHERE_API_KEY set as an environment variable
#
# Usage:
#   COHERE_API_KEY=your-key AWS_REGION=eu-west-1 ./infra/create_infrastructure.sh
set -euo pipefail

REGION="${AWS_REGION:-eu-west-1}"
PROJECT="rag-course"
KEY_PAIR_NAME="${PROJECT}-key"
SG_NAME="${PROJECT}-sg"
INSTANCE_TYPE="t3.micro"

if [ -z "${COHERE_API_KEY:-}" ]; then
  echo "ERROR: set the COHERE_API_KEY environment variable before running this script."
  exit 1
fi

echo "============================================================"
echo " Provisioning ${PROJECT} infrastructure in ${REGION}"
echo "============================================================"

# ── 1. ECR Repository ─────────────────────────────────────────────────────────
# ECR stores your container images. 500MB is free per month.
# scan-on-push checks for known CVEs every time you push a new image.
echo ""
echo "[1/7] Creating ECR repository..."
aws ecr create-repository \
  --repository-name "${PROJECT}" \
  --region "${REGION}" \
  --image-scanning-configuration scanOnPush=true \
  --query "repository.repositoryUri" \
  --output text \
  2>/dev/null || echo "  (already exists — skipping)"

# ── 2. IAM Role ───────────────────────────────────────────────────────────────
# EC2 needs permission to:
#   - Pull images from ECR (AmazonEC2ContainerRegistryReadOnly)
#   - Read secrets from SSM Parameter Store (AmazonSSMReadOnlyAccess)
# Using a role is the secure way — no long-lived access keys on the instance.
echo ""
echo "[2/7] Creating IAM role..."
aws iam create-role \
  --role-name "${PROJECT}-ec2-role" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --output text 2>/dev/null || echo "  (role already exists — skipping)"

aws iam attach-role-policy \
  --role-name "${PROJECT}-ec2-role" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" \
  2>/dev/null || true

aws iam attach-role-policy \
  --role-name "${PROJECT}-ec2-role" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess" \
  2>/dev/null || true

# Instance profile is the "wrapper" that lets EC2 use an IAM role.
aws iam create-instance-profile \
  --instance-profile-name "${PROJECT}-ec2-profile" \
  2>/dev/null || true

aws iam add-role-to-instance-profile \
  --instance-profile-name "${PROJECT}-ec2-profile" \
  --role-name "${PROJECT}-ec2-role" \
  2>/dev/null || true

echo "  IAM role and instance profile ready."

# ── 3. EC2 Key Pair ───────────────────────────────────────────────────────────
# The private key (.pem) is saved once — AWS never shows it again.
# Keep it safe: it's your only way to SSH into the instance.
echo ""
echo "[3/7] Creating EC2 key pair..."
if [ ! -f "${KEY_PAIR_NAME}.pem" ]; then
  aws ec2 create-key-pair \
    --key-name "${KEY_PAIR_NAME}" \
    --region "${REGION}" \
    --query "KeyMaterial" \
    --output text > "${KEY_PAIR_NAME}.pem"
  chmod 400 "${KEY_PAIR_NAME}.pem"
  echo "  Private key saved to ./${KEY_PAIR_NAME}.pem — do NOT commit this file."
else
  echo "  Key file already exists locally — skipping."
fi

# ── 4. Security Group ─────────────────────────────────────────────────────────
# A firewall that controls what traffic can reach the EC2 instance.
# Port 22   → SSH (so you can log in and run commands)
# Port 8000 → the FastAPI server (so the API is reachable from the internet)
#
# In a real production setup you would restrict port 22 to your IP only.
echo ""
echo "[4/7] Creating security group..."
VPC_ID=$(aws ec2 describe-vpcs \
  --region "${REGION}" \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text)

SG_ID=$(aws ec2 create-security-group \
  --group-name "${SG_NAME}" \
  --description "${PROJECT} — SSH + API" \
  --vpc-id "${VPC_ID}" \
  --region "${REGION}" \
  --query "GroupId" \
  --output text 2>/dev/null || \
  aws ec2 describe-security-groups \
    --region "${REGION}" \
    --filters "Name=group-name,Values=${SG_NAME}" \
    --query "SecurityGroups[0].GroupId" \
    --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "${SG_ID}" \
  --protocol tcp --port 22 --cidr "0.0.0.0/0" \
  --region "${REGION}" 2>/dev/null || true

aws ec2 authorize-security-group-ingress \
  --group-id "${SG_ID}" \
  --protocol tcp --port 8000 --cidr "0.0.0.0/0" \
  --region "${REGION}" 2>/dev/null || true

echo "  Security group: ${SG_ID}"

# ── 5. SSM Parameter Store ────────────────────────────────────────────────────
# SecureString encrypts the value with KMS at rest.
# The EC2 instance retrieves it at boot using its IAM role — no .env files on disk.
echo ""
echo "[5/7] Storing COHERE_API_KEY in SSM Parameter Store..."
aws ssm put-parameter \
  --name "/rag_course/cohere_api_key" \
  --value "${COHERE_API_KEY}" \
  --type "SecureString" \
  --region "${REGION}" \
  --overwrite \
  --output text > /dev/null
echo "  Stored at /${PROJECT}/cohere_api_key"

# ── 6. Get latest Amazon Linux 2023 AMI ───────────────────────────────────────
# AL2023 is AWS's current free-tier Linux. It ships with Podman pre-installed.
echo ""
echo "[6/7] Finding latest Amazon Linux 2023 AMI..."
AMI_ID=$(aws ec2 describe-images \
  --region "${REGION}" \
  --owners amazon \
  --filters \
    "Name=name,Values=al2023-ami-2023*-x86_64" \
    "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text)
echo "  AMI: ${AMI_ID}"

# ── 7. Launch EC2 t2.micro ────────────────────────────────────────────────────
# user-data is a script that runs ONCE on first boot.
# It installs Podman, pulls the image, and starts the systemd service.
# The EBS root volume is 8GB (included free with t2.micro).
echo ""
echo "[7/7] Launching EC2 t2.micro..."

# IAM instance profiles take a few seconds to propagate after creation.
echo "  Waiting 10s for IAM profile to propagate..."
sleep 10

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "${AMI_ID}" \
  --instance-type "${INSTANCE_TYPE}" \
  --key-name "${KEY_PAIR_NAME}" \
  --security-group-ids "${SG_ID}" \
  --iam-instance-profile "Name=${PROJECT}-ec2-profile" \
  --region "${REGION}" \
  --user-data "file://infra/ec2_userdata.sh" \
  --block-device-mappings '[{
    "DeviceName": "/dev/xvda",
    "Ebs": {"VolumeSize": 8, "VolumeType": "gp2", "DeleteOnTermination": true}
  }]' \
  --tag-specifications \
    "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT}},{Key=Project,Value=${PROJECT}}]" \
  --query "Instances[0].InstanceId" \
  --output text)

echo "  Instance launched: ${INSTANCE_ID}"
echo "  Waiting for it to reach 'running' state..."
aws ec2 wait instance-running \
  --instance-ids "${INSTANCE_ID}" \
  --region "${REGION}"

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --region "${REGION}" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

echo ""
echo "============================================================"
echo " ✓  Infrastructure ready!"
echo "============================================================"
echo "  Instance ID : ${INSTANCE_ID}"
echo "  Public IP   : ${PUBLIC_IP}"
echo ""
echo "  The EC2 instance is bootstrapping (~3 min)."
echo "  It will pull the image from ECR and start the API automatically."
echo ""
echo "  SSH in:       ssh -i ${KEY_PAIR_NAME}.pem ec2-user@${PUBLIC_IP}"
echo "  Watch logs:   ssh -i ${KEY_PAIR_NAME}.pem ec2-user@${PUBLIC_IP} 'sudo journalctl -u rag-course -f'"
echo "  API:          http://${PUBLIC_IP}:8000"
echo "  API docs:     http://${PUBLIC_IP}:8000/docs"
echo ""
echo "  To deploy a new version: EC2_HOST=${PUBLIC_IP} ./scripts/deploy.sh"
echo "  To tear everything down: ./infra/destroy_infrastructure.sh"

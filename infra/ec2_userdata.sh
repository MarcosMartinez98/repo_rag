#!/usr/bin/env bash
# EC2 User Data script — runs ONCE automatically on first boot.
# AWS injects this script and executes it as root before the instance is ready.
#
# This script:
#   1. Updates the system and installs Podman
#   2. Retrieves the COHERE_API_KEY from SSM Parameter Store
#   3. Creates a persistent directory for ChromaDB data
#   4. Pulls the container image from ECR
#   5. Registers a systemd service that keeps the API running
#
# Logs are written to: /var/log/rag-course-init.log
set -euo pipefail
exec > /var/log/rag-course-init.log 2>&1

PROJECT="rag-course"
REGION="eu-west-1"    # must match create_infrastructure.sh

echo "[$(date)] Starting RAG Course bootstrap..."

# ── 1. System update and Podman ───────────────────────────────────────────────
# Amazon Linux 2023 ships with Podman available in the default repos.
echo "[$(date)] Installing system packages..."
dnf update -y --quiet
dnf install -y docker
systemctl enable docker
systemctl start docker

# ── 2. Retrieve COHERE_API_KEY from SSM ───────────────────────────────────────
# --with-decryption decrypts the SecureString — only works because the EC2
# instance has the SSMReadOnlyAccess policy via its IAM role.
echo "[$(date)] Retrieving secrets from SSM..."
COHERE_API_KEY=$(aws ssm get-parameter \
  --name "/${PROJECT}/cohere_api_key" \
  --with-decryption \
  --region "${REGION}" \
  --query "Parameter.Value" \
  --output text)

# ── 3. Write runtime env file ─────────────────────────────────────────────────
# chmod 600 means only root can read this file.
mkdir -p /opt/${PROJECT}
cat > /opt/${PROJECT}/.env << EOF
COHERE_API_KEY=${COHERE_API_KEY}
CHROMA_PERSIST_DIRECTORY=/app/chroma_db
EOF
chmod 600 /opt/${PROJECT}/.env

# ── 4. Persistent ChromaDB volume directory ───────────────────────────────────
# This directory on the EBS root volume survives container restarts.
# In a full production setup you would use a separate EBS volume here.
mkdir -p /opt/${PROJECT}/chroma_db
chown -R 1001:1001 /opt/${PROJECT}/chroma_db

# ── 5. Pull container image from ECR ─────────────────────────────────────────
echo "[$(date)] Pulling image from ECR..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_URI="${REGISTRY}/${PROJECT}"

ECR_TOKEN=$(aws ecr get-login-password --region "${REGION}")
docker login --username AWS --password "${ECR_TOKEN}" "${REGISTRY}"

docker pull "${ECR_URI}:latest"
echo "[$(date)] Image pulled: ${ECR_URI}:latest"

# ── 6. Create systemd service ─────────────────────────────────────────────────
# systemd manages the container lifecycle:
#   - Starts it when the EC2 instance boots
#   - Restarts it automatically if it crashes (Restart=always)
#   - Logs are accessible via: journalctl -u rag-course
cat > /etc/systemd/system/${PROJECT}.service << EOF
[Unit]
Description=RAG Course API
Documentation=https://github.com/MarcosMartinez98/repo_rag
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10

# Remove any stale container from a previous run
ExecStartPre=-/usr/bin/docker rm -f ${PROJECT}

# Run the container:
#   --rm          removes the container when it stops (the volume data persists)
#   --env-file    injects the COHERE_API_KEY
#   --volume      mounts the ChromaDB data directory from the host
#   --publish     exposes port 8000 to the outside world
ExecStart=/usr/bin/docker run \
  --name ${PROJECT} \
  --rm \
  --env-file /opt/${PROJECT}/.env \
  --volume /opt/${PROJECT}/chroma_db:/app/chroma_db \
  --publish 8000:8000 \
  ${ECR_URI}:latest

ExecStop=/usr/bin/docker stop ${PROJECT}

[Install]
WantedBy=multi-user.target
EOF

# ── 7. Enable and start the service ───────────────────────────────────────────
systemctl daemon-reload
systemctl enable ${PROJECT}
systemctl start ${PROJECT}

echo "[$(date)] Bootstrap complete. Service started."
echo "[$(date)] Check status: systemctl status ${PROJECT}"
echo "[$(date)] Watch logs:   journalctl -u ${PROJECT} -f"

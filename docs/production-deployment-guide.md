# Tenderpreneur MVP — Production Deployment Guide

This guide describes the complete procedure for deploying **Tenderpreneur** to a production cloud server (VPS) running Ubuntu 24.04 LTS with automated HTTPS, PostgreSQL 17, MinIO object storage, FastAPI backend, and Next.js 15 frontend.

---

## 1. System Requirements & Hosting Recommendations

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **CPU** | 2 vCPUs | 4 vCPUs |
| **RAM** | 4 GB | 8 GB |
| **Storage** | 40 GB NVMe SSD | 80 GB NVMe SSD |
| **Operating System** | Ubuntu 22.04 / 24.04 LTS | Ubuntu 24.04 LTS |

### Recommended VPS Providers
- **Hetzner Cloud**: `CPX21` (3 vCPU, 4GB RAM) or `CPX31` (4 vCPU, 8GB RAM) — excellent performance/price ratio.
- **DigitalOcean**: Basic Droplet with Dedicated CPU ($24/mo).
- **AWS EC2**: `t3.medium` or `t4g.medium` (with 50GB gp3 EBS).

---

## 2. Server Provisioning & Initial Hardening

### 2.1. Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw htop
```

### 2.2. Configure UFW Firewall
Allow SSH, HTTP, and HTTPS only:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2.3. Install Docker Engine & Docker Compose
```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow non-root user to run docker
sudo usermod -aG docker $USER
newgrp docker
```

---

## 3. DNS Configuration

Point your domain name records to the server's public IPv4 address:

| Type | Host | Value | Purpose |
|---|---|---|---|
| **A** | `app` | `YOUR_SERVER_PUBLIC_IP` | Main Web & API domain (`app.tenderpreneur.co.za`) |
| **A** | `@` (root) | `YOUR_SERVER_PUBLIC_IP` | Optional root domain |

*Wait 5–10 minutes for DNS propagation before running Caddy, as Caddy validates domain ownership with Let's Encrypt via HTTP-01 challenge.*

---

## 4. Application Deployment

### 4.1. Clone Repository
```bash
git clone https://github.com/your-org/tenderpreneur.git /opt/tenderpreneur
cd /opt/tenderpreneur/infra/docker
```

### 4.2. Configure Production Environment
Copy the production template and generate cryptographically secure secrets:
```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Generate a secure 64-character hexadecimal key for JWT signing:
```bash
openssl rand -hex 32
```

Generate secure passwords for PostgreSQL and MinIO:
```bash
openssl rand -base64 24
```

Edit `.env.production` using `nano .env.production`:
- Set `DOMAIN_NAME=app.tenderpreneur.co.za`
- Set `TENDERPRENEUR_JWT_SECRET=<your-openssl-generated-hex>`
- Set `POSTGRES_PASSWORD=<your-db-password>`
- Set `MINIO_ROOT_PASSWORD=<your-minio-password>`
- Set `TENDERPRENEUR_GEMINI_API_KEY=<your-google-gemini-api-key>`
- Set `TENDERPRENEUR_SMTP_PASSWORD=<your-sendgrid-or-smtp-key>`

### 4.3. Run Automated Deployment
Make the deployment script executable and run it:
```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Validate that all security variables are non-default and >= 32 characters.
2. Build optimized multi-stage production containers for API and Web.
3. Boot PostgreSQL 17, MinIO, API, Web, and Caddy.
4. Run Alembic migrations (`alembic upgrade head`).
5. Verify health probes.

---

## 5. Post-Deployment Verification

### 5.1. Check Container Status
```bash
docker compose ps
```
Expected output: All services (`postgres`, `minio`, `api`, `web`, `caddy`) show status `Up` (healthy).

### 5.2. Run Smoke Test Suite
Run the automated procurement verification loop inside the API container:
```bash
docker compose exec api python -m pytest tests/test_mvp_verification_loop.py -v
```

### 5.3. Ingest Sample Production Data (Optional)
To seed the initial contractor and supplier directory into production:
```bash
docker compose exec api python -m app.seed
```

---

## 6. Backup & Disaster Recovery Runbook

### 6.1. Automated Daily PostgreSQL Database Backup
Create `/opt/tenderpreneur/scripts/backup-db.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="/var/backups/tenderpreneur"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
docker compose -f /opt/tenderpreneur/infra/docker/docker-compose.yml exec -T postgres pg_dump -U tenderpreneur tenderpreneur | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete
```
Schedule via root cron (`sudo crontab -e`):
```cron
0 2 * * * /opt/tenderpreneur/scripts/backup-db.sh >> /var/log/tenderpreneur-backup.log 2>&1
```

### 6.2. Document Storage Disaster Recovery (MinIO)
MinIO stores raw uploaded BoQ schedules, spreadsheets, and generated PDF/Excel audit exports in the `tenderpreneur_minio` Docker volume. For offsite disaster recovery, sync `/var/lib/docker/volumes/tenderpreneur_minio/_data` to AWS S3 or Backblaze B2 using `rclone`.

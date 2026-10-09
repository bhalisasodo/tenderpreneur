# BoQPro MVP — Production Deployment Guide

This guide describes the deployment procedure for **BoQPro** to a production cloud server (VPS) running Ubuntu 24.04 LTS with automated HTTPS, PostgreSQL 17, persistent local file storage, a FastAPI backend, and a Next.js 15 frontend.

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

### 2.2. Configure Firewall (UFW)
Allow SSH, HTTP, and HTTPS:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2.3. Install Docker & Docker Compose
```bash
# Add Docker's official GPG key:
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker:
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 3. DNS Configuration

Point your domain A records to your server public IP address:

| Record Type | Hostname | Value | Purpose |
|---|---|---|---|
| **A** | `app` | `YOUR_SERVER_PUBLIC_IP` | Main Web & API domain (`app.boqpro.co.za`) |
| **A** | `@` (root) | `YOUR_SERVER_PUBLIC_IP` | Optional root domain |

*Wait 5–10 minutes for DNS propagation before running Caddy, as Caddy validates domain ownership with Let's Encrypt via HTTP-01 challenge.*

---

## 4. Application Deployment

### 4.1. Clone Repository
```bash
git clone https://github.com/your-org/boqpro.git /opt/boqpro
cd /opt/boqpro
```

### 4.2. Configure Production Environment
Copy the production template and generate cryptographically secure secrets:
```bash
cp infra/docker/env.production.example .env.production
chmod 600 .env.production
```

Generate a secure 64-character hexadecimal key for JWT signing:
```bash
openssl rand -hex 32
```

Generate a password for PostgreSQL:
```bash
openssl rand -hex 24
```

Edit `.env.production` using `nano .env.production`:
- Set `DOMAIN_NAME=app.boqpro.co.za`
- Set `BOQPRO_JWT_SECRET=<your-openssl-generated-hex>`
- Set `POSTGRES_PASSWORD` and the same password in `BOQPRO_DATABASE_URL`
- Set `BOQPRO_PASSWORD_SALT=<a-separate-openssl-generated-hex>`
- Set `BOQPRO_APP_BASE_URL` and `BOQPRO_PUBLIC_APP_URL` to your HTTPS app URL
- Set `BOQPRO_CORS_ORIGINS` to a JSON array containing the HTTPS app origin
- Set `BOQPRO_GEMINI_API_KEY=<your-google-gemini-api-key>`
- Set `BOQPRO_SMTP_PASSWORD=<your-sendgrid-or-smtp-key>`

The example defaults to the rule-based parser and console notifications. Configure Gemini and a real SMTP provider before relying on AI parsing or quote-request email delivery. Uploaded files are stored in a persistent local Docker volume; back it up with the database.

### 4.3. Run Automated Deployment
Make the deployment script executable and run it:
```bash
chmod +x infra/docker/deploy.sh
infra/docker/deploy.sh
```

The script will:
1. Validate that all security variables are non-default and >= 32 characters.
2. Build optimized multi-stage production containers for API and Web.
3. Boot PostgreSQL 17, API, Web, and Caddy.
4. Run Alembic migrations (`alembic upgrade head`).
5. Verify health probes.

---

## 5. Post-Deployment Verification

### 5.1. Check Container Status
```bash
docker compose -f infra/docker/docker-compose.yml --env-file .env.production ps
```
Expected output: All services (`postgres`, `api`, `web`, `caddy`) show status `Up`.

### 5.2. Verify Public Health
Confirm that the public health endpoint responds after deployment:
```bash
curl --fail --show-error https://app.boqpro.co.za/health
```

### 5.3. Account Onboarding
Contractors can register from the public web app and access their workspace immediately. Supplier registrations create pending applications; a platform operator must review and approve them before they can receive marketplace requests. Do not create platform operator accounts through public registration.

BoQPro does not create demo users or seed production tenants automatically. Create the initial platform operator account interactively after verifying the administrator:
```bash
docker compose -f infra/docker/docker-compose.yml --env-file .env.production exec -it api \
  python -m app.commands.create_account \
  --organisation-type contractor \
  --organisation-name "BoQPro Platform Operations" \
  --organisation-email "operations@example.co.za" \
  --region "eThekwini" \
  --user-name "Platform Operator" \
  --user-email "operator@example.co.za" \
  --role platform_operator
```
The command prompts for a password and confirmation; do not pass passwords as command-line arguments. Store operator credentials securely and restrict operator access to separately verified staff.

Before opening public registration, verify the production domain, HTTPS, database backups, storage persistence, parser-provider configuration, outbound notifications and supplier-approval staffing. Contractor registrations are immediately enabled and do not currently require email verification.

---

## 6. Backup & Disaster Recovery Runbook

### 6.1. Automated Daily PostgreSQL Database Backup
Create `/opt/boqpro/scripts/backup-db.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="/var/backups/boqpro"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
docker compose -f /opt/boqpro/infra/docker/docker-compose.yml exec -T postgres pg_dump -U boqpro boqpro | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete
```
Schedule via root cron (`sudo crontab -e`):
```cron
0 2 * * * /opt/boqpro/scripts/backup-db.sh >> /var/log/boqpro-backup.log 2>&1
```

### 6.2. Document Storage Disaster Recovery
The current Compose deployment stores uploaded documents and generated exports in the persistent `boqpro_storage` Docker volume. Back up this volume alongside PostgreSQL and test restoration before launch. The current application supports local file storage; an object-storage provider must be implemented before replacing it with S3-compatible storage.

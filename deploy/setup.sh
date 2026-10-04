#!/usr/bin/env bash
# ==============================================================================
# FarmKonnect — Production Deployment Automation Script (Ubuntu 22.04 / 24.04)
# Domain: farmkonnect.zirocreativeagency.co.ke
# ==============================================================================

set -euo pipefail

APP_DIR="/var/www/farmkonnect"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/venv"
DOMAIN="farmkonnect.zirocreativeagency.co.ke"
WWW_DOMAIN="www.farmkonnect.zirocreativeagency.co.ke"

echo "=== [1/8] Installing System Dependencies ==="
sudo apt-get update -y
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    python3-dev \
    libpq-dev \
    nginx \
    postgresql \
    postgresql-contrib \
    redis-server \
    certbot \
    python3-certbot-nginx \
    gunicorn \
    curl \
    git \
    ufw

echo "=== [2/8] Setting Up Directory Layout & Permissions ==="
sudo mkdir -p "${APP_DIR}"
sudo mkdir -p "${BACKEND_DIR}/logs"
sudo mkdir -p "${BACKEND_DIR}/staticfiles"
sudo mkdir -p "${BACKEND_DIR}/media"
sudo mkdir -p /var/www/certbot
sudo mkdir -p /var/backups/farmkonnect

sudo chown -R www-data:www-data "${APP_DIR}"
sudo chmod -R 755 "${APP_DIR}"
sudo chmod -R 775 "${BACKEND_DIR}/logs"
sudo chmod -R 775 "${BACKEND_DIR}/staticfiles"
sudo chmod -R 775 "${BACKEND_DIR}/media"

echo "=== [3/8] Python Virtual Environment & Dependencies ==="
if [ ! -d "${VENV_DIR}" ]; then
    sudo -u www-data python3 -m venv "${VENV_DIR}"
fi

sudo -u www-data "${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel
sudo -u www-data "${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"
sudo -u www-data "${VENV_DIR}/bin/pip" install psycopg2-binary gunicorn

echo "=== [4/8] Configuring PostgreSQL Database ==="
# Check if database exists, create if not
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'farmkonnect'" | grep -q 1 || \
sudo -u postgres psql <<'SQL'
CREATE DATABASE farmkonnect;
CREATE USER farmkonnect WITH ENCRYPTED PASSWORD 'CHANGE_TO_GENERATED_PASSWORD';
ALTER ROLE farmkonnect SET client_encoding TO 'utf8';
ALTER ROLE farmkonnect SET default_transaction_isolation TO 'read committed';
ALTER ROLE farmkonnect SET timezone TO 'Africa/Nairobi';
GRANT ALL PRIVILEGES ON DATABASE farmkonnect TO farmkonnect;
\c farmkonnect
GRANT ALL ON SCHEMA public TO farmkonnect;
SQL

echo "=== [5/8] Running Migrations & Collectstatic ==="
sudo -u www-data "${VENV_DIR}/bin/python" "${BACKEND_DIR}/manage.py" migrate --noinput
sudo -u www-data "${VENV_DIR}/bin/python" "${BACKEND_DIR}/manage.py" collectstatic --noinput

echo "=== [6/8] Installing Systemd Service ==="
sudo cp "${APP_DIR}/deploy/systemd/farmkonnect.service" /etc/systemd/system/farmkonnect.service
sudo systemctl daemon-reload
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl enable farmkonnect
sudo systemctl restart farmkonnect

echo "=== [7/8] Configuring Nginx Reverse Proxy ==="
sudo cp "${APP_DIR}/deploy/nginx/farmkonnect.conf" /etc/nginx/sites-available/farmkonnect
sudo ln -sf /etc/nginx/sites-available/farmkonnect /etc/nginx/sites-enabled/farmkonnect
# Remove default nginx site if present
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
sudo systemctl reload nginx

echo "=== [8/8] Let's Encrypt TLS Certificate Provisioning ==="
echo "Acquiring TLS certificates for ${DOMAIN} and ${WWW_DOMAIN}..."
sudo certbot --nginx --non-interactive --agree-tos --redirect \
    -m "admin@zirocreativeagency.co.ke" \
    -d "${DOMAIN}" \
    -d "${WWW_DOMAIN}"

sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

echo "=============================================================================="
echo "Deployment Complete! FarmKonnect is live at: https://${DOMAIN}"
echo "=============================================================================="

#!/usr/bin/env bash
# ==============================================================================
# FarmKonnect Backup and Rollback Snapshot Utility
# Creates atomic point-in-time snapshots of database, nginx config, and environment
# ==============================================================================

set -euo pipefail

BACKUP_DIR="/var/backups/farmkonnect"
DATE=$(date +%Y-%m-%d_%H%M%S)

sudo mkdir -p "${BACKUP_DIR}"

echo "=== Taking Point-in-Time Backup: ${DATE} ==="

# 1. Database backup (PostgreSQL if running, or SQLite snapshot)
if command -v pg_dump >/dev/null 2>&1 && sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw farmkonnect; then
    echo "Dumping PostgreSQL database 'farmkonnect'..."
    sudo -u postgres pg_dump farmkonnect | gzip > "${BACKUP_DIR}/db-${DATE}.sql.gz"
fi

if [ -f "/var/www/farmkonnect/backend/db.sqlite3" ]; then
    echo "Backing up SQLite database..."
    cp "/var/www/farmkonnect/backend/db.sqlite3" "${BACKUP_DIR}/sqlite-${DATE}.db"
fi

# 2. Nginx configuration backup
if [ -f "/etc/nginx/sites-available/farmkonnect" ]; then
    echo "Backing up Nginx configuration..."
    cp "/etc/nginx/sites-available/farmkonnect" "${BACKUP_DIR}/nginx-${DATE}.conf.bak"
fi

# 3. Environment configuration backup
if [ -f "/var/www/farmkonnect/backend/.env" ]; then
    echo "Backing up .env configuration..."
    cp "/var/www/farmkonnect/backend/.env" "${BACKUP_DIR}/env-${DATE}.bak"
    chmod 600 "${BACKUP_DIR}/env-${DATE}.bak"
fi

echo "Backup complete! Files stored in ${BACKUP_DIR}/"
ls -lh "${BACKUP_DIR}"/*"${DATE}"*

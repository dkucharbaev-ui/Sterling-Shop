#!/bin/bash
set -e

# ==============================================================================
# PSYCHO STARS - AUTOMATED POSTGRESQL BACKUP SCRIPT
# ==============================================================================

BACKUP_DIR="/var/backups/psychostars"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/psychostars_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=14

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting PostgreSQL backup..."
docker exec -t psycho_stars_postgres pg_dump -U psychouser -d psychostars | gzip > "${BACKUP_FILE}"

echo "[$(date)] Backup completed: ${BACKUP_FILE} ($(du -sh "${BACKUP_FILE}" | cut -f1))"

# Prune old backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -type f -name "psychostars_*.sql.gz" -mtime +${RETENTION_DAYS} -exec rm {} \;
echo "[$(date)] Old backups older than ${RETENTION_DAYS} days pruned."

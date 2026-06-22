#!/usr/bin/env bash
# Elite Fintech Systems — PostgreSQL backup (VPS / Railway / Neon)
#
# Usage:
#   export DATABASE_URL="postgresql://user:pass@host:5432/elite_fintech"
#   ./scripts/backup-db.sh
#
# Optional:
#   BACKUP_DIR=/var/backups/elite RETENTION_DAYS=30 ./scripts/backup-db.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTFILE="${BACKUP_DIR}/elite-fintech-${STAMP}.sql.gz"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set" >&2
  exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump not found — install postgresql-client" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
echo "Backing up to ${OUTFILE} ..."
pg_dump "${DATABASE_URL}" --no-owner --no-acl | gzip -9 > "${OUTFILE}"
echo "Backup complete ($(du -h "${OUTFILE}" | cut -f1))"

if [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]] && [[ "${RETENTION_DAYS}" -gt 0 ]]; then
  find "${BACKUP_DIR}" -name 'elite-fintech-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
  echo "Pruned backups older than ${RETENTION_DAYS} days"
fi

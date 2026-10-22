#!/bin/sh
set -e
TS=$(date +%Y%m%d_%H%M%S)
DUMP="/tmp/ucalc_${TS}.sql.gz"
REMOTE="/ucalc_backups/db/ucalc_${TS}.sql.gz"

export PGPASSWORD="$DB_PASSWORD"
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$DUMP"
echo "[$(date)] Dump: $DUMP ($(du -h "$DUMP" | cut -f1))"

# Яндекс-Диск
curl -s -X PUT -H "Authorization: OAuth $YADISK_TOKEN" \
    "https://cloud-api.yandex.net/v1/disk/resources?path=/ucalc_backups" -o /dev/null || true
curl -s -X PUT -H "Authorization: OAuth $YADISK_TOKEN" \
    "https://cloud-api.yandex.net/v1/disk/resources?path=/ucalc_backups/db" -o /dev/null || true

UPLOAD_URL=$(curl -s -G -H "Authorization: OAuth $YADISK_TOKEN" \
    --data-urlencode "path=$REMOTE" --data-urlencode "overwrite=true" \
    "https://cloud-api.yandex.net/v1/disk/resources/upload" \
    | sed -n 's/.*"href":"\([^"]*\)".*/\1/p')

curl -s -X PUT -T "$DUMP" "$UPLOAD_URL"
echo "[$(date)] Uploaded: $REMOTE"
rm -f "$DUMP"

# Оставить последние 5 бэкапов
curl -s -G -H "Authorization: OAuth $YADISK_TOKEN" \
    --data-urlencode "path=/ucalc_backups/db" --data-urlencode "limit=200" \
    "https://cloud-api.yandex.net/v1/disk/resources" \
    | grep -o '"path":"[^"]*\.sql\.gz"' | sed 's/"path":"//;s/"$//' \
    | sort -r | tail -n +6 | while read -r P; do
        curl -s -X DELETE -G -H "Authorization: OAuth $YADISK_TOKEN" \
            --data-urlencode "path=$P" --data-urlencode "permanently=false" \
            "https://cloud-api.yandex.net/v1/disk/resources" -o /dev/null
        echo "[$(date)] Deleted: $P"
    done

echo "[$(date)] Backup finished"
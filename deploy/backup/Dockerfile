FROM postgres:16-alpine
RUN apk add --no-cache bash age rclone
COPY backup.sh restore.sh restore-drill.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/backup.sh /usr/local/bin/restore.sh /usr/local/bin/restore-drill.sh
ENTRYPOINT ["backup.sh"]

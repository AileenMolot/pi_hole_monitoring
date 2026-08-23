#!/usr/bin/env sh
set -eu

backup_dir="${1:-./backups}"
timestamp="$(date +%Y%m%d-%H%M%S)"

case "$backup_dir" in
  /*) backup_path="$backup_dir" ;;
  *) backup_path="$(pwd)/$backup_dir" ;;
esac

mkdir -p "$backup_dir"

# The volume name is derived from the compose project name (pi-hole-monitoring)
# defined in docker-compose.yml and the volume name (grafana-data).
# If you rename the compose project, update this accordingly.
docker run --rm \
  -v pi-hole-monitoring_grafana-data:/grafana-data:ro \
  -v "$backup_path:/backup" \
  alpine:3.20 \
  sh -c "tar czf /backup/grafana-data-$timestamp.tgz -C /grafana-data ."

printf 'Created %s/grafana-data-%s.tgz\n' "$backup_dir" "$timestamp"

# Keep only the 7 most recent backups to avoid filling the disk.
find "$backup_dir" -maxdepth 1 -name 'grafana-data-*.tgz' | sort -r | tail -n +8 | xargs -r rm -f

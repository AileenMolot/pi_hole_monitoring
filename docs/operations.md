# Operations Guide

## First Deployment

### 1. Install Docker

```sh
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for the group change to take effect
```

### 2. Clone the repository

```sh
git clone https://github.com/AileenMolot/pi_hole_monitoring.git
cd pi_hole_monitoring
```

### 3. Create and configure `.env`

```sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` and set at minimum:

```env
PIHOLE_HOSTNAME=192.168.1.10   # your Pi-hole IP or hostname
PIHOLE_API_TOKEN=...           # from Pi-hole Settings → API / Web interface
GRAFANA_ADMIN_PASSWORD=...     # long random string
GRAFANA_SECRET_KEY=...         # generate: openssl rand -base64 32
```

### 4. Validate configuration

```sh
./scripts/validate-config.sh
```

Fix any errors before continuing.

### 5. Start the stack

```sh
docker compose up -d
```

### 6. Verify everything is healthy

```sh
./scripts/check-stack.sh
```

Open Grafana at `http://127.0.0.1:3000` and log in with the admin credentials from `.env`.

### 7. Configure an alert receiver

Edit `alertmanager/alertmanager.yml` and add a real notification receiver. See [configuration.md](configuration.md) for examples.

---

## Day-to-Day Operations

### Check stack status

```sh
docker compose ps
./scripts/check-stack.sh
```

### View logs

```sh
# All services
docker compose logs -f

# Single service
docker compose logs -f grafana
docker compose logs -f prometheus
docker compose logs -f pihole-exporter
```

### Reload Alertmanager config without restarting

After editing `alertmanager/alertmanager.yml`:

```sh
docker compose kill -s SIGHUP alertmanager
```

### Reload Prometheus config without restarting

After editing `prometheus/prometheus.yml` or `prometheus/alerts.yml`:

```sh
docker compose kill -s SIGHUP prometheus
```

### Restart a single service

```sh
docker compose restart grafana
```

### Stop the stack

```sh
docker compose down
```

Data volumes are preserved. To also remove volumes (destructive — all metrics and Grafana state are lost):

```sh
docker compose down -v
```

---

## Backups

### Create a backup

```sh
./scripts/backup-grafana.sh
```

Backups are saved to `./backups/` by default. Pass a custom path as the first argument:

```sh
./scripts/backup-grafana.sh /mnt/nas/grafana-backups
```

The script keeps the 7 most recent archives and removes older ones automatically.

### What is backed up

- Grafana volume (`grafana-data`): user preferences, annotations, manually created dashboards and datasources, alert notification history, and session data

The following do **not** need to be backed up because they are version-controlled in the repository:
- Provisioned dashboards (`grafana/dashboards/`)
- Datasource config (`grafana/provisioning/`)
- Prometheus rules (`prometheus/alerts.yml`)
- Alertmanager config (`alertmanager/alertmanager.yml`)

Prometheus metrics (`prometheus-data`) are not backed up by default. They are ephemeral by design — the stack will rebuild its metric history as time passes after a restore.

### Restore a Grafana backup

Stop Grafana, restore the volume from a backup archive, then restart:

```sh
docker compose stop grafana

docker run --rm \
  -v pi-hole-monitoring_grafana-data:/grafana-data \
  -v "$(pwd)/backups:/backup:ro" \
  alpine:3.20 \
  sh -c "rm -rf /grafana-data/* && tar xzf /backup/grafana-data-TIMESTAMP.tgz -C /grafana-data"

docker compose start grafana
```

Replace `TIMESTAMP` with the filename of the archive you want to restore.

---

## Upgrades

### Upgrade container images

1. Update image tags in `docker-compose.yml` (e.g. `grafana/grafana:13.0.2` → `grafana/grafana:13.1.0`)
2. Validate: `./scripts/validate-config.sh`
3. Back up Grafana before upgrading: `./scripts/backup-grafana.sh`
4. Pull and restart:

```sh
docker compose pull
docker compose up -d
```

5. Verify: `./scripts/check-stack.sh`

### Update alert rules or Prometheus config

1. Edit `prometheus/alerts.yml` or `prometheus/prometheus.yml`
2. Validate: `./scripts/validate-config.sh`
3. Reload without restarting: `docker compose kill -s SIGHUP prometheus`
4. Check `Status > Rules` and `Status > Targets` in the Prometheus UI

### Update Grafana dashboards

1. Edit the JSON files in `grafana/dashboards/`
2. Restart Grafana to pick up the changes: `docker compose restart grafana`

---

## Remote Access

The stack binds to `127.0.0.1` by default. Prometheus and Alertmanager have no built-in authentication, so exposing them directly on a network is not recommended.

### SSH tunnel (recommended)

From your local machine:

```sh
ssh -L 3000:127.0.0.1:3000 \
    -L 9090:127.0.0.1:9090 \
    -L 9093:127.0.0.1:9093 \
    pi@<raspberry-pi-ip>
```

Then open `http://127.0.0.1:3000` locally.

### LAN access (less secure)

To make the UIs accessible on the local network without a tunnel:

```env
MONITORING_BIND_ADDRESS=0.0.0.0
```

Note that Prometheus and Alertmanager will be accessible without authentication to anyone on the LAN. Use firewall rules to restrict access if needed.

### Reverse proxy with authentication

If exposing Grafana over HTTPS via a reverse proxy (nginx, Caddy, Traefik):

1. Set `GRAFANA_ROOT_URL` to the public URL (e.g. `https://grafana.home.example.com`)
2. Set `GRAFANA_COOKIE_SECURE=true`
3. Keep Prometheus and Alertmanager on `127.0.0.1` and proxy only Grafana, or add authentication at the proxy level for the other UIs

---

## Troubleshooting

### Prometheus target is down

1. Open `http://127.0.0.1:9090/targets` and check the error message
2. For `raspberry-pi` target: check that Node Exporter is running (`docker compose ps node-exporter`) and that `host.docker.internal` resolves from within the Prometheus container. If it does not, replace `host.docker.internal:9100` in `prometheus/prometheus.yml` with the Pi's LAN IP
3. For `pihole` target: check Pi-hole Exporter logs (`docker compose logs pihole-exporter`) and verify `PIHOLE_HOSTNAME` and `PIHOLE_API_TOKEN` are correct in `.env`

### Grafana shows "No data"

1. Confirm Prometheus is running and targets are healthy
2. Open the Grafana datasource settings (Connections → Data sources → Prometheus) and click **Save & test**
3. Check that the dashboard time range includes a period when data was being collected

### Grafana sessions expire on every restart

`GRAFANA_SECRET_KEY` is missing or was not set. Without it Grafana generates a new random key each time it starts, which invalidates all cookies. Add a fixed key to `.env`:

```sh
echo "GRAFANA_SECRET_KEY=$(openssl rand -base64 32)" >> .env
docker compose restart grafana
```

### Alerts are not being delivered

1. Run `./scripts/check-stack.sh` — it will warn if no notification receiver is configured
2. Open `http://127.0.0.1:9093` and check Alertmanager status
3. Verify `alertmanager/alertmanager.yml` has a real receiver with a `*_configs` block
4. After updating the config, reload: `docker compose kill -s SIGHUP alertmanager`
5. Check Alertmanager logs: `docker compose logs alertmanager`

### Pi-hole Exporter returns errors

1. Check logs: `docker compose logs pihole-exporter`
2. Confirm the Pi-hole API is reachable from the Pi: `curl "http://${PIHOLE_HOSTNAME}/admin/api.php?auth=${PIHOLE_API_TOKEN}"`
3. Confirm `PIHOLE_API_TOKEN` is correct — an invalid token returns `[]` from the Pi-hole API, which the exporter treats as an error
4. If Pi-hole uses HTTPS with a self-signed certificate, mount the CA cert into the exporter and set `PIHOLE_PROTOCOL=https`

### Disk is filling up

The most common cause is Prometheus TSDB growth. Options:

- Reduce `PROMETHEUS_RETENTION` in `.env` (e.g. `15d`) and restart Prometheus
- Increase available disk space
- Remove unused Docker images: `docker image prune -a`
- Check if Grafana backups are accumulating on the same partition: `ls -lh backups/`

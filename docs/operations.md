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
PIHOLE_PASSWORD=...            # Pi-hole app password (Settings → Web interface / API)
GRAFANA_ADMIN_PASSWORD=...     # long random string
GRAFANA_SECRET_KEY=...         # generate: openssl rand -base64 32
SIGNAL_NUMBER=+380...          # Signal account you will link in step 7
SIGNAL_RECIPIENTS=+380...      # who receives alerts (comma-separated)
HEALTHCHECKS_URL=...           # optional: healthchecks.io ping URL (5 min period, 10 min grace)
```

### 4. Validate configuration

```sh
./scripts/validate_config.py
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

### 7. Link Signal for alert delivery

`signal-api` must be linked to your Signal account once, as a secondary device (the same way Signal Desktop is linked). Its port is bound to localhost on the Pi, so tunnel it from your computer:

```sh
ssh -L 8080:127.0.0.1:8080 pi@<raspberry-pi-ip>
```

Open `http://127.0.0.1:8080/v1/qrcodelink?device_name=pi-monitoring`. In the Signal app, go to Settings → Linked devices → **+** and scan the QR code. The link is stored in the `signal-data` volume and survives restarts.

Send a test alert:

```sh
docker compose exec alertmanager amtool alert add TestAlert severity=info \
  --annotation=summary="Test alert from Pi monitoring" \
  --alertmanager.url=http://localhost:9093
```

It arrives on Signal after about 30 seconds (`group_wait`). If it doesn't, check `docker compose logs signal-bridge signal-api`.

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

## State and Recovery

There is no backup script, because everything that matters is in the repository or can be recreated:

- Dashboards, the datasource, alert rules and Alertmanager config are version-controlled and provisioned from this repository.
- `grafana-data` holds only UI state: preferences, stars, annotations, sessions. If it is lost or a Grafana upgrade breaks it, reset it and Grafana re-provisions everything on start:

```sh
docker compose stop grafana
docker compose rm -f grafana
docker volume rm pi-hole-monitoring_grafana-data
docker compose up -d grafana
```

- `prometheus-data` is metric history; it rebuilds as time passes.
- `signal-data` holds the linked Signal account. If it is lost, link Signal again (First Deployment, step 7).

---

## Upgrades

### Upgrade container images

1. Update image tags in `docker-compose.yml` (e.g. `grafana/grafana:13.0.2` → `grafana/grafana:13.1.0`)
2. Validate: `./scripts/validate_config.py`
3. Pull and restart:

```sh
docker compose pull
docker compose up -d
```

4. Verify: `./scripts/check-stack.sh`. If a Grafana upgrade leaves it broken, roll back the tag or reset its volume (see State and Recovery).

### Update alert rules or Prometheus config

1. Edit `prometheus/alerts.yml` or `prometheus/prometheus.yml`
2. Validate: `./scripts/validate_config.py`
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
3. For `pihole` target: check Pi-hole Exporter logs (`docker compose logs pihole-exporter`) and verify `PIHOLE_HOSTNAME` and `PIHOLE_PASSWORD` are correct in `.env`

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

1. Open `http://127.0.0.1:9093` and check Alertmanager status
2. Check bridge logs: `docker compose logs signal-bridge`. A `delivery failed` line means `signal-api` rejected the send; Alertmanager will retry.
3. Check `docker compose logs signal-api`. If the device link was removed in the Signal app, link it again (First Deployment, step 7).
4. Verify `SIGNAL_NUMBER` and `SIGNAL_RECIPIENTS` in `.env` use international format (`+380...`), then run `docker compose up -d signal-bridge`
5. Check Alertmanager logs: `docker compose logs alertmanager`

### Pi-hole Exporter returns errors

1. Check logs: `docker compose logs pihole-exporter`
2. Confirm the Pi-hole API accepts the password from the Pi (Pi-hole v6): `curl -s -X POST "http://${PIHOLE_HOSTNAME}/api/auth" -d "{\"password\":\"${PIHOLE_PASSWORD}\"}"`. A response containing `"valid":true` means the password works.
3. If it doesn't, create a new app password in Pi-hole (Settings → Web interface / API → Configure app password), put it in `PIHOLE_PASSWORD`, and run `docker compose up -d pihole-exporter`
4. If Pi-hole uses HTTPS with a self-signed certificate, mount the CA cert into the exporter and set `PIHOLE_PROTOCOL=https`

### Disk is filling up

The most common cause is Prometheus TSDB growth. Options:

- Reduce `PROMETHEUS_RETENTION` (e.g. `15d`) or `PROMETHEUS_RETENTION_SIZE` (e.g. `2GB`) in `.env`, then run `docker compose up -d prometheus`
- Increase available disk space
- Remove unused Docker images: `docker image prune -a`

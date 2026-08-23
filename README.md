# Raspberry Pi and Pi-hole Monitoring

Docker Compose monitoring stack for a Raspberry Pi 5 and an existing Pi-hole instance.

This project intentionally does not install or manage Pi-hole. It only collects metrics from the Raspberry Pi host and from a Pi-hole API endpoint.

## Stack

- Prometheus for metrics collection and alert rules
- Grafana for dashboards
- Node Exporter for Raspberry Pi host metrics
- Pi-hole Exporter for Pi-hole metrics
- Alertmanager for alert routing

Pinned container baselines are kept current in `docker-compose.yml`. Review and refresh them as part of regular maintenance.

## Requirements

- Raspberry Pi OS or another Linux host
- Docker Engine with Docker Compose
- Existing Pi-hole instance reachable from the Raspberry Pi
- Pi-hole API token

## Configure

Copy the example environment file and edit the values:

```sh
cp .env.example .env
```

Required values:

```env
MONITORING_BIND_ADDRESS=127.0.0.1
PIHOLE_HOSTNAME=192.168.1.10
PIHOLE_PROTOCOL=http
PIHOLE_PORT=80
PIHOLE_API_TOKEN=paste-real-token-here
GRAFANA_ADMIN_PASSWORD=use-a-long-random-password
GRAFANA_SECRET_KEY=generate-with-openssl-rand-base64-32
```

Generate `GRAFANA_SECRET_KEY` with:

```sh
openssl rand -base64 32
```

This key signs Grafana sessions. Without it, Grafana generates a random key at startup and all sessions are invalidated on every container restart.

`PIHOLE_HOSTNAME` should be a hostname or IP address only. Keep the protocol in `PIHOLE_PROTOCOL`.

`GRAFANA_ROOT_URL` defaults to `http://127.0.0.1:3000`. Set it to your Grafana URL if you want correct absolute links in alert notifications.

`.env` is ignored by Git because it contains secrets. Keep the Pi-hole API token and Grafana password out of commits, screenshots, and shared logs.

## Run

```sh
docker compose up -d
```

Open:

- Grafana: `http://127.0.0.1:3000`
- Prometheus: `http://127.0.0.1:9090`
- Alertmanager: `http://127.0.0.1:9093`

The monitoring web UIs bind to localhost by default. For remote access, prefer SSH tunneling, a VPN, or an authenticated reverse proxy. If you intentionally want direct LAN access, set:

```env
MONITORING_BIND_ADDRESS=0.0.0.0
```

Grafana is provisioned automatically with:

- `Raspberry Pi Resources`
- `Pi-hole Monitoring`

Provisioned dashboards cannot be deleted or edited from the UI. To modify them, edit the JSON files in `grafana/dashboards/` and restart Grafana.

## Check Health

Validate files before deploying:

```sh
./scripts/validate-config.sh
```

The validator checks:

- YAML syntax (requires PyYAML)
- JSON syntax
- Shell script syntax
- `docker compose config` (requires Docker)
- Prometheus config and alert rules (requires `promtool`)
- Whether `.env` exists
- Whether an Alertmanager notification receiver is configured

After the stack is running:

```sh
./scripts/check-stack.sh
```

This checks that Prometheus targets are healthy, Grafana is reachable, and Alertmanager is reachable. It also warns if no notification receiver has been configured.

In Prometheus, check `Status > Targets`. The expected jobs are:

- `prometheus`
- `raspberry-pi`
- `pihole`

## Alerts

Alert rules live in `prometheus/alerts.yml`.

Included alerts:

- Raspberry Pi Node Exporter down
- Pi-hole Exporter down
- high Raspberry Pi CPU load
- high memory usage
- disk usage above 85 percent
- recent Raspberry Pi reboot
- CPU temperature above 80°C
- sustained network interface errors
- no Pi-hole DNS query increase for 15 minutes
- very low Pi-hole block percentage

All alert descriptions include the actual metric value at the time of firing.

When Node Exporter or the Pi-hole Exporter goes down, Alertmanager suppresses derived alerts for the same source via inhibit rules, preventing alert storms from a single root cause.

Alertmanager is wired in but uses a placeholder receiver. Add your preferred receiver in `alertmanager/alertmanager.yml`, such as email, Telegram, ntfy, Gotify, or Slack.

## Backups

Grafana stores mutable UI changes in a Docker volume. Create a local backup with:

```sh
./scripts/backup-grafana.sh
```

The script keeps the 7 most recent backups and removes older ones automatically. Pass a custom path to change the backup directory:

```sh
./scripts/backup-grafana.sh /mnt/backup/grafana
```

The dashboards included in `grafana/dashboards/` are already version-controlled starter dashboards.

Grafana backups may contain users, session data, datasource metadata, and other operational information. Store them like secrets.

## Notes

Node Exporter uses host networking, host PID namespace, and a read-only host root mount so it can report Raspberry Pi host metrics instead of only container metrics. This is powerful by design, so expose port `9100` only on trusted networks and use host firewall rules if the Raspberry Pi is on a shared LAN.

Prometheus scrapes Node Exporter through `host.docker.internal:9100`. Modern Docker Engine on Linux supports this through the host gateway mapping in many setups, but if the Raspberry Pi cannot resolve it, replace that target in `prometheus/prometheus.yml` with the Raspberry Pi LAN IP, for example `192.168.1.20:9100`.

The Pi-hole scrape interval is set to 30 seconds to match the exporter poll interval. Scraping more frequently would return stale data.

Pi-hole Exporter is reachable only inside the Docker monitoring network by default. If Pi-hole uses HTTPS with a private certificate, mount trusted certificates into the exporter container and set `PIHOLE_PROTOCOL=https`.

## Security Defaults

- Prometheus and Alertmanager are bound to localhost by default.
- Pi-hole Exporter is not published to the host.
- Prometheus HTTP lifecycle reload is disabled.
- Alertmanager high-availability peer listening is disabled for this single-node stack.
- Containers drop Linux capabilities and use `no-new-privileges`.
- All containers use read-only root filesystems.
- Grafana sign-up, Gravatar, telemetry reporting, plugin update checks, and news feed are disabled.
- Grafana sessions are signed with a user-supplied secret key.
- Provisioned datasources and dashboards are locked against UI modification.
- Secrets live in `.env`, which is ignored by Git.

See `SECURITY.md` for the threat model, remaining risks, and deployment hardening checklist.

## Documentation

- [Architecture](docs/architecture.md) — component diagram, data flow, network layout, port summary
- [Configuration](docs/configuration.md) — all environment variables, Prometheus and Alertmanager config reference
- [Alerts](docs/alerts.md) — per-alert explanations and response runbooks
- [Operations](docs/operations.md) — deploy, backup, upgrade, remote access, troubleshooting

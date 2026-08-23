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
```

`PIHOLE_HOSTNAME` should be a hostname or IP address only. Keep the protocol in `PIHOLE_PROTOCOL`.

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

## Check Health

Validate files before deploying:

```sh
./scripts/validate-config.sh
```

The validator uses Python 3 for local checks. If PyYAML is installed, it also performs standalone YAML parsing. When Docker or `promtool` are available, it runs their native validation checks too.

After the stack is running:

```sh
./scripts/check-stack.sh
```

In Prometheus, check `Status > Targets`. The expected jobs are:

- `prometheus`
- `raspberry-pi`
- `pihole`

## Alerts

Alert rules live in `prometheus/alerts.yml`.

Included starter alerts:

- Raspberry Pi Node Exporter down
- Pi-hole Exporter down
- high Raspberry Pi CPU load
- high memory usage
- disk usage above 85 percent
- recent Raspberry Pi reboot
- no Pi-hole DNS query increase
- very low Pi-hole block percentage

Alertmanager is wired in but uses a placeholder receiver. Add your preferred receiver in `alertmanager/alertmanager.yml`, such as email, Telegram, ntfy, Gotify, or Slack.

## Backups

Grafana stores mutable UI changes in a Docker volume. Create a local backup with:

```sh
./scripts/backup-grafana.sh
```

The dashboards included in `grafana/dashboards/` are already version-controlled starter dashboards.

Grafana backups may contain users, session data, datasource metadata, and other operational information. Store them like secrets.

## Notes

Node Exporter uses host networking, host PID namespace, and a read-only host root mount so it can report Raspberry Pi host metrics instead of only container metrics. This is powerful by design, so expose port `9100` only on trusted networks and use host firewall rules if the Raspberry Pi is on a shared LAN.

Prometheus scrapes Node Exporter through `host.docker.internal:9100`. Modern Docker Engine on Linux supports this through the host gateway mapping in many setups, but if the Raspberry Pi cannot resolve it, replace that target in `prometheus/prometheus.yml` with the Raspberry Pi LAN IP, for example `192.168.1.20:9100`.

Pi-hole Exporter is reachable only inside the Docker monitoring network by default. If Pi-hole uses HTTPS with a private certificate, mount trusted certificates into the exporter container and set `PIHOLE_PROTOCOL=https`.

## Security Defaults

- Prometheus and Alertmanager are bound to localhost by default.
- Pi-hole Exporter is not published to the host.
- Prometheus HTTP lifecycle reload is disabled.
- Alertmanager high-availability peer listening is disabled for this single-node stack.
- Containers drop Linux capabilities and use `no-new-privileges`.
- Prometheus, Alertmanager, Pi-hole Exporter, and Node Exporter use read-only root filesystems.
- Grafana sign-up, Gravatar, and anonymous telemetry reporting are disabled.
- Secrets live in `.env`, which is ignored by Git.

See `SECURITY.md` for the threat model, remaining risks, and deployment hardening checklist.

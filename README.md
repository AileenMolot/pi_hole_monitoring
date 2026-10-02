# Raspberry Pi and Pi-hole Monitoring

Docker Compose monitoring stack for a Raspberry Pi 5 and an existing Pi-hole instance. It doesn't install or manage Pi-hole; it only reads metrics from the Pi host and the Pi-hole API.

- **Prometheus** collects metrics and evaluates alert rules
- **Grafana** shows two provisioned dashboards: Raspberry Pi Resources and Pi-hole Monitoring
- **Node Exporter** and **Pi-hole Exporter** expose the metrics
- **Alertmanager** sends alerts to **Signal** through `signal-api` and a small webhook bridge (`signal-bridge/bridge.py`)
- A **Watchdog** heartbeat can ping healthchecks.io, so you're told when the whole Pi goes down

## Requirements

- Raspberry Pi OS (or another Linux host) with Docker Engine and Docker Compose
- An existing Pi-hole reachable from the Pi, with an app password (v6) or API token (v5)
- A Signal account to link as a secondary device

## Quick start

```sh
cp .env.example .env && chmod 600 .env   # fill in the required values
./scripts/validate_config.py
docker compose up -d
./scripts/check-stack.sh
```

Then link Signal and send a test alert ([Operations, step 7](docs/operations.md#7-link-signal-for-alert-delivery)).

Grafana is at `http://127.0.0.1:3000`, Prometheus at `:9090` and Alertmanager at `:9093`. They're bound to localhost; use an SSH tunnel for remote access ([Operations → Remote Access](docs/operations.md#remote-access)).

## Documentation

- [Configuration](docs/configuration.md): `.env` and config files
- [Operations](docs/operations.md): deploy, Signal linking, upgrades, recovery, remote access, troubleshooting
- [Alerts](docs/alerts.md): what each alert means and how to respond
- [Architecture](docs/architecture.md): components, network layout, ports
- [Security](SECURITY.md): threat model, hardening, remaining risks

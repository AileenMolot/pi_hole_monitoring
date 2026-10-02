# Configuration Reference

## Environment

All runtime settings live in `.env`. [`.env.example`](../.env.example) lists every variable with a comment and marks the required ones. Copy it and fill it in:

```sh
cp .env.example .env
chmod 600 .env
```

Compose fails fast if a required variable is missing. After changing `.env`, run `docker compose up -d` to recreate the affected containers.

## Prometheus

`prometheus/prometheus.yml` scrapes every 15s and evaluates rules every 15s. The `pihole` job scrapes every 30s to keep load on the Pi-hole API low.

If `host.docker.internal` does not resolve on your host, replace the `raspberry-pi` target with the Pi's LAN IP (for example `192.168.1.20:9100`). In that case, set `NODE_EXPORTER_LISTEN_ADDRESS` to that same IP.

Reload after editing: `docker compose kill -s SIGHUP prometheus`.

## Alertmanager

`alertmanager/alertmanager.yml` sends every alert to the `signal` receiver, a webhook to `signal-bridge`. A child route repeats `Watchdog` every 5 minutes (instead of 4 hours) to keep the dead man's switch fed.

To add another channel (email, Telegram, ntfy…), add its `*_configs` block to the `signal` receiver; see the [Alertmanager receiver docs](https://prometheus.io/docs/alerting/latest/configuration/#receiver-integration-settings).

Reload after editing: `docker compose kill -s SIGHUP alertmanager`.

## Grafana

The datasource (`grafana/provisioning/datasources/prometheus.yml`) and both dashboards (`grafana/dashboards/*.json`) are provisioned from the repository and locked against UI edits. To change a dashboard, edit its JSON and run `docker compose restart grafana`.

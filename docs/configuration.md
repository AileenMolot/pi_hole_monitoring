# Configuration Reference

All runtime configuration lives in `.env`. Copy `.env.example` to `.env` and fill in the values before running the stack.

```sh
cp .env.example .env
chmod 600 .env
```

## Environment Variables

### General

| Variable | Default | Required | Description |
|---|---|---|---|
| `TZ` | `Europe/Kiev` | No | Timezone used by Grafana for dashboard display. |
| `MONITORING_BIND_ADDRESS` | `127.0.0.1` | No | IP address that Grafana, Prometheus, and Alertmanager bind to. Use `127.0.0.1` (localhost only) or `0.0.0.0` (all interfaces, LAN-accessible). |

### Pi-hole

| Variable | Default | Required | Description |
|---|---|---|---|
| `PIHOLE_HOSTNAME` | — | **Yes** | Hostname or IP address of the existing Pi-hole instance. Do not include a protocol prefix. |
| `PIHOLE_PROTOCOL` | `http` | No | Protocol used to reach Pi-hole: `http` or `https`. |
| `PIHOLE_PORT` | `80` | No | Port Pi-hole's web interface listens on. |
| `PIHOLE_API_TOKEN` | — | **Yes** | Pi-hole API token. Find it in Pi-hole Settings → API / Web interface → Show API token. |
| `PIHOLE_EXPORTER_INTERVAL` | `30s` | No | How often Pi-hole Exporter polls the Pi-hole API. The Prometheus scrape interval for the `pihole` job is set to match this value. |

### Grafana

| Variable | Default | Required | Description |
|---|---|---|---|
| `GRAFANA_PORT` | `3000` | No | Host port Grafana listens on. |
| `GRAFANA_ADMIN_USER` | `admin` | No | Grafana admin username. |
| `GRAFANA_ADMIN_PASSWORD` | — | **Yes** | Grafana admin password. Use a long random string. |
| `GRAFANA_SECRET_KEY` | — | **Yes** | Key used to sign Grafana sessions and cookies. Generate with `openssl rand -base64 32`. Without a fixed key, Grafana generates one at startup and invalidates all sessions on every container restart. |
| `GRAFANA_ROOT_URL` | `http://127.0.0.1:3000` | No | Absolute URL of the Grafana instance. Used for links in alert notifications. Change this if Grafana is accessed through a reverse proxy or at a non-default address. |
| `GRAFANA_COOKIE_SECURE` | `false` | No | Set to `true` when Grafana is served over HTTPS to mark session cookies as Secure. |

### Prometheus

| Variable | Default | Required | Description |
|---|---|---|---|
| `PROMETHEUS_PORT` | `9090` | No | Host port Prometheus listens on. |
| `PROMETHEUS_RETENTION` | `30d` | No | How long Prometheus keeps metrics. Accepts durations like `15d`, `90d`. Older data is deleted automatically. |

### Alertmanager

| Variable | Default | Required | Description |
|---|---|---|---|
| `ALERTMANAGER_PORT` | `9093` | No | Host port Alertmanager listens on. |

### Node Exporter

| Variable | Default | Required | Description |
|---|---|---|---|
| `NODE_EXPORTER_LISTEN_ADDRESS` | `0.0.0.0:9100` | No | Address Node Exporter binds to. Defaults to all interfaces because Node Exporter uses host networking and Prometheus reaches it via `host.docker.internal`. Change to a specific LAN IP to reduce exposure on multi-homed hosts. |

## Prometheus Configuration

`prometheus/prometheus.yml` is mounted read-only into the Prometheus container. Key settings:

- `scrape_interval: 15s` — global default scrape frequency
- `evaluation_interval: 15s` — how often alert rules are evaluated
- `external_labels.instance: raspberry-pi-monitoring` — label attached to all metrics and alerts from this Prometheus instance; useful if alerts are routed to a shared Alertmanager or a remote write target
- The `pihole` job overrides `scrape_interval: 30s` and `scrape_timeout: 25s` to match the exporter poll interval

If `host.docker.internal` does not resolve on your host, replace it in `prometheus/prometheus.yml` with the Raspberry Pi's LAN IP:

```yaml
- job_name: raspberry-pi
  static_configs:
    - targets:
        - 192.168.1.20:9100   # replace with actual Pi IP
```

## Alertmanager Configuration

`alertmanager/alertmanager.yml` controls how alerts are grouped and delivered.

The stack ships with a `default-log` placeholder receiver. Alerts will not be delivered until a real receiver is added. Example configurations:

**Email**
```yaml
receivers:
  - name: default-log
    email_configs:
      - to: you@example.com
        from: alertmanager@example.com
        smarthost: smtp.example.com:587
        auth_username: you@example.com
        auth_password: your-smtp-password
```

**Telegram**
```yaml
receivers:
  - name: default-log
    telegram_configs:
      - bot_token: your-bot-token
        chat_id: 123456789
```

**ntfy**
```yaml
receivers:
  - name: default-log
    webhook_configs:
      - url: https://ntfy.sh/your-topic
```

After editing `alertmanager/alertmanager.yml`, reload Alertmanager without restarting the stack:

```sh
docker compose kill -s SIGHUP alertmanager
```

## Grafana Provisioning

Grafana is provisioned automatically from files in `grafana/`:

```
grafana/
  provisioning/
    datasources/
      prometheus.yml   # Prometheus datasource (locked, not editable from UI)
    dashboards/
      dashboards.yml   # Dashboard provider config
  dashboards/
    raspberry-pi.json  # Raspberry Pi Resources dashboard
    pihole.json        # Pi-hole Monitoring dashboard
```

Provisioned dashboards and datasources cannot be modified from the Grafana UI. To update a dashboard, edit the JSON file and restart Grafana:

```sh
docker compose restart grafana
```

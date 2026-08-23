# Architecture

## Overview

The stack runs entirely in Docker Compose on the Raspberry Pi. It does not touch Pi-hole — it only reads from Pi-hole's HTTP API via a dedicated exporter container.

## Component Diagram

```
                        ┌─────────────────────────────────────┐
                        │          Raspberry Pi host          │
                        │                                     │
  ┌──────────┐          │  ┌─────────────┐  ┌─────────────┐  │
  │ Pi-hole  │◄─────────┼──│pihole-      │  │node-        │  │
  │ (any     │  HTTP/   │  │exporter     │  │exporter     │  │
  │  host)   │  API     │  │:9617        │  │:9100        │  │
  └──────────┘          │  └──────┬──────┘  └──────┬──────┘  │
                        │         │                 │         │
                        │  ┌──────▼─────────────────▼──────┐  │
                        │  │         Prometheus             │  │
                        │  │         :9090                  │  │
                        │  │  scrapes, evaluates rules      │  │
                        │  └──────┬──────────────┬─────────┘  │
                        │         │              │             │
                        │  ┌──────▼──────┐ ┌────▼──────────┐  │
                        │  │  Grafana    │ │ Alertmanager  │  │
                        │  │  :3000      │ │ :9093         │  │
                        │  │  dashboards │ │ routing       │  │
                        │  └─────────────┘ └───────────────┘  │
                        │                                     │
                        └─────────────────────────────────────┘
                                        │
                               browser (localhost
                               or SSH tunnel)
```

## Components

### Prometheus
Collects metrics on a configurable scrape interval (default 15s, 30s for Pi-hole). Evaluates alert rules every 15 seconds and forwards firing alerts to Alertmanager. Retains data for 30 days by default.

### Grafana
Reads from Prometheus via the provisioned datasource. Ships two pre-built dashboards. All provisioning is file-based — datasources and dashboards are locked against UI modification so the repository stays the source of truth.

### Node Exporter
Runs with host networking and the host PID namespace so it can report real Raspberry Pi hardware metrics (CPU, memory, disk, temperature, network) rather than container-scoped metrics. Mounts the host root filesystem read-only at `/host`.

### Pi-hole Exporter
Polls the Pi-hole HTTP API at a configurable interval (default 30s) and exposes the results as Prometheus metrics. Runs inside the Docker monitoring network and is not published to the host.

### Alertmanager
Receives alerts from Prometheus, groups them, applies inhibit rules, and routes them to a configured receiver. Ships with a `default-log` placeholder receiver — alerts are not delivered until a real receiver is added.

## Network Layout

```
Docker network: pi-monitoring
  prometheus
  grafana
  pihole-exporter
  alertmanager

Host network (node-exporter only):
  node-exporter — listens on 0.0.0.0:9100 by default
```

Node Exporter uses host networking so it sees the actual host interfaces and processes. Prometheus reaches it via `host.docker.internal:9100`, which resolves to the host gateway on modern Docker Engine on Linux.

Pi-hole Exporter sits inside the monitoring network and is not exposed to the host or LAN. It initiates outbound connections to Pi-hole — the only component that needs to reach an external host.

## Data Flow

```
1. Node Exporter reads /proc, /sys, and /host on the Raspberry Pi host
2. Pi-hole Exporter polls Pi-hole API (HTTP or HTTPS)
3. Prometheus scrapes Node Exporter and Pi-hole Exporter on schedule
4. Prometheus evaluates alert rules every evaluation_interval
5. Firing alerts are sent to Alertmanager
6. Alertmanager applies grouping, inhibition, and silences
7. Alertmanager forwards alerts to the configured receiver
8. Grafana queries Prometheus on demand when a dashboard is viewed
```

## Persistence

| Volume | Contents |
|---|---|
| `prometheus-data` | TSDB metrics (30-day retention by default) |
| `grafana-data` | Grafana database, plugins, user preferences |
| `alertmanager-data` | Alert state, silences |

Grafana dashboards and datasource config are provisioned from `grafana/` in the repository and are not stored in the volume. Only UI state (preferences, silences, annotations, manually created objects) lives in the volumes.

## Port Summary

| Port | Service | Bound to |
|---|---|---|
| 3000 | Grafana | `MONITORING_BIND_ADDRESS` (default `127.0.0.1`) |
| 9090 | Prometheus | `MONITORING_BIND_ADDRESS` (default `127.0.0.1`) |
| 9093 | Alertmanager | `MONITORING_BIND_ADDRESS` (default `127.0.0.1`) |
| 9100 | Node Exporter | `NODE_EXPORTER_LISTEN_ADDRESS` (default `0.0.0.0`) |
| 9617 | Pi-hole Exporter | internal Docker network only |

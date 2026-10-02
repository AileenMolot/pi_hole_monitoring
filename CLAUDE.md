# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Docker Compose monitoring stack for a Raspberry Pi 5 host and an existing, externally-managed Pi-hole instance. This repo does not install or run Pi-hole itself — it only scrapes metrics from a Pi-hole API endpoint and from the host. There is no application code to build or test; the repo is entirely declarative config (Compose, Prometheus, Alertmanager, Grafana provisioning/dashboards) plus a few POSIX shell/Python scripts.

## Commands

Validate all config before deploying (YAML/JSON syntax, shell syntax, `docker compose config`, `promtool` checks if installed, `.env` presence, Alertmanager receiver presence):

```sh
./scripts/validate-config.sh
```

This just execs `scripts/validate_config.py` — edit that file directly when changing validation logic.

Start/stop the stack:

```sh
docker compose up -d
docker compose down
```

Check a running stack's health (Prometheus targets, Grafana, Alertmanager reachability, warns if no Alertmanager receiver configured):

```sh
./scripts/check-stack.sh
```

There are no unit tests. "Testing" a change means running `validate-config.sh`, then `docker compose up -d` and `check-stack.sh` against a real or test Pi-hole.

## Architecture

Seven containers on one `pi-monitoring` Docker network (`docker-compose.yml`), wired as:

- **node-exporter** — runs with `network_mode: host`, `pid: host`, and a read-only `/:/host` bind mount to report real host metrics (not container metrics). This is the one component with an intentionally expanded trust boundary; it listens on the `docker0` IP (`172.17.0.1:9100`) by default so it isn't on the LAN; don't widen that without a firewall.
- **pihole-exporter** (`ekofr/pihole-exporter`) — polls the existing Pi-hole's API using `PIHOLE_HOSTNAME`/`PIHOLE_PROTOCOL`/`PIHOLE_PORT`/`PIHOLE_PASSWORD` from `.env`. Reachable only inside the Docker network, never published to the host.
- **prometheus** — scrapes `raspberry-pi` (`host.docker.internal:9100`, via the `host-gateway` extra_hosts mapping), `pihole` (`pihole-exporter:9617`, 30s interval to match the exporter's own poll interval — don't scrape faster, it'll just return stale data), and itself. Alert rules live in `prometheus/alerts.yml`; `--web.enable-lifecycle` is deliberately not enabled.
- **alertmanager** — receives alerts from Prometheus and posts them as webhooks to `signal-bridge` (the `signal` receiver). A child route sends the always-firing `Watchdog` alert every 5m as a dead man's switch heartbeat. Has inhibit rules so an exporter-down alert suppresses all alerts derived from that same exporter, preventing storms.
- **signal-bridge** — `signal-bridge/bridge.py`, a stdlib-only Python script in a pinned `python:*-alpine` image. It turns Alertmanager webhooks into `/v2/send` calls to `signal-api`, and for `Watchdog` calls `/v1/receive` (proves the Signal link works) then pings `HEALTHCHECKS_URL` instead of messaging. It returns 502 on failure so Alertmanager retries.
- **signal-api** (`bbernhard/signal-cli-rest-api`) — holds the linked Signal account in the `signal-data` volume. Port bound to `127.0.0.1` only, for the one-time QR linking page.
- **grafana** — auto-provisioned from `grafana/provisioning/` (datasource pointing at `prometheus:9090`, dashboard provider pointing at `grafana/dashboards/`). Provisioned datasources/dashboards are locked (`editable: false`, `allowUiUpdates: false`) — to change a dashboard, edit the JSON in `grafana/dashboards/` (`pihole.json`, `raspberry-pi.json`) and restart Grafana, not the UI.

All services other than node-exporter and signal-api (whose entrypoint needs a writable root and capabilities): `read_only: true` root filesystem + `tmpfs: /tmp`, `cap_drop: ALL`, `no-new-privileges`. Every service uses the shared `logging: *logging` anchor (size-capped json-file logs). Preserve these when editing `docker-compose.yml`.

Everything is driven by `.env` (copied from `.env.example`), with Compose defaults as fallback (`${VAR:-default}`) and hard failures for required secrets (`${VAR:?set VAR in .env}`) — `PIHOLE_HOSTNAME`, `PIHOLE_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_SECRET_KEY`, `SIGNAL_NUMBER`, `SIGNAL_RECIPIENTS`. `MONITORING_BIND_ADDRESS` (default `127.0.0.1`) controls whether Grafana/Prometheus/Alertmanager ports are exposed beyond localhost.

## Conventions to preserve when editing

- Container image tags are pinned (no `latest`); bump deliberately, not incidentally.
- New alert rules in `prometheus/alerts.yml` should include the live metric value in their `description` annotation (via `{{ $value | humanize... }}`), matching the existing style.
- If you add a scrape job, exporter, or alert that can itself go down, add a corresponding Alertmanager `inhibit_rules` entry so it suppresses its own derived alerts, as done for `RaspberryPiExporterDown` and `PiholeExporterDown`.
- `scripts/validate_config.py` globs `*.yml`/`*.json`/`*.sh`/`*.py` across the repo (skipping hidden dirs), so new files are checked automatically. Use the `.yml` extension, not `.yaml`.
- `prometheus.yml` references `alerts.yml` relatively so `promtool check config` works outside the container.
- Security posture (localhost binding, read-only filesystems, dropped capabilities, no public exposure) is treated as a first-class concern here — see `SECURITY.md` before loosening any of it, and update `SECURITY.md` if you do.

## Docs

- `docs/architecture.md` — component diagram, data flow, network layout, port summary
- `docs/configuration.md` — full environment variable and config reference
- `docs/alerts.md` — per-alert explanations and response runbooks
- `docs/operations.md` — deploy, recovery, upgrade, remote access, troubleshooting
- `SECURITY.md` — threat model, hardening applied, remaining risks, maintenance checklist

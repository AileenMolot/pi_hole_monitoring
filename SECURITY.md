# Security Notes

This project monitors a Raspberry Pi and an existing Pi-hole instance. It does not install Pi-hole and should not be exposed directly to the public internet.

## Main Threats

- Unauthorized access to Grafana, Prometheus, or Alertmanager.
- Leakage of the Pi-hole password or Grafana secret key from `.env`, shell history, or Docker metadata.
- Overexposure of host metrics through Node Exporter.
- Running outdated container images with known CVEs.
- Misuse of the linked Signal account through `signal-api`.

## Hardening Applied

- Grafana, Prometheus, and Alertmanager bind to `127.0.0.1` by default through `MONITORING_BIND_ADDRESS`.
- Pi-hole Exporter is only reachable on the internal Docker network.
- Prometheus `--web.enable-lifecycle` is not enabled.
- Alertmanager peer clustering is disabled with `--cluster.listen-address=` for this single-node deployment.
- Containers drop all Linux capabilities where practical (all except `signal-api`).
- Containers use `no-new-privileges`.
- All containers except `signal-api` use read-only root filesystems with `tmpfs` mounts for writable scratch space.
- `signal-bridge` runs as `nobody` (UID 65534).
- Container logs are size-capped, and Prometheus storage is capped by `PROMETHEUS_RETENTION_SIZE`, so neither can fill the disk.
- Grafana sign-up, Gravatar, update checks, plugin update checks, news feed, and telemetry reporting are disabled.
- Grafana sessions are signed with a user-supplied `GRAFANA_SECRET_KEY`, preventing session forgery and invalidation on restart.
- Provisioned Grafana datasources are locked (`editable: false`) and provisioned dashboards cannot be deleted or modified from the UI.
- Required secrets fail fast if `.env` is missing or incomplete.
- `.env` is ignored by Git.
- Container image tags are pinned instead of using `latest`.
- Prometheus `external_labels` identify this instance in Alertmanager routing.

## Remaining Risks

### Node Exporter

Node Exporter uses host networking, the host PID namespace, and a read-only host root mount. This is the standard pattern for accurate Linux host metrics from a container, but it is a deliberate trust boundary expansion.

Mitigations:

- `NODE_EXPORTER_LISTEN_ADDRESS` defaults to the `docker0` bridge IP (`172.17.0.1:9100`), so port `9100` is reachable from containers and the host but not from the LAN.
- Do not change it to `0.0.0.0` unless you also restrict port `9100` with host firewall rules.

### Pi-hole Password and Grafana Secret Key

The Pi-hole exporter and Grafana both read secrets from environment variables. Any local user with Docker access can generally inspect container environment variables, so Docker access should be treated as privileged.

Mitigations:

- Keep `.env` permissions tight: `chmod 600 .env`.
- Do not commit `.env`.
- Do not share `docker inspect` output publicly.
- Rotate the Pi-hole app password if it is exposed.
- Rotate `GRAFANA_SECRET_KEY` if it is exposed (this will invalidate all active Grafana sessions).

### Web UI Access

Grafana has authentication, but Prometheus and Alertmanager do not provide strong built-in auth in this Compose stack.

Mitigations:

- Keep `MONITORING_BIND_ADDRESS=127.0.0.1` unless behind a VPN, SSH tunnel, or authenticated reverse proxy.
- If exposing Grafana over HTTPS, set `GRAFANA_COOKIE_SECURE=true`.
- Use a long random Grafana admin password.
- Use a long random `GRAFANA_SECRET_KEY` (generate with `openssl rand -base64 32`).

### Signal API

`signal-api` holds the keys of a Signal account linked as a secondary device, and its REST API can send messages as that account without authentication. Its entrypoint adjusts users and file ownership at startup, so it runs without `read_only` or `cap_drop` (it keeps `no-new-privileges`).

Mitigations:

- Its port is published on `127.0.0.1` only (for the one-time QR linking page), regardless of `MONITORING_BIND_ADDRESS`; inside Docker it is reachable only on the monitoring network.
- Prefer a dedicated Signal number rather than your personal account.
- To revoke access, remove the linked device from the Signal app (Settings → Linked devices) and delete the `signal-data` volume.

### Alert Delivery

Alerts go to Signal via `signal-bridge` → `signal-api`. If the whole Raspberry Pi or Docker stops, nothing on the Pi can alert you.

Mitigations:

- Set `HEALTHCHECKS_URL` so the always-firing `Watchdog` alert pings an external dead man's switch every 5 minutes. The ping is skipped if `signal-api` can't reach Signal, so a broken Signal link is caught too.
- Run `./scripts/validate-config.sh` after changes to confirm a receiver is configured.

## Maintenance Checklist

- Review image tags monthly (Dependabot opens PRs for new tags; `docker-compose` ecosystem in `.github/dependabot.yml`).
- Run an image scanner such as Trivy or Grype on the Raspberry Pi host.
- Check Prometheus `Status > Targets` after every upgrade.
- Rotate Grafana admin password, `GRAFANA_SECRET_KEY`, and Pi-hole credentials after suspected exposure.
- Keep Docker Engine and Raspberry Pi OS patched.
- Send a test alert after upgrading `signal-api` (see `docs/operations.md`).

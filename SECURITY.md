# Security Notes

This project monitors a Raspberry Pi and an existing Pi-hole instance. It does not install Pi-hole and should not be exposed directly to the public internet.

## Main Threats

- Unauthorized access to Grafana, Prometheus, or Alertmanager.
- Leakage of the Pi-hole API token or Grafana secret key from `.env`, shell history, backups, or Docker metadata.
- Overexposure of host metrics through Node Exporter.
- Running outdated container images with known CVEs.
- Treating monitoring backups as harmless data.

## Hardening Applied

- Grafana, Prometheus, and Alertmanager bind to `127.0.0.1` by default through `MONITORING_BIND_ADDRESS`.
- Pi-hole Exporter is only reachable on the internal Docker network.
- Prometheus `--web.enable-lifecycle` is not enabled.
- Alertmanager peer clustering is disabled with `--cluster.listen-address=` for this single-node deployment.
- Containers drop all Linux capabilities where practical.
- Containers use `no-new-privileges`.
- All containers use read-only root filesystems with `tmpfs` mounts for writable scratch space.
- Grafana sign-up, Gravatar, update checks, plugin update checks, news feed, and telemetry reporting are disabled.
- Grafana sessions are signed with a user-supplied `GRAFANA_SECRET_KEY`, preventing session forgery and invalidation on restart.
- Provisioned Grafana datasources are locked (`editable: false`) and provisioned dashboards cannot be deleted or modified from the UI.
- Required secrets fail fast if `.env` is missing or incomplete.
- `.env` and backup archives are ignored by Git.
- Container image tags are pinned instead of using `latest`.
- Prometheus `external_labels` identify this instance in Alertmanager routing.

## Remaining Risks

### Node Exporter

Node Exporter uses host networking, the host PID namespace, and a read-only host root mount. This is the standard pattern for accurate Linux host metrics from a container, but it is a deliberate trust boundary expansion.

Mitigations:

- Keep port `9100` reachable only from the monitoring host or trusted LAN.
- Use host firewall rules on shared networks.
- Change `NODE_EXPORTER_LISTEN_ADDRESS` to a specific trusted interface when possible.

### Pi-hole API Token and Grafana Secret Key

The Pi-hole exporter and Grafana both read secrets from environment variables. Any local user with Docker access can generally inspect container environment variables, so Docker access should be treated as privileged.

Mitigations:

- Keep `.env` permissions tight: `chmod 600 .env`.
- Do not commit `.env`.
- Do not share `docker inspect` output publicly.
- Rotate the Pi-hole token if it is exposed.
- Rotate `GRAFANA_SECRET_KEY` if it is exposed (this will invalidate all active Grafana sessions).

### Web UI Access

Grafana has authentication, but Prometheus and Alertmanager do not provide strong built-in auth in this Compose stack.

Mitigations:

- Keep `MONITORING_BIND_ADDRESS=127.0.0.1` unless behind a VPN, SSH tunnel, or authenticated reverse proxy.
- If exposing Grafana over HTTPS, set `GRAFANA_COOKIE_SECURE=true`.
- Use a long random Grafana admin password.
- Use a long random `GRAFANA_SECRET_KEY` (generate with `openssl rand -base64 32`).

### Backups

Grafana backups can contain sensitive operational data including session tokens, datasource metadata, and user information.

Mitigations:

- Store backup archives outside public shares.
- Encrypt backups if copied off the Raspberry Pi.
- The backup script retains only the 7 most recent archives; adjust the retention count in `scripts/backup-grafana.sh` if needed.

### Alertmanager Notifications

Alertmanager ships with a placeholder `default-log` receiver. Until a real receiver is configured, alerts are logged internally but never delivered.

Mitigations:

- Configure a notification receiver in `alertmanager/alertmanager.yml` (email, Telegram, ntfy, Gotify, Slack, etc.).
- Run `./scripts/check-stack.sh` to confirm a receiver is configured.
- Run `./scripts/validate-config.sh` to catch a missing receiver before deployment.

## Maintenance Checklist

- Review image tags monthly.
- Run an image scanner such as Trivy or Grype on the Raspberry Pi host.
- Check Prometheus `Status > Targets` after every upgrade.
- Rotate Grafana admin password, `GRAFANA_SECRET_KEY`, and Pi-hole credentials after suspected exposure.
- Keep Docker Engine and Raspberry Pi OS patched.
- Verify backup archives are readable and stored securely.

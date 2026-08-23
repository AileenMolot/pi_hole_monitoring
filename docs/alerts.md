# Alert Reference

Alert rules live in `prometheus/alerts.yml`. Prometheus evaluates them every 15 seconds and forwards firing alerts to Alertmanager.

## Inhibit Rules

When Node Exporter or Pi-hole Exporter goes down, Alertmanager suppresses all derived alerts for the same source. This prevents alert storms when a single root cause (e.g. the Pi reboots) would otherwise fire every dependent alert simultaneously.

| Source alert | Suppressed alerts |
|---|---|
| `RaspberryPiExporterDown` | All alerts with `job="raspberry-pi"` |
| `PiholeExporterDown` | All alerts with `job="pihole"` |

---

## Raspberry Pi Alerts

### RaspberryPiExporterDown

| Field | Value |
|---|---|
| Severity | critical |
| For | 2 minutes |
| Expression | `up{job="raspberry-pi"} == 0` |

**What it means:** Prometheus cannot reach Node Exporter. The Raspberry Pi may be offline, Node Exporter may have crashed, or the Docker container may have stopped.

**How to respond:**
1. Check if the Pi is reachable: `ping <pi-ip>`
2. SSH into the Pi and check container status: `docker compose ps`
3. If Node Exporter is stopped: `docker compose up -d node-exporter`
4. Check logs: `docker compose logs node-exporter`

---

### RaspberryPiHighCpuLoad

| Field | Value |
|---|---|
| Severity | warning |
| For | 10 minutes |
| Expression | `node_load1 / num_cpus > 1.5` |

**What it means:** The 1-minute load average per CPU core has exceeded 1.5 for 10 consecutive minutes. The Raspberry Pi is under sustained heavy load.

**How to respond:**
1. SSH into the Pi and check what is consuming CPU: `top` or `htop`
2. Check if any monitoring containers are misbehaving: `docker stats`
3. Consider whether a background process (e.g. `apt upgrade`, `unattended-upgrades`) is temporarily responsible

---

### RaspberryPiMemoryPressure

| Field | Value |
|---|---|
| Severity | warning |
| For | 10 minutes |
| Expression | `1 - (MemAvailable / MemTotal) > 0.85` |

**What it means:** Less than 15% of RAM has been available for 10 minutes. This does not include page cache (which Linux reclaims on demand) — `MemAvailable` already accounts for reclaimable memory.

**How to respond:**
1. Identify memory consumers: `ps aux --sort=-%mem | head -20`
2. Check container memory usage: `docker stats`
3. If the Pi consistently runs close to the limit, consider reducing `PROMETHEUS_RETENTION` or adding swap

---

### RaspberryPiDiskAlmostFull

| Field | Value |
|---|---|
| Severity | warning |
| For | 15 minutes |
| Expression | `1 - (avail_bytes / size_bytes) > 0.85` (excludes tmpfs, overlay, squashfs) |

**What it means:** A mounted filesystem has been above 85% usage for 15 minutes. The alert includes the `mountpoint` label so you can see which filesystem triggered it.

**How to respond:**
1. Check disk usage: `df -h` and `du -sh /* 2>/dev/null | sort -rh | head -20`
2. Common culprits: Prometheus TSDB (`docker volume inspect pi-hole-monitoring_prometheus-data`), Docker images, system logs
3. Reduce `PROMETHEUS_RETENTION` in `.env` and restart Prometheus if metrics storage is the cause
4. Remove unused Docker images: `docker image prune`
5. Rotate old Grafana backups if stored on the same filesystem

---

### RaspberryPiRebooted

| Field | Value |
|---|---|
| Severity | info |
| For | 0 minutes (fires immediately) |
| Expression | `time() - node_boot_time_seconds < 300` |

**What it means:** The Raspberry Pi booted less than 5 minutes ago. This fires once after every reboot, expected or not.

**How to respond:**
- If the reboot was planned, resolve or silence the alert in Alertmanager.
- If the reboot was unexpected, check system logs for the cause: `journalctl -b -1 -n 100` (previous boot) or `last reboot`.

---

### RaspberryPiHighTemperature

| Field | Value |
|---|---|
| Severity | warning |
| For | 2 minutes |
| Expression | `node_thermal_zone_temp > 80` |

**What it means:** The CPU thermal zone temperature has exceeded 80°C for 2 minutes. On Raspberry Pi 5, the CPU begins throttling around 80°C and will reduce clock speed to protect the hardware.

**How to respond:**
1. Check current temperature: `vcgencmd measure_temp` on the Pi
2. Improve airflow around the Pi (ensure the case has ventilation or a heatsink/fan)
3. Identify CPU-heavy processes and reduce load if possible
4. Consider adding active cooling (a fan) if this alert fires regularly

---

### RaspberryPiNetworkErrors

| Field | Value |
|---|---|
| Severity | warning |
| For | 10 minutes |
| Expression | `rate(receive_errs[5m]) + rate(transmit_errs[5m]) > 0` (excludes loopback) |

**What it means:** A network interface is reporting a sustained non-zero error rate. The alert includes the `device` label identifying which interface.

**How to respond:**
1. Check interface errors: `ip -s link show <device>`
2. Check cable or Wi-Fi signal quality
3. Intermittent errors on Wi-Fi are common under interference — a wired connection is more reliable for a monitoring host

---

## Pi-hole Alerts

### PiholeExporterDown

| Field | Value |
|---|---|
| Severity | critical |
| For | 2 minutes |
| Expression | `up{job="pihole"} == 0` |

**What it means:** Prometheus cannot scrape the Pi-hole Exporter container. The exporter may have crashed, or it may be unable to reach the Pi-hole API.

**How to respond:**
1. Check container status: `docker compose ps pihole-exporter`
2. Check logs: `docker compose logs pihole-exporter`
3. Verify Pi-hole is reachable from the Pi: `curl http://<PIHOLE_HOSTNAME>/admin/api.php`
4. Confirm `PIHOLE_API_TOKEN` is correct — an invalid token causes the exporter to return errors

---

### PiholeNoDnsQueries

| Field | Value |
|---|---|
| Severity | warning |
| For | 0 minutes (fires immediately) |
| Expression | `increase(pihole_dns_queries_today[15m]) == 0` |

**What it means:** Pi-hole's total query count has not increased in the last 15 minutes. Either Pi-hole has stopped receiving DNS queries (no devices are using it as their DNS server) or the Pi-hole API is returning stale data.

**How to respond:**
1. Open the Pi-hole dashboard and check the query log
2. Verify that client devices are configured to use the Pi-hole as their DNS server
3. If queries are appearing in the Pi-hole UI but this alert is still firing, the exporter may have a connectivity issue — check `docker compose logs pihole-exporter`

Note: This alert will not fire at midnight when Pi-hole resets its daily counter because the 15-minute window spanning the reset shows a decrease, not zero.

---

### PiholeBlockingDisabledOrIneffective

| Field | Value |
|---|---|
| Severity | info |
| For | 30 minutes |
| Expression | `pihole_ads_percentage_today < 1` |

**What it means:** Fewer than 1% of DNS queries are being blocked over the current day. This may indicate that Pi-hole's blocking has been disabled, blocklists are empty or failed to update, or that query traffic is unusually clean.

**How to respond:**
1. Open Pi-hole → Settings → Blocking and confirm blocking is enabled
2. Check that blocklists are populated: Pi-hole → Group Management → Adlists
3. Update gravity: `pihole -g`
4. A legitimately low block rate is possible on networks with few ad-serving domains in use — adjust the threshold in `prometheus/alerts.yml` if needed

#!/usr/bin/env sh
set -eu

# Resolve published host:port from Compose so .env overrides are respected.
prometheus="$(docker compose port prometheus 9090)"
grafana="$(docker compose port grafana 3000)"
alertmanager="$(docker compose port alertmanager 9093)"

docker compose ps
printf '\nPrometheus targets:\n'
targets_json="$(curl -fsS "http://${prometheus}/api/v1/targets?state=active")"
printf 'Prometheus API is reachable.\n'

if printf '%s' "$targets_json" | grep -q '"health":"down"'; then
  printf 'One or more Prometheus targets are down. Check Prometheus Status > Targets.\n' >&2
  exit 1
fi

printf 'Prometheus targets report healthy.\n'

printf '\nGrafana:\n'
curl -fsS "http://${grafana}/api/health" >/dev/null
printf 'Grafana API is reachable.\n'

printf '\nAlertmanager:\n'
curl -fsS "http://${alertmanager}/-/healthy" >/dev/null
printf 'Alertmanager API is reachable.\n'

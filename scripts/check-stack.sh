#!/usr/bin/env sh
set -eu

env_value() {
  key="$1"
  default_value="$2"

  if [ -f ./.env ]; then
    value="$(awk -F= -v key="$key" '$1 == key {print substr($0, length(key) + 2)}' ./.env | tail -n 1)"
    if [ -n "$value" ]; then
      printf '%s' "$value"
      return
    fi
  fi

  printf '%s' "$default_value"
}

prometheus_port="$(env_value PROMETHEUS_PORT 9090)"
grafana_port="$(env_value GRAFANA_PORT 3000)"
alertmanager_port="$(env_value ALERTMANAGER_PORT 9093)"

docker compose ps
printf '\nPrometheus targets:\n'
targets_json="$(curl -fsS "http://localhost:${prometheus_port}/api/v1/targets?state=active")"
printf 'Prometheus API is reachable.\n'

if printf '%s' "$targets_json" | grep -q '"health":"down"'; then
  printf 'One or more Prometheus targets are down. Check Prometheus Status > Targets.\n' >&2
  exit 1
fi

printf 'Prometheus targets report healthy.\n'

printf '\nGrafana:\n'
curl -fsS "http://localhost:${grafana_port}/api/health" >/dev/null
printf 'Grafana API is reachable.\n'

printf '\nAlertmanager:\n'
curl -fsS "http://localhost:${alertmanager_port}/-/healthy" >/dev/null
printf 'Alertmanager API is reachable.\n'

# Warn if no real notification receiver has been configured yet.
if ! grep -qE '(email|webhook|slack|pagerduty|telegram|pushover|opsgenie|victorops|sns|wechat|msteams|discord)_configs' \
    ./alertmanager/alertmanager.yml 2>/dev/null; then
  printf 'Warning: Alertmanager has no notification receiver configured. Alerts will be logged but not delivered.\n' >&2
fi

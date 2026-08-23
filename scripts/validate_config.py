#!/usr/bin/env python3
"""Validate local monitoring project configuration files."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

YAML_FILES = [
    "docker-compose.yml",
    "prometheus/prometheus.yml",
    "prometheus/alerts.yml",
    "alertmanager/alertmanager.yml",
    "grafana/provisioning/datasources/prometheus.yml",
    "grafana/provisioning/dashboards/dashboards.yml",
]

JSON_FILES = [
    "grafana/dashboards/raspberry-pi.json",
    "grafana/dashboards/pihole.json",
]

SHELL_FILES = [
    "scripts/check-stack.sh",
    "scripts/backup-grafana.sh",
    "scripts/validate-config.sh",
]

PYTHON_FILES = [
    "scripts/validate_config.py",
]

# Config keys that indicate a real notification receiver is wired up.
_RECEIVER_CONFIG_KEYS = (
    "email_configs",
    "webhook_configs",
    "slack_configs",
    "pagerduty_configs",
    "opsgenie_configs",
    "victorops_configs",
    "pushover_configs",
    "sns_configs",
    "telegram_configs",
    "msteams_configs",
    "discord_configs",
    "webex_configs",
)


def print_result(status: str, message: str) -> None:
    print(f"{status} {message}")


def project_file(relative_path: str) -> Path:
    path = (ROOT / relative_path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"path escapes project root: {relative_path}")
    return path


def import_yaml_safely():
    original_path = list(sys.path)
    try:
        root_str = str(ROOT)
        cwd = os.getcwd()
        sys.path = [
            entry
            for entry in sys.path
            if entry not in ("", root_str, cwd)
        ]
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return None
    finally:
        sys.path = original_path

    return yaml


def check_env_file() -> None:
    env_path = project_file(".env")
    if not env_path.exists():
        print_result("warn", ".env not found — copy .env.example to .env and fill in real values before deploying")
    else:
        print_result("ok", ".env exists")


def validate_yaml() -> None:
    yaml = import_yaml_safely()
    for relative_path in YAML_FILES:
        path = project_file(relative_path)
        if yaml is None:
            print_result("skip", f"{relative_path}: PyYAML is not installed")
            continue
        with path.open("r", encoding="utf-8") as handle:
            yaml.safe_load(handle)
        print_result("ok", relative_path)


def validate_json() -> None:
    for relative_path in JSON_FILES:
        path = project_file(relative_path)
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
        print_result("ok", relative_path)


def validate_shell() -> None:
    for relative_path in SHELL_FILES:
        path = project_file(relative_path)
        subprocess.run(["sh", "-n", str(path)], check=True)
        print_result("ok", relative_path)


def validate_python() -> None:
    for relative_path in PYTHON_FILES:
        path = project_file(relative_path)
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        print_result("ok", relative_path)


def validate_docker_compose() -> None:
    if not command_exists("docker"):
        print_result("skip", "docker compose config: docker is not installed")
        return

    subprocess.run(
        ["docker", "compose", "--env-file", ".env.example", "config"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        check=True,
    )
    print_result("ok", "docker compose config")


def validate_prometheus() -> None:
    if not command_exists("promtool"):
        print_result("skip", "promtool checks: promtool is not installed")
        return

    subprocess.run(
        ["promtool", "check", "config", "prometheus/prometheus.yml"],
        cwd=ROOT,
        check=True,
    )
    print_result("ok", "prometheus/prometheus.yml (promtool)")

    subprocess.run(
        ["promtool", "check", "rules", "prometheus/alerts.yml"],
        cwd=ROOT,
        check=True,
    )
    print_result("ok", "prometheus/alerts.yml (promtool)")


def check_alertmanager_receiver() -> None:
    path = project_file("alertmanager/alertmanager.yml")
    content = path.read_text(encoding="utf-8")
    if not any(key in content for key in _RECEIVER_CONFIG_KEYS):
        print_result(
            "warn",
            "alertmanager/alertmanager.yml: no notification receiver configured"
            " — alerts will not be delivered",
        )
    else:
        print_result("ok", "alertmanager/alertmanager.yml receiver")


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def main() -> int:
    check_env_file()
    validate_yaml()
    validate_json()
    validate_shell()
    validate_python()
    validate_docker_compose()
    validate_prometheus()
    check_alertmanager_receiver()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

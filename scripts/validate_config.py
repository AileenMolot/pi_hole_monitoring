#!/usr/bin/env python3
"""Validate local monitoring project configuration files."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_files(pattern: str) -> list[Path]:
    """Files matching pattern, skipping hidden directories like .git."""
    return sorted(
        path
        for path in ROOT.rglob(pattern)
        if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    )


def ok(message: str) -> None:
    print(f"ok {message}")


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    if (ROOT / ".env").exists():
        ok(".env exists")
    else:
        print("warn .env not found — copy .env.example to .env and fill in real values before deploying")

    try:
        import yaml
    except ModuleNotFoundError:
        print("skip YAML syntax: PyYAML is not installed")
    else:
        for path in project_files("*.yml"):
            yaml.safe_load(path.read_text(encoding="utf-8"))
            ok(str(path.relative_to(ROOT)))

    for path in project_files("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
        ok(str(path.relative_to(ROOT)))

    for path in project_files("*.sh"):
        run("sh", "-n", str(path))
        ok(str(path.relative_to(ROOT)))

    for path in project_files("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        ok(str(path.relative_to(ROOT)))

    if shutil.which("docker"):
        subprocess.run(
            ["docker", "compose", "--env-file", ".env.example", "config"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        ok("docker compose config")
    else:
        print("skip docker compose config: docker is not installed")

    if shutil.which("promtool"):
        run("promtool", "check", "config", "prometheus/prometheus.yml")
        ok("prometheus config and rules (promtool)")
    else:
        print("skip promtool checks: promtool is not installed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

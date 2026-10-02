#!/usr/bin/env python3
"""Forward Alertmanager webhooks to Signal via signal-cli-rest-api.

Watchdog alerts are not sent to Signal. Instead the bridge receives pending
Signal messages (proving the linked account still works and keeping it in
sync), then pings HEALTHCHECKS_URL (if set), so an external service notices
when anything in the chain goes silent.
"""

import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

SIGNAL_API = os.environ.get("SIGNAL_API_URL", "http://signal-api:8080")
SIGNAL_NUMBER = os.environ["SIGNAL_NUMBER"]
SIGNAL_RECIPIENTS = os.environ["SIGNAL_RECIPIENTS"].split(",")
HEALTHCHECKS_URL = os.environ.get("HEALTHCHECKS_URL", "")


def format_alert(alert: dict) -> str:
    status = "RESOLVED" if alert["status"] == "resolved" else "FIRING"
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    return "\n".join(
        [
            f"[{status}] {labels.get('alertname', '?')} ({labels.get('severity', '?')})",
            annotations.get("summary", ""),
            annotations.get("description", ""),
        ]
    ).strip()


def post_json(url: str, payload: dict) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(request, timeout=30).close()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        alerts = body.get("alerts", [])
        try:
            if all(a["labels"].get("alertname") == "Watchdog" for a in alerts):
                number = urllib.parse.quote(SIGNAL_NUMBER, safe="")
                urllib.request.urlopen(f"{SIGNAL_API}/v1/receive/{number}", timeout=60).close()
                if HEALTHCHECKS_URL:
                    urllib.request.urlopen(HEALTHCHECKS_URL, timeout=30).close()
            else:
                message = "\n\n".join(format_alert(a) for a in alerts)
                post_json(
                    f"{SIGNAL_API}/v2/send",
                    {"message": message, "number": SIGNAL_NUMBER, "recipients": SIGNAL_RECIPIENTS},
                )
        except Exception as error:  # noqa: BLE001 - any failure should make Alertmanager retry
            self.log_error("delivery failed: %s", error)
            self.send_response(502)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()

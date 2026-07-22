"""Run a local Home Assistant with every Aivi blueprint installed.

Usage: uv run nox -s dev  (or: uv run python dev/run.py)

- Home Assistant runs at http://localhost:8123 (login: aivi / aivi).
- The repo's blueprints/ directory is symlinked into the config, so edits
  land live - reload blueprints (or the demo automations) to pick them up.
- Demo automations drive every blueprint from controllable helper entities;
  see the "Aivi Demo" dashboard.
- Payloads are sent to a local sink on port 8124 that pretty-prints them.
  Point them at the real Aivi API instead by exporting:
      AIVI_ACTIVITY_URL='https://api.getaivi.app/activity/{{ slug }}'
      AIVI_WIDGET_URL='https://api.getaivi.app/widget/{{ slug }}'
      AIVI_AUTHORIZATION='Token <your token>'
"""

import json
import pathlib
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_DIR = pathlib.Path(__file__).parent
STORAGE = CONFIG_DIR / ".storage"
SINK_PORT = 8124
USERNAME = PASSWORD = "aivi"

ONBOARDING = {
    "version": 4,
    "minor_version": 1,
    "key": "onboarding",
    "data": {"done": ["user", "core_config", "analytics", "integration"]},
}


class SinkHandler(BaseHTTPRequestHandler):
    """Pretty-prints every payload Home Assistant sends to the fake API."""

    def do_PATCH(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            pretty = json.dumps(json.loads(body), indent=2, ensure_ascii=False)
        except ValueError:
            pretty = body.decode(errors="replace")
        print(f"\n\033[1;36m→ PATCH {self.path}\033[0m\n{pretty}", flush=True)
        payload = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        """Silence the default per-request access log."""


def seed_auth() -> None:
    """Create the login and skip onboarding on the very first run."""
    if STORAGE.exists():
        return
    subprocess.run(
        [
            sys.executable,
            "-m",
            "homeassistant",
            "--script",
            "auth",
            "-c",
            str(CONFIG_DIR),
            "add",
            USERNAME,
            PASSWORD,
        ],
        check=True,
    )
    (STORAGE / "onboarding").write_text(json.dumps(ONBOARDING))


def main() -> int:
    seed_auth()

    sink = ThreadingHTTPServer(("127.0.0.1", SINK_PORT), SinkHandler)
    threading.Thread(target=sink.serve_forever, daemon=True).start()

    print(
        "\n"
        "  Home Assistant:  http://localhost:8123  (login: aivi / aivi)\n"
        f"  Aivi API sink:   http://localhost:{SINK_PORT}  "
        "(payloads are printed below)\n"
        "  Real API:        export AIVI_ACTIVITY_URL / AIVI_WIDGET_URL / "
        "AIVI_AUTHORIZATION\n",
        flush=True,
    )

    try:
        return subprocess.run(
            [sys.executable, "-m", "homeassistant", "-c", str(CONFIG_DIR)],
            check=False,
        ).returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

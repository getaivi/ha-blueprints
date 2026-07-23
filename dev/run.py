"""Run a local Home Assistant with every Aivi blueprint installed.

Usage: uv run nox -s dev  (or: uv run python dev/run.py)

- Home Assistant runs at http://localhost:8123 (login: aivi / aivi).
- The repo's blueprints/ directory is symlinked into the config, so edits
  land live - reload blueprints (or the demo automations) to pick them up.
- Demo automations drive every blueprint from controllable helper entities;
  see the "Aivi Demo" dashboard.
- Payloads are sent to a local sink on port 8124 that pretty-prints them.
  Point them at the real Aivi API instead by exporting:
      AIVI_HOST=https://api.getaivi.app
      AIVI_TOKEN=<your token>
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_DIR = pathlib.Path(__file__).parent
STORAGE = CONFIG_DIR / ".storage"
REPO_BLUEPRINTS = CONFIG_DIR.parent / "blueprints"
MIRROR = CONFIG_DIR / "blueprints" / "automation" / "aivi"
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


def sync_blueprints() -> None:
    """Mirror the repo's blueprints with real directories + per-file symlinks.

    Home Assistant discovers blueprints with a recursive glob that does not
    follow directory symlinks, so a single symlinked directory would keep
    the Blueprints UI empty. Symlinked files inside real directories are
    discovered fine and still reflect repo edits live.
    """
    if MIRROR.is_symlink():
        MIRROR.unlink()
    elif MIRROR.exists():
        shutil.rmtree(MIRROR)
    for src in sorted(REPO_BLUEPRINTS.glob("*/*/blueprint.yaml")):
        dst = MIRROR / src.relative_to(REPO_BLUEPRINTS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src)


def hass_environ() -> dict[str, str]:
    """Compose the rest_command env vars from AIVI_HOST / AIVI_TOKEN."""
    env = dict(os.environ)
    if host := env.get("AIVI_HOST"):
        host = host.rstrip("/")
        env.setdefault("AIVI_ACTIVITY_URL", f"{host}/activity/{{{{ slug }}}}")
        env.setdefault("AIVI_WIDGET_URL", f"{host}/widget/{{{{ slug }}}}")
    if token := env.get("AIVI_TOKEN"):
        env.setdefault("AIVI_AUTHORIZATION", f"Token {token}")
    return env


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
    sync_blueprints()
    seed_auth()

    sink = ThreadingHTTPServer(("127.0.0.1", SINK_PORT), SinkHandler)
    threading.Thread(target=sink.serve_forever, daemon=True).start()

    target = os.environ.get("AIVI_HOST", f"local sink on port {SINK_PORT}")
    print(
        "\n"
        "  Home Assistant:  http://localhost:8123  (login: aivi / aivi)\n"
        f"  Payloads go to:  {target}\n"
        "  Real API:        export AIVI_HOST=https://api.getaivi.app "
        "AIVI_TOKEN=<your token>\n",
        flush=True,
    )

    try:
        return subprocess.run(
            [sys.executable, "-m", "homeassistant", "-c", str(CONFIG_DIR)],
            check=False,
            env=hass_environ(),
        ).returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

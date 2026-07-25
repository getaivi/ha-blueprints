# Contributing

## Development setup

The project is managed with [uv](https://docs.astral.sh/uv/) and
[nox](https://nox.thea.codes/):

```sh
uv run nox -s test   # run the test suite
uv run nox -s lint   # type check (ty) + lint/format (ruff)
```

Every blueprint has tests under `tests/activities/` or `tests/widgets/`,
driven by a harness that mocks the Aivi rest commands and asserts on the
exact payloads sent.

## Local development

Run a disposable Home Assistant with every blueprint installed:

```sh
uv run nox -s dev
```

Then open <http://localhost:8123> and log in as `aivi` / `aivi` (onboarding is
skipped automatically). What you get:

- **All blueprints, live.** Every repo blueprint is symlinked into the
  instance and shows up in Settings → Automations & Scenes → Blueprints, so
  you can create automations from them in the UI. Edits to the YAML land
  immediately — reload the configuration (or restart) to pick them up. No
  more uploading blueprints by hand.
- **A demo automation per blueprint** (see `dev/demo_automations.yaml`),
  wired to controllable helper entities on the default dashboard: toggle the
  washer, drag the temperature slider, start the tea timer.
- **A local API sink** on port 8124 that pretty-prints every payload the
  blueprints send, so you can inspect the exact wire format in the terminal.

To push to the real Aivi API (and your actual devices) instead of the sink:

```sh
AIVI_HOST=https://api.getaivi.app AIVI_TOKEN=<your token> uv run nox -s dev
```

The instance's state lives in gitignored files under `dev/` — delete
`dev/.storage/` for a factory reset.

## Releasing

Blueprints are published to the flat registry at
`https://ha.getaivi.app/blueprints/` by pushing a release tag:

| Category | Repo path | Release tag | Published as |
| --- | --- | --- | --- |
| Activity | `blueprints/activities/<name>/` | `<name>-1.2.3` | `<name>-v1.yaml`, `<name>-v1.2.3.yaml` |
| Widget | `blueprints/widgets/<name>/` | `widget-<name>-1.2.3` | `widget-<name>-v1.yaml`, `widget-<name>-v1.2.3.yaml` |

Activity blueprints keep their historical unprefixed names, so existing
import URLs never change. Widget blueprints live under the `widget-` prefix,
which keeps the flat namespace collision-free; `tests/test_publishing.py`
enforces that the two namespaces stay disjoint.

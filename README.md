<p align="center">
  <a href="https://getaivi.app">
    <img alt="Aivi icon" width="128" src="https://github.com/user-attachments/assets/a7040ecb-c933-43b6-bf55-1d07d8c1781e" />
  </a>
</p>

<p align="center">
  <strong>Aivi</strong><br />
  Live Activities over API
</p>

<p align="center">
    <a href="https://getaivi.app">Website</a>
    &bull;
    <a href="https://docs.getaivi.app">Documentation</a>
</p>

---

## Blueprints for Home Assistant

This repository is where the official Aivi Home Assistant blueprints are
developed. For details on the available blueprints and how to use them, see the
[blueprint documentation](https://docs.getaivi.app/home-assistant/blueprints/).

The blueprints are organized by what they drive:

- [`blueprints/activities/`](blueprints/activities) — blueprints that update
  Live Activities via `rest_command.update_live_activity`.
- [`blueprints/widgets/`](blueprints/widgets) — blueprints that update
  Home/Lock Screen widgets via `rest_command.update_widget`, one per widget
  template.

## Local development

Run a disposable Home Assistant with every blueprint installed:

```sh
uv run nox -s dev
```

Then open <http://localhost:8123> and log in as `aivi` / `aivi` (onboarding is
skipped automatically). What you get:

- **All blueprints, live.** The repo's `blueprints/` directory is symlinked
  into the instance, so edits land immediately — reload the YAML
  configuration (or restart) to pick them up. No more uploading blueprints by
  hand.
- **A demo automation per blueprint** (see `dev/demo_automations.yaml`),
  wired to controllable helper entities on the **Aivi Demo** dashboard:
  toggle the washer, drag the temperature slider, start the tea timer.
- **A local API sink** on port 8124 that pretty-prints every payload the
  blueprints send, so you can inspect the exact wire format in the terminal.

To push to the real Aivi API (and your actual devices) instead of the sink:

```sh
AIVI_ACTIVITY_URL='https://api.getaivi.app/activity/{{ slug }}' \
AIVI_WIDGET_URL='https://api.getaivi.app/widget/{{ slug }}' \
AIVI_AUTHORIZATION='Token <your token>' \
uv run nox -s dev
```

The instance's state lives in gitignored files under `dev/` — delete
`dev/.storage/` for a factory reset.

## What is Aivi?

Aivi is the simplest way to connect your devices to a real-time Live Activity
on your iPhone. By making a HTTP call to the Aivi API, you can track the
progress of anything – from a washer machine cycle to a progress of a 3D print.

### Features
- **Broad support.** Supports live activities on iOS, iPadOS, WatchOS, CarPlay
  and MacOS<sup>1</sup>.
- **Shared activities.** You set it up once by inviting people, and a single
  API call automatically updates everyone’s devices. No extra work needed to
  keep the whole group in sync.
- **Live activities for any device.** Most smart home devices do not offer live
  activities. Aivi bridges that gap, allowing you to add them to all your
  devices, old or new.
- **Power-Efficient.** Because Aivi only sends data when something changes,
  your devices do not waste battery constantly polling for updates.


<sup>1</sup> Mirroring live activities on MacOS is currently not available in
the EU.

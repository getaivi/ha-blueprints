import json
from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness

MAX_DEVICES = 8
BLUEPRINT = "widgets/battery"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.vacuum_battery", "68")
    hass.states.async_set(
        "sensor.lock_battery",
        "45",
        {"friendly_name": "Door Lock Battery"},
    )
    hass.states.async_set("binary_sensor.lock_charging", "on")


def base_config() -> dict[str, Any]:
    return {
        "slug": "batteries",
        "devices": [
            {
                "name": "Robot vacuum",
                "level": "sensor.vacuum_battery",
                "icon": "fan.fill",
            },
        ],
        "watched": ["sensor.vacuum_battery"],
    }


async def test_reports_configured_devices(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "batteries",
            "devices": [
                {
                    "name": "Robot vacuum",
                    "level": "sensor.vacuum_battery",
                    "icon": "fan.fill",
                },
                {
                    "level": "sensor.lock_battery",
                    "charging": "binary_sensor.lock_charging",
                    "icon": "lock.fill",
                },
            ],
            "watched": [
                "sensor.vacuum_battery",
                "sensor.lock_battery",
                "binary_sensor.lock_charging",
            ],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.vacuum_battery", "70")
        await calls.wait_for_new()

    calls.assert_calls(
        "batteries",
        {
            "content": {
                "template": "battery",
                "devices": [
                    {
                        "name": "Robot vacuum",
                        "level": 70.0,
                        "charging": False,
                        "icon": "fan.fill",
                    },
                    {
                        # Falls back to the friendly name, with the trailing
                        # "Battery" stripped.
                        "name": "Door Lock",
                        "level": 45.0,
                        "charging": True,
                        "icon": "lock.fill",
                    },
                ],
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_caps_at_eight_devices(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    for n in range(9):
        hass.states.async_set(f"sensor.device_{n}_battery", "50")

    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "batteries",
            "devices": [
                {"name": f"Device {n}", "level": f"sensor.device_{n}_battery"}
                for n in range(9)
            ],
            "watched": ["sensor.device_0_battery"],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.device_0_battery", "51")
        await calls.wait_for_new()

    payload = calls.calls[-1].data["payload"]
    devices = json.loads(payload)["content"]["devices"]
    assert len(devices) == MAX_DEVICES
    assert devices[-1]["name"] == "Device 7"


async def test_clamps_level_to_valid_range(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.vacuum_battery", "104")
        await calls.wait_for_new()

    calls.assert_calls(
        "batteries",
        {
            "content": IsPartialDict(
                devices=[IsPartialDict(level=100)],
            ),
        },
    )


async def test_skips_unavailable_devices(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.lock_battery", "unavailable")

    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "batteries",
            "devices": [
                {"name": "Robot vacuum", "level": "sensor.vacuum_battery"},
                {"name": "Door lock", "level": "sensor.lock_battery"},
            ],
            "watched": ["sensor.vacuum_battery"],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.vacuum_battery", "70")
        await calls.wait_for_new()

    calls.assert_calls(
        "batteries",
        {
            "content": IsPartialDict(
                devices=[IsPartialDict(name="Robot vacuum")],
            ),
        },
    )


async def test_skips_update_when_no_device_available(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.vacuum_battery", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

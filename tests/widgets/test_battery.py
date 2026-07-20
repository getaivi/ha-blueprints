from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness

BLUEPRINT = "widgets/battery"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.vacuum_battery", "68")
    hass.states.async_set("sensor.lock_battery", "45")
    hass.states.async_set("binary_sensor.lock_charging", "on")


def base_config() -> dict[str, Any]:
    return {
        "slug": "batteries",
        "device_1_name": "Robot vacuum",
        "device_1_level": "sensor.vacuum_battery",
        "device_1_icon": "fan.fill",
    }


async def test_reports_configured_devices(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "device_2_name": "Door lock",
            "device_2_level": "sensor.lock_battery",
            "device_2_charging": "binary_sensor.lock_charging",
            "device_2_icon": "lock.fill",
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
                        "name": "Door lock",
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


async def test_skips_unconfigured_devices(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.vacuum_battery", "70")
        await calls.wait_for_new()

    calls.assert_calls(
        "batteries",
        {
            "content": IsPartialDict(
                devices=[
                    {
                        "name": "Robot vacuum",
                        "level": 70.0,
                        "charging": False,
                        "icon": "fan.fill",
                    },
                ],
            ),
        },
    )


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


async def test_skips_update_when_no_device_available(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.vacuum_battery", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, icon_obj

BLUEPRINT = "widgets/gauge"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.office_temperature",
        "21.5",
        {"unit_of_measurement": "°C"},
    )


def base_config() -> dict[str, Any]:
    return {
        "slug": "office",
        "value_sensor": "sensor.office_temperature",
        "label": "Office",
        "icon": "thermometer.medium",
    }


async def test_reacts_to_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.office_temperature",
            "23.5",
            {"unit_of_measurement": "°C"},
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "office",
        {
            "content": {
                "template": "gauge",
                "value": 23.5,
                "min_value": 0.0,
                "max_value": 100.0,
                "unit": "°C",
                "label": "Office",
                "color": None,
                "icon": icon_obj("thermometer.medium"),
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_dial_customization(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "min_value": -10,
            "max_value": 40,
            "unit": "degrees",
            "color": "orange",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.office_temperature",
            "23.5",
            {"unit_of_measurement": "°C"},
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "office",
        {
            "content": IsPartialDict(
                min_value=-10.0,
                max_value=40.0,
                unit="degrees",
                color="orange",
            ),
        },
    )


async def test_value_template(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "office",
            "value_template": (
                "{{ states('sensor.office_temperature')|float * 2 }}"
            ),
            "custom_triggers": [
                {
                    "trigger": "state",
                    "entity_id": "sensor.office_temperature",
                },
            ],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.office_temperature",
            "10",
            {"unit_of_measurement": "°C"},
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "office",
        {"content": IsPartialDict(value=20.0, label=None, unit=None)},
    )


async def test_skips_update_when_value_unavailable(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.office_temperature", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

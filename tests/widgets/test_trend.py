from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, icon_obj, value_obj

BLUEPRINT = "widgets/trend"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.outdoor_temperature",
        "21.4",
        {"unit_of_measurement": "°C", "history": [18.2, 19.6, 20.8, 21.4]},
    )
    hass.states.async_set("sensor.temperature_trend", "Rising")


def base_config() -> dict[str, Any]:
    return {
        "slug": "outdoor",
        "value_sensor": "sensor.outdoor_temperature",
        "points_template": (
            "{{ state_attr('sensor.outdoor_temperature', 'history') }}"
        ),
        "state_sensor": "sensor.temperature_trend",
        "icon": "thermometer.medium",
    }


async def test_reacts_to_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.outdoor_temperature",
            "22.0",
            {
                "unit_of_measurement": "°C",
                "history": [18.2, 19.6, 20.8, 22.0],
            },
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "outdoor",
        {
            "content": {
                "template": "trend",
                "value": 22.0,
                "unit": "°C",
                "points": [18.2, 19.6, 20.8, 22.0],
                "state": value_obj("Rising"),
                "color": None,
                "icon": icon_obj("thermometer.medium"),
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_sparkline_color_and_unit_override(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "color": "teal", "unit": "degrees"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.temperature_trend", "Falling")
        await calls.wait_for_new()

    calls.assert_calls(
        "outdoor",
        {
            "content": IsPartialDict(
                color="teal",
                unit="degrees",
                state=value_obj("Falling"),
            ),
        },
    )


async def test_skips_update_when_points_invalid(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "points_template": "{{ 'not-a-list' }}"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.temperature_trend", "Falling")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0


async def test_skips_update_when_too_few_points(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "points_template": "{{ [21.4] }}"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.temperature_trend", "Falling")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

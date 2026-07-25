from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, icon_obj, value_obj

BLUEPRINT = "widgets/progress"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.washer_progress", "0.25")
    hass.states.async_set("sensor.washer_cycle", "Washing")
    hass.states.async_set(
        "sensor.washer_end_time",
        "2026-07-20T14:30:00+00:00",
        {"device_class": "timestamp"},
    )


def base_config() -> dict[str, Any]:
    return {
        "slug": "washer",
        "progress_value": "sensor.washer_progress",
        "state_sensor": "sensor.washer_cycle",
        "end_date_sensor": "sensor.washer_end_time",
        "icon": "washer",
    }


async def test_reacts_to_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.washer_progress", "0.5")
        await calls.wait_for_new()

    calls.assert_calls(
        "washer",
        {
            "content": {
                "template": "progress",
                "progress": {
                    "style": "simple",
                    "value": 0.5,
                    "color": "blue",
                },
                "state": value_obj("Washing"),
                "end_date": "2026-07-20T14:30:00+00:00",
                "icon": icon_obj("washer"),
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_works_without_optional_inputs(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "washer",
            "progress_value": "sensor.washer_progress",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.washer_progress", "0.75")
        await calls.wait_for_new()

    calls.assert_calls(
        "washer",
        {
            "content": IsPartialDict(
                progress={"style": "simple", "value": 0.75, "color": "blue"},
                state=None,
                end_date=None,
            ),
        },
    )


async def test_progress_color_and_template(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "washer",
            "progress_value_template": (
                "{{ states('sensor.washer_progress')|float / 2 }}"
            ),
            "progress_color": "green",
            "custom_triggers": [
                {
                    "trigger": "state",
                    "entity_id": "sensor.washer_progress",
                },
            ],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.washer_progress", "0.8")
        await calls.wait_for_new()

    calls.assert_calls(
        "washer",
        {
            "content": IsPartialDict(
                progress={"style": "simple", "value": 0.4, "color": "green"},
            ),
        },
    )


async def test_skips_update_when_progress_unavailable(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.washer_progress", "unknown")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

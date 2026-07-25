from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, icon_obj, value_obj

BLUEPRINT = "widgets/countdown"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.garbage_pickup",
        "2026-07-22T06:00:00+00:00",
        {"device_class": "timestamp"},
    )
    hass.states.async_set("sensor.garbage_type", "Paper & cardboard")


def base_config() -> dict[str, Any]:
    return {
        "slug": "garbage",
        "target_sensor": "sensor.garbage_pickup",
        "subtitle_sensor": "sensor.garbage_type",
        "icon": "trash.fill",
    }


async def test_reacts_to_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "expired_text": "Collected"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.garbage_pickup",
            "2026-07-29T06:00:00+00:00",
            {"device_class": "timestamp"},
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "garbage",
        {
            "content": {
                "template": "countdown",
                "target": "2026-07-29T06:00:00+00:00",
                "subtitle": value_obj("Paper & cardboard"),
                "expired_text": "Collected",
                "icon": icon_obj("trash.fill"),
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_target_template(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "garbage",
            "target_template": "{{ '2026-08-01T06:00:00+00:00' }}",
            "custom_triggers": [
                {
                    "trigger": "state",
                    "entity_id": "sensor.garbage_type",
                },
            ],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.garbage_type", "Compost")
        await calls.wait_for_new()

    calls.assert_calls(
        "garbage",
        {
            "content": IsPartialDict(
                target="2026-08-01T06:00:00+00:00",
                subtitle=None,
                expired_text=None,
            ),
        },
    )


async def test_skips_update_when_target_invalid(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.garbage_pickup", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

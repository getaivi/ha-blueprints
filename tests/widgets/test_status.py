import json
from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, icon_obj, value_obj

BLUEPRINT = "widgets/status"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.living_room_temperature",
        "21.5",
        {"unit_of_measurement": "°C"},
    )
    hass.states.async_set("sensor.living_room_comfort", "Comfortable")


def base_config() -> dict[str, Any]:
    return {
        "slug": "living-room",
        "value_sensor": "sensor.living_room_temperature",
        "state_sensor": "sensor.living_room_comfort",
        "icon": "thermometer.medium",
    }


async def test_reacts_to_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.living_room_temperature",
            "23.0",
            {"unit_of_measurement": "°C"},
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "living-room",
        {
            "content": {
                "template": "status",
                "value": value_obj("23.0 °C"),
                "state": value_obj("Comfortable"),
                "icon": icon_obj("thermometer.medium"),
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
            "slug": "living-room",
            "state_sensor": "sensor.living_room_comfort",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.living_room_comfort", "Too warm")
        await calls.wait_for_new()

    calls.assert_calls(
        "living-room",
        {
            "content": {
                "template": "status",
                "value": None,
                "state": value_obj("Too warm"),
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_value_and_state_templates(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "living-room",
            "value_template": (
                "{{ states('sensor.living_room_temperature') }} degrees"
            ),
            "value_color_template": "{{ 'orange' }}",
            "state_template": "{{ 'Toasty' }}",
            "custom_triggers": [
                {
                    "trigger": "state",
                    "entity_id": "sensor.living_room_temperature",
                },
            ],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.living_room_temperature",
            "25.0",
            {"unit_of_measurement": "°C"},
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "living-room",
        {
            "content": IsPartialDict(
                value=value_obj("25.0 degrees", text_color="orange"),
                state=value_obj("Toasty"),
            ),
        },
    )


async def test_colors_and_formatter(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "value_color": "cyan",
            "state_color": "green",
            "state_formatter": "time_since",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.living_room_comfort", "Comfy")
        await calls.wait_for_new()

    calls.assert_calls(
        "living-room",
        {
            "content": IsPartialDict(
                value=value_obj("21.5 °C", text_color="cyan"),
                state=value_obj(
                    "Comfy",
                    text_color="green",
                    formatter="time_since",
                ),
            ),
        },
    )


async def test_accent_and_tap_url(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "accent": "indigo",
            "tap_url_template": "{{ 'homeassistant://navigate/climate' }}",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.living_room_comfort", "Comfy")
        await calls.wait_for_new()

    calls.assert_calls(
        "living-room",
        {
            "content": IsPartialDict(
                accent="indigo",
                tap_url="homeassistant://navigate/climate",
            ),
        },
    )


async def test_stale_after_included_when_set(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "stale_after": 900},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.living_room_comfort", "Comfy")
        await calls.wait_for_new()

    recorded = calls.calls[-1]
    payload = json.loads(recorded.data["payload"])
    assert payload["stale_after"] == 900  # noqa: PLR2004


async def test_stale_after_omitted_by_default(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.living_room_comfort", "Comfy")
        await calls.wait_for_new()

    recorded = calls.calls[-1]
    payload = json.loads(recorded.data["payload"])
    assert "stale_after" not in payload


async def test_icon_customization(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "icon": "thermometer.sun",
            "icon_rendering_mode": "palette",
            "icon_primary_color": "red",
            "icon_secondary_color": "orange",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.living_room_comfort", "Comfy")
        await calls.wait_for_new()

    calls.assert_calls(
        "living-room",
        {
            "content": IsPartialDict(
                icon=icon_obj(
                    "thermometer.sun",
                    rendering_mode="palette",
                    primary_color="red",
                    secondary_color="orange",
                ),
            ),
        },
    )

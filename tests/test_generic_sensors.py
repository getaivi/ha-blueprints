from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.helpers.aivi import AiviTestHarness


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("binary_sensor.dishwasher_state", "off")
    hass.states.async_set("sensor.dishwasher_progress", "0.0")
    hass.states.async_set("sensor.dishwasher_human_state", "Idle")
    hass.states.async_set(
        "sensor.dishwasher_relative_eta",
        "0",
        {"device_class": "duration"},
    )


@pytest.mark.asyncio
async def test_reacts_to_state_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        "generic-sensors",
        {
            "slug": "dishwasher",
            "state": "binary_sensor.dishwasher_state",
            "progress": "sensor.dishwasher_progress",
            "human_state": "sensor.dishwasher_human_state",
            "eta": "sensor.dishwasher_relative_eta",
            "icon": "washer",
        },
    )

    hass.states.async_set("binary_sensor.dishwasher_state", "on")
    hass.states.async_set("sensor.dishwasher_human_state", "In progress")
    hass.states.async_set("sensor.dishwasher_relative_eta", "3600")

    with harness.record_calls() as calls:
        await hass.async_block_till_done()

    calls.assert_calls(
        "dishwasher",
        {
            "state": "ONGOING",
            "content": {
                "template": "generic",
                "state": "In progress",
                "remaining_time": 3600,
                "progress": 0.0,
                "icon": "washer",
            },
        },
    )

    hass.states.async_set("binary_sensor.dishwasher_state", "off")
    hass.states.async_set("sensor.dishwasher_human_state", "Done")

    with harness.record_calls() as calls:
        await hass.async_block_till_done()

    calls.assert_calls(
        "dishwasher",
        {
            "state": "IDLE",
            "content": {
                "template": "generic",
                "state": "Done",
                "remaining_time": None,
                "progress": 1.0,
                "icon": "washer",
            },
        },
    )


@pytest.mark.parametrize(
    ("name", "value", "expected_slug", "expected_content"),
    [
        ("icon", "circle.square", None, IsPartialDict(icon="circle.square")),
        ("slug", "oven", "oven", IsPartialDict()),
    ],
)
@pytest.mark.asyncio
async def test_blueprint_input_reflected_in_call(
    hass: HomeAssistant,
    harness: AiviTestHarness,
    name: str,
    value: str,
    expected_slug: str | None,
    expected_content: Any,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3}}},
    )

    await harness.setup_blueprint(
        "generic-sensors",
        {
            "slug": "dishwasher",
            "state": "binary_sensor.dishwasher_state",
            "progress": "sensor.dishwasher_progress",
            "human_state": "sensor.dishwasher_human_state",
            "eta": "sensor.dishwasher_relative_eta",
            "icon": "washer",
            name: value,
        },
    )

    hass.states.async_set("binary_sensor.dishwasher_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        expected_slug or "dishwasher",
        {
            "state": "ONGOING",
            "content": expected_content,
        },
    )

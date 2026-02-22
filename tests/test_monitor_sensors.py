from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("binary_sensor.laundry_state", "off")
    hass.states.async_set("sensor.left_header", "Left header")
    hass.states.async_set("sensor.left_value", "10")
    hass.states.async_set("sensor.left_footer", "Left footer")
    hass.states.async_set("sensor.right_header", "Right header")
    hass.states.async_set("sensor.right_value", "20")
    hass.states.async_set("sensor.right_footer", "Right footer")
    hass.states.async_set("input_boolean.show_left", "on")
    hass.states.async_set("input_boolean.show_right", "off")


@pytest.mark.asyncio
async def test_reacts_to_state_and_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        "monitor-sensors",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "primary_column": "right",
            "left_column_header": "sensor.left_header",
            "left_column_value": "sensor.left_value",
            "left_column_value_color": "red",
            "left_column_value_formatter": "time_since",
            "left_column_footer": "sensor.left_footer",
            "left_column_visibility_condition": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.show_left",
                    "state": "on",
                }
            ],
            "right_column_header": "sensor.right_header",
            "right_column_value": "sensor.right_value",
            "right_column_footer": "sensor.right_footer",
            "right_column_visibility_condition": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.show_right",
                    "state": "on",
                }
            ],
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")

    with harness.record_calls() as calls:
        await hass.async_block_till_done()

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": {
                "template": "monitor",
                "icon": "washer",
                "primary_column": "right",
                "left_column": {
                    "header": "Left header",
                    "value": {
                        "value": "10",
                        "text_color": "red",
                        "formatter": "time_since",
                    },
                    "footer": "Left footer",
                },
                "right_column": None,
            },
        },
    )

    with harness.record_calls() as calls:
        hass.states.async_set("sensor.left_value", "11")
        await calls.wait_for_new()

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                left_column=IsPartialDict(
                    value=IsPartialDict(
                        value="11",
                        text_color="red",
                        formatter="time_since",
                    ),
                ),
                right_column=None,
            ),
        },
    )


@pytest.mark.parametrize(
    ("name", "value", "expected_slug", "expected_content"),
    [
        ("icon", "flame", None, IsPartialDict(icon="flame")),
        ("primary_column", "left", None, IsPartialDict(primary_column="left")),
        ("slug", "boiler", "boiler", IsPartialDict()),
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
    await harness.setup_blueprint(
        "monitor-sensors",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            name: value,
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        expected_slug or "laundry",
        {
            "state": "ONGOING",
            "content": expected_content,
        },
    )

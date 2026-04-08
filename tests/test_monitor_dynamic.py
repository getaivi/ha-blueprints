import asyncio
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


@pytest.mark.parametrize(
    ("config_overrides", "changed_entity_id", "changed_state", "expected_content"),
    [
        pytest.param(
            {
                "left_column_header": "sensor.left_header",
                "left_column_value": "sensor.left_value",
            },
            "sensor.left_header",
            "Left header updated",
            IsPartialDict(left_column=IsPartialDict(header="Left header updated")),
            id="left_header_sensor",
        ),
        pytest.param(
            {
                "left_column_value": "sensor.left_value",
            },
            "sensor.left_value",
            "11",
            IsPartialDict(left_column=IsPartialDict(value=IsPartialDict(value="11"))),
            id="left_value_sensor",
        ),
        pytest.param(
            {
                "left_column_footer": "sensor.left_footer",
                "left_column_value": "sensor.left_value",
            },
            "sensor.left_footer",
            "Left footer updated",
            IsPartialDict(left_column=IsPartialDict(footer="Left footer updated")),
            id="left_footer_sensor",
        ),
        pytest.param(
            {
                "right_column_header": "sensor.right_header",
                "right_column_value": "sensor.right_value",
            },
            "sensor.right_header",
            "Right header updated",
            IsPartialDict(right_column=IsPartialDict(header="Right header updated")),
            id="right_header_sensor",
        ),
        pytest.param(
            {
                "right_column_value": "sensor.right_value",
            },
            "sensor.right_value",
            "21",
            IsPartialDict(right_column=IsPartialDict(value=IsPartialDict(value="21"))),
            id="right_value_sensor",
        ),
        pytest.param(
            {
                "right_column_footer": "sensor.right_footer",
                "right_column_value": "sensor.right_value",
            },
            "sensor.right_footer",
            "Right footer updated",
            IsPartialDict(right_column=IsPartialDict(footer="Right footer updated")),
            id="right_footer_sensor",
        ),
    ],
)
@pytest.mark.asyncio
async def test_reacts_to_state_and_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
    config_overrides: dict[str, Any],
    changed_entity_id: str,
    changed_state: str,
    expected_content: Any,
) -> None:
    hass.states.async_set("input_boolean.show_right", "on")

    await harness.setup_blueprint(
        "monitor-dynamic",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "primary_column": "right",
            "left_column_visibility_condition": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.show_left",
                    "state": "on",
                }
            ],
            "right_column_visibility_condition": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.show_right",
                    "state": "on",
                }
            ],
            **config_overrides,
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    with harness.record_calls() as calls:
        hass.states.async_set(changed_entity_id, changed_state)
        await asyncio.wait_for(calls.wait_for_new(), timeout=0.3)

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": expected_content,
        },
    )


@pytest.mark.asyncio
async def test_custom_triggers_support_template_inputs(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.template_left_header", "Templated left header")

    await harness.setup_blueprint(
        "monitor-dynamic",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "left_column_value_template": "{{ 'left value' }}",
            "left_column_header_template": (
                "{{ states('sensor.template_left_header') }}"
            ),
            "custom_triggers": [
                {
                    "trigger": "state",
                    "entity_id": "sensor.template_left_header",
                }
            ],
        },
    )

    hass.states.async_set("sensor.template_left_header", "Updated templated header")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "laundry",
        {
            "state": "IDLE",
            "content": IsPartialDict(
                left_column=IsPartialDict(
                    header="Updated templated header",
                ),
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
        "monitor-dynamic",
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


@pytest.mark.parametrize(
    "input_overrides",
    [
        pytest.param(
            {},
            id="implicit_defaults",
        ),
        pytest.param(
            {
                "left_column_value_color": "default",
                "left_column_value_formatter": "passthrough",
                "right_column_value_color": "default",
                "right_column_value_formatter": "passthrough",
            },
            id="explicit_defaults",
        ),
    ],
)
@pytest.mark.asyncio
async def test_defaults_are_normalized(
    hass: HomeAssistant,
    harness: AiviTestHarness,
    input_overrides: dict[str, str],
) -> None:
    hass.states.async_set("input_boolean.show_right", "on")

    await harness.setup_blueprint(
        "monitor-dynamic",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "left_column_value": "sensor.left_value",
            "left_column_visibility_condition": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.show_left",
                    "state": "on",
                }
            ],
            "right_column_value": "sensor.right_value",
            "right_column_visibility_condition": [
                {
                    "condition": "state",
                    "entity_id": "input_boolean.show_right",
                    "state": "on",
                }
            ],
            **input_overrides,
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                left_column=IsPartialDict(
                    value=IsPartialDict(
                        value="10",
                        text_color=None,
                        formatter=None,
                    ),
                ),
                right_column=IsPartialDict(
                    value=IsPartialDict(
                        value="20",
                        text_color=None,
                        formatter=None,
                    ),
                ),
            ),
        },
    )


@pytest.mark.asyncio
async def test_value_sensors_include_units_if_set(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("input_boolean.show_right", "on")
    hass.states.async_set("sensor.left_value", "22", {"unit_of_measurement": "m²"})
    hass.states.async_set("sensor.right_value", "55", {"unit_of_measurement": "°C"})

    await harness.setup_blueprint(
        "monitor-dynamic",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "left_column_value": "sensor.left_value",
            "right_column_value": "sensor.right_value",
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                left_column=IsPartialDict(
                    value=IsPartialDict(
                        value="22 m²",
                    ),
                ),
                right_column=IsPartialDict(
                    value=IsPartialDict(
                        value="55 °C",
                    ),
                ),
            ),
        },
    )


@pytest.mark.asyncio
async def test_used_templated_inputs_if_set(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("input_boolean.show_right", "on")

    await harness.setup_blueprint(
        "monitor-dynamic",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "left_column_value_template": "{{ states('sensor.left_value') }}",
            "left_column_value_color_template": "{{ 'purple' }}",
            "left_column_header_template": "{{ states('sensor.left_header') }}",
            "left_column_footer_template": "{{ states('sensor.left_footer') }}",
            "right_column_value_template": "{{ states('sensor.right_value') }}",
            "right_column_value_color_template": "{{ 'green' }}",
            "right_column_header_template": "{{ states('sensor.right_header') }}",
            "right_column_footer_template": "{{ states('sensor.right_footer') }}",
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                left_column=IsPartialDict(
                    header="Left header",
                    value=IsPartialDict(
                        value="10",
                        text_color="purple",
                    ),
                    footer="Left footer",
                ),
                right_column=IsPartialDict(
                    header="Right header",
                    value=IsPartialDict(
                        value="20",
                        text_color="green",
                    ),
                    footer="Right footer",
                ),
            ),
        },
    )


@pytest.mark.asyncio
async def test_tap_url_template(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        "monitor-dynamic",
        {
            "slug": "laundry",
            "state": "binary_sensor.laundry_state",
            "icon": "washer",
            "tap_url_template": "{{ 'homeassistant://navigate/laundry' }}",
        },
    )

    hass.states.async_set("binary_sensor.laundry_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "laundry",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                tap_url="homeassistant://navigate/laundry",
            ),
        },
    )

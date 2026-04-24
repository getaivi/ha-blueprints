import asyncio
from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, icon_obj

BLUEPRINT = "progress-simple"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("binary_sensor.activity_state", "off")
    hass.states.async_set("sensor.progress", "0.5")
    hass.states.async_set("sensor.header_left", "Header left")
    hass.states.async_set("sensor.header_right", "Header right")
    hass.states.async_set("sensor.footer_left", "Footer left")
    hass.states.async_set("sensor.footer_right", "Footer right")
    hass.states.async_set("sensor.compact", "Compact")


def base_config(**overrides: Any) -> dict[str, Any]:
    return {
        "slug": "test-activity",
        "state": "binary_sensor.activity_state",
        "progress_value": "sensor.progress",
        **overrides,
    }


@pytest.mark.asyncio
async def test_state_ongoing(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                template="progress",
                progress=IsPartialDict(style="simple", value=0.5),
            ),
        },
    )


@pytest.mark.asyncio
async def test_state_idle(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    hass.states.async_set("binary_sensor.activity_state", "on")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    hass.states.async_set("binary_sensor.activity_state", "off")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {"state": "IDLE", "content": IsPartialDict(template="progress")},
    )


@pytest.mark.asyncio
async def test_progress_value_from_sensor(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    hass.states.async_set("binary_sensor.activity_state", "on")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    hass.states.async_set("sensor.progress", "0.75")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                progress=IsPartialDict(value=0.75),
            ),
        },
    )


@pytest.mark.asyncio
async def test_progress_value_from_template(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(progress_value_template="{{ 0.42 }}"),
    )

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                progress=IsPartialDict(value=0.42),
            ),
        },
    )


@pytest.mark.asyncio
async def test_progress_value_template_reacts_to_entity_change(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.raw_progress", "50")

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            progress_value_template="{{ states('sensor.raw_progress')|float / 100 }}",
            custom_triggers=[
                {
                    "trigger": "state",
                    "entity_id": "sensor.raw_progress",
                }
            ],
        ),
    )

    hass.states.async_set("binary_sensor.activity_state", "on")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    hass.states.async_set("sensor.raw_progress", "75")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                progress=IsPartialDict(value=0.75),
            ),
        },
    )


@pytest.mark.parametrize(
    ("config_overrides", "changed_entity_id", "changed_state", "expected_content"),
    [
        pytest.param(
            {"header_left_sensor": "sensor.header_left"},
            "sensor.header_left",
            "Updated header left",
            IsPartialDict(
                header_left=IsPartialDict(value="Updated header left"),
            ),
            id="header_left_sensor",
        ),
        pytest.param(
            {"header_right_sensor": "sensor.header_right"},
            "sensor.header_right",
            "Updated header right",
            IsPartialDict(
                header_right=IsPartialDict(value="Updated header right"),
            ),
            id="header_right_sensor",
        ),
        pytest.param(
            {"footer_left_sensor": "sensor.footer_left"},
            "sensor.footer_left",
            "Updated footer left",
            IsPartialDict(
                footer_left=IsPartialDict(value="Updated footer left"),
            ),
            id="footer_left_sensor",
        ),
        pytest.param(
            {"footer_right_sensor": "sensor.footer_right"},
            "sensor.footer_right",
            "Updated footer right",
            IsPartialDict(
                footer_right=IsPartialDict(value="Updated footer right"),
            ),
            id="footer_right_sensor",
        ),
        pytest.param(
            {"compact_value_sensor": "sensor.compact"},
            "sensor.compact",
            "Updated compact",
            IsPartialDict(
                compact_value=IsPartialDict(value="Updated compact"),
            ),
            id="compact_value_sensor",
        ),
    ],
)
@pytest.mark.asyncio
async def test_reacts_to_slot_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
    config_overrides: dict[str, Any],
    changed_entity_id: str,
    changed_state: str,
    expected_content: Any,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config(**config_overrides))

    hass.states.async_set("binary_sensor.activity_state", "on")
    with harness.record_calls() as calls:
        await calls.wait_for_new()

    with harness.record_calls() as calls:
        hass.states.async_set(changed_entity_id, changed_state)
        await asyncio.wait_for(calls.wait_for_new(), timeout=0.3)

    calls.assert_calls(
        "test-activity",
        {"state": "ONGOING", "content": expected_content},
    )


@pytest.mark.asyncio
async def test_template_overrides(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            header_left_template="{{ 'Templated HL' }}",
            header_left_color_template="{{ 'purple' }}",
            header_right_template="{{ 'Templated HR' }}",
            footer_left_template="{{ 'Templated FL' }}",
            footer_right_template="{{ 'Templated FR' }}",
            compact_value_template="{{ 'Templated CV' }}",
        ),
    )

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="Templated HL", text_color="purple"),
                header_right=IsPartialDict(value="Templated HR"),
                footer_left=IsPartialDict(value="Templated FL"),
                footer_right=IsPartialDict(value="Templated FR"),
                compact_value=IsPartialDict(value="Templated CV"),
            ),
        },
    )


@pytest.mark.parametrize(
    "input_overrides",
    [
        pytest.param({}, id="implicit_defaults"),
        pytest.param(
            {
                "header_left_color": "default",
                "header_left_formatter": "passthrough",
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
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            header_left_sensor="sensor.header_left",
            **input_overrides,
        ),
    )

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(
                    value="Header left",
                    text_color=None,
                    formatter=None,
                ),
            ),
        },
    )


@pytest.mark.asyncio
async def test_slot_sensor_includes_units(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.header_left", "42", {"unit_of_measurement": "°C"})

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(header_left_sensor="sensor.header_left"),
    )

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="42 °C"),
            ),
        },
    )


@pytest.mark.asyncio
async def test_custom_triggers_support_template_inputs(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.dynamic_header", "Initial")

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            header_left_template="{{ states('sensor.dynamic_header') }}",
            custom_triggers=[
                {
                    "trigger": "state",
                    "entity_id": "sensor.dynamic_header",
                }
            ],
        ),
    )

    hass.states.async_set("sensor.dynamic_header", "Updated")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "IDLE",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="Updated"),
            ),
        },
    )


@pytest.mark.parametrize(
    ("config_overrides", "expected_slug", "expected_content"),
    [
        pytest.param(
            {"icon": "washer"},
            None,
            IsPartialDict(icon=icon_obj("washer")),
            id="icon",
        ),
        pytest.param(
            {"slug": "my-washer"},
            "my-washer",
            IsPartialDict(),
            id="slug",
        ),
        pytest.param(
            {"progress_color": "green"},
            None,
            IsPartialDict(progress=IsPartialDict(color="green")),
            id="progress_color",
        ),
        pytest.param(
            {"tap_url_template": "{{ 'homeassistant://navigate/laundry' }}"},
            None,
            IsPartialDict(tap_url="homeassistant://navigate/laundry"),
            id="tap_url",
        ),
        pytest.param(
            {},
            None,
            IsPartialDict(icon=None),
            id="icon_defaults_to_none",
        ),
        pytest.param(
            {
                "header_left_sensor": "sensor.header_left",
                "header_left_template": "{{ 'From template' }}",
            },
            None,
            IsPartialDict(header_left=IsPartialDict(value="From template")),
            id="template_takes_precedence_over_sensor",
        ),
    ],
)
@pytest.mark.asyncio
async def test_blueprint_input_reflected_in_call(
    hass: HomeAssistant,
    harness: AiviTestHarness,
    config_overrides: dict[str, Any],
    expected_slug: str | None,
    expected_content: Any,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config(**config_overrides))

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        expected_slug or "test-activity",
        {"state": "ONGOING", "content": expected_content},
    )


@pytest.mark.asyncio
async def test_icon_customization(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            icon="thermometer.sun",
            icon_rendering_mode="palette",
            icon_primary_color="red",
            icon_secondary_color="orange",
            icon_tertiary_color="yellow",
            icon_color_rendering="gradient",
        ),
    )

    hass.states.async_set("binary_sensor.activity_state", "on")

    with harness.record_calls() as calls:
        await calls.wait_for_new()

    calls.assert_calls(
        "test-activity",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                icon={
                    "name": "thermometer.sun",
                    "rendering_mode": "palette",
                    "primary_color": "red",
                    "secondary_color": "orange",
                    "tertiary_color": "yellow",
                    "color_rendering": "gradient",
                },
            ),
        },
    )

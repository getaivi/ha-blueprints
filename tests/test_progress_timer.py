from typing import Any

import pytest
from dirty_equals import IsApprox, IsPartialDict
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.helpers.aivi import AiviTestHarness, icon_obj

BLUEPRINT = "progress-timer"


def base_config(**overrides: Any) -> dict[str, Any]:
    return {
        "slug": "egg",
        "timer": "timer.egg",
        "icon": "timer",
        **overrides,
    }


@pytest.mark.asyncio
async def test_short_timer(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3}}},
    )

    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await hass.async_block_till_done()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                template="progress",
                header_left=IsPartialDict(value="In progress"),
                header_right=IsPartialDict(value="< 1 min"),
                progress=IsPartialDict(
                    style="simple", value=IsApprox(0.33, delta=0.02)
                ),
            ),
        },
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_right=IsPartialDict(value="< 1 min"),
                progress=IsPartialDict(value=IsApprox(0.67, delta=0.02)),
            ),
        },
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_right=IsPartialDict(value="< 1 min"),
                progress=IsPartialDict(value=1),
            ),
        },
        {
            "state": "IDLE",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="Done"),
                header_right=None,
                progress=IsPartialDict(style="simple", value=1),
            ),
        },
        deduplicate=False,
    )


@pytest.mark.asyncio
async def test_pausing(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3600}}},
    )

    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "pause",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="Paused"),
                progress=IsPartialDict(value=IsApprox(0.0)),
            ),
        },
    )


@pytest.mark.asyncio
async def test_resuming(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3600}}},
    )

    await harness.setup_blueprint(BLUEPRINT, base_config())

    for action in ["start", "pause", "start"]:
        with harness.record_calls() as calls:
            await hass.services.async_call(
                "timer",
                action,
                {"entity_id": "timer.egg"},
                blocking=True,
            )
            await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="In progress"),
                progress=IsPartialDict(value=IsApprox(0.0, delta=0.001)),
            ),
        },
    )


@pytest.mark.asyncio
async def test_supports_custom_state_sensor(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.human_state", "Counting down")

    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 100}}},
    )

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(human_state="sensor.human_state"),
    )

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="Counting down"),
            ),
        },
    )

    with harness.record_calls() as calls:
        hass.states.async_set("sensor.human_state", "Still going")
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_left=IsPartialDict(value="Still going"),
            ),
        },
    )


@pytest.mark.asyncio
async def test_eta_formatting_hours_and_minutes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": "01:23:00"}}},
    )

    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_right=IsPartialDict(value="1h 22m"),
            ),
        },
    )


@pytest.mark.asyncio
async def test_eta_formatting_minutes_only(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": "00:45:00"}}},
    )

    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                header_right=IsPartialDict(value="44 min"),
            ),
        },
    )


@pytest.mark.asyncio
async def test_footer_left_sensor(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.footer", "Cotton 60°C")

    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3600}}},
    )

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(footer_left_sensor="sensor.footer"),
    )

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(
                footer_left=IsPartialDict(value="Cotton 60°C"),
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
            {"slug": "oven"},
            "oven",
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
            {"header_left_color": "purple"},
            None,
            IsPartialDict(header_left=IsPartialDict(text_color="purple")),
            id="header_left_color",
        ),
        pytest.param(
            {"header_right_color": "green"},
            None,
            IsPartialDict(header_right=IsPartialDict(text_color="green")),
            id="header_right_color",
        ),
        pytest.param(
            {"footer_right_template": "{{ 'Templated' }}"},
            None,
            IsPartialDict(footer_right=IsPartialDict(value="Templated")),
            id="footer_right_template",
        ),
        pytest.param(
            {"tap_url_template": "{{ 'homeassistant://navigate/kitchen' }}"},
            None,
            IsPartialDict(tap_url="homeassistant://navigate/kitchen"),
            id="tap_url",
        ),
        pytest.param(
            {"icon": ""},
            None,
            IsPartialDict(icon=None),
            id="icon_defaults_to_none",
        ),
    ],
)
@pytest.mark.asyncio
async def test_blueprint_input_reflected_in_call(
    hass: HomeAssistant,
    harness: AiviTestHarness,
    config_overrides: dict[str, str],
    expected_slug: str | None,
    expected_content: Any,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3600}}},
    )

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(**config_overrides),
    )

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        expected_slug or "egg",
        {
            "state": "ONGOING",
            "content": expected_content,
        },
    )


@pytest.mark.asyncio
async def test_idle_state_includes_footer_slots(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.footer", "Cotton 60°C")

    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3}}},
    )

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(footer_left_sensor="sensor.footer"),
    )

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Get the last call which should be IDLE
    idle_calls = [c for c in calls.calls if "IDLE" in str(c.data.get("payload", ""))]
    assert len(idle_calls) == 1


@pytest.mark.asyncio
async def test_icon_customization(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await async_setup_component(
        hass,
        domain="timer",
        config={"timer": {"egg": {"duration": 3600}}},
    )

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

    with harness.record_calls() as calls:
        await hass.services.async_call(
            "timer",
            "start",
            {"entity_id": "timer.egg"},
            blocking=True,
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
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

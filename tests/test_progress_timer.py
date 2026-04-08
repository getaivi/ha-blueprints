from typing import Any

import pytest
from dirty_equals import IsApprox, IsPartialDict
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.helpers.aivi import AiviTestHarness

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
async def test_progress_color(
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
        base_config(progress_color="green"),
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
                progress=IsPartialDict(color="green"),
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


@pytest.mark.asyncio
async def test_footer_template(
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
        base_config(footer_right_template="{{ 'Templated' }}"),
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
                footer_right=IsPartialDict(value="Templated"),
            ),
        },
    )


@pytest.mark.asyncio
async def test_tap_url_template(
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
            tap_url_template="{{ 'homeassistant://navigate/kitchen' }}",
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
                tap_url="homeassistant://navigate/kitchen",
            ),
        },
    )


@pytest.mark.asyncio
async def test_icon_defaults_to_none(
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
        {
            "slug": "egg",
            "timer": "timer.egg",
        },
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
            "content": IsPartialDict(icon=None),
        },
    )


@pytest.mark.parametrize(
    ("name", "value", "expected_slug", "expected_content"),
    [
        ("icon", "washer", None, IsPartialDict(icon="washer")),
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
        BLUEPRINT,
        base_config(**{name: value}),
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

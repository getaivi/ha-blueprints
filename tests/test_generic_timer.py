from typing import Any

import pytest
from dirty_equals import IsApprox, IsPartialDict
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.helpers.aivi import AiviTestHarness


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

    await harness.setup_blueprint(
        "generic-timer",
        {
            "slug": "egg",
            "timer": "timer.egg",
            "icon": "timer",
        },
    )

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
            "content": {
                "template": "generic",
                "state": "In progress",
                "remaining_time": 2,
                "progress": 0.3333333333333333,
                "icon": "timer",
            },
        },
        {
            "state": "ONGOING",
            "content": {
                "template": "generic",
                "state": "In progress",
                "remaining_time": 1,
                "progress": 0.6666666666666666,
                "icon": "timer",
            },
        },
        {
            "state": "ONGOING",
            "content": {
                "template": "generic",
                "state": "In progress",
                "remaining_time": 0,
                "progress": 1,
                "icon": "timer",
            },
        },
        {
            "state": "IDLE",
            "content": {
                "template": "generic",
                "state": "Done",
                "remaining_time": None,
                "progress": 1,
                "icon": "timer",
            },
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

    await harness.setup_blueprint(
        "generic-timer",
        {
            "slug": "egg",
            "timer": "timer.egg",
            "icon": "timer",
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
            "content": {
                "template": "generic",
                "state": "Paused",
                "remaining_time": IsApprox(3600),
                "progress": IsApprox(0.0),
                "icon": "timer",
            },
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

    await harness.setup_blueprint(
        "generic-timer",
        {
            "slug": "egg",
            "timer": "timer.egg",
            "icon": "timer",
        },
    )

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
            "content": {
                "template": "generic",
                "state": "In progress",
                "remaining_time": IsApprox(3600),
                "progress": IsApprox(0.0, delta=0.001),
                "icon": "timer",
            },
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
        "generic-timer",
        {
            "slug": "egg",
            "timer": "timer.egg",
            "icon": "timer",
            "human_state": "sensor.human_state",
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
            "content": IsPartialDict(state="Counting down"),
        },
    )

    with harness.record_calls() as calls:
        hass.states.async_set("sensor.human_state", "Still going")
        await calls.wait_for_new()

    calls.assert_calls(
        "egg",
        {
            "state": "ONGOING",
            "content": IsPartialDict(state="Still going"),
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
        "generic-timer",
        {
            "slug": "egg",
            "timer": "timer.egg",
            "icon": "timer",
            name: value,
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
        expected_slug or "egg",
        {
            "state": "ONGOING",
            "content": expected_content,
        },
    )

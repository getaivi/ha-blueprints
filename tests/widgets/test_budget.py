from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness, value_obj

BLUEPRINT = "widgets/budget"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.monthly_spending", "519.30")
    hass.states.async_set("sensor.monthly_budget", "1500")
    hass.states.async_set("sensor.days_left", "20 days left")


def base_config() -> dict[str, Any]:
    return {
        "slug": "spending",
        "spent_sensor": "sensor.monthly_spending",
        "budget_amount": 1200,
        "currency": "USD",
    }


async def test_reacts_to_sensor_changes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "subtitle_sensor": "sensor.days_left"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.monthly_spending", "540.10")
        await calls.wait_for_new()

    calls.assert_calls(
        "spending",
        {
            "content": {
                "template": "budget",
                "total": {"spent": 540.10, "budget": 1200.0},
                "categories": [],
                "currency": "USD",
                "display": None,
                "subtitle": value_obj("20 days left"),
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_budget_sensor_takes_precedence(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "budget_sensor": "sensor.monthly_budget"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.monthly_spending", "540.10")
        await calls.wait_for_new()

    calls.assert_calls(
        "spending",
        {
            "content": IsPartialDict(
                total={"spent": 540.10, "budget": 1500.0},
            ),
        },
    )


async def test_no_budget_and_display_and_currency_normalization(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "spending",
            "spent_sensor": "sensor.monthly_spending",
            "currency": "sek",
            "display": "spent",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.monthly_spending", "540.10")
        await calls.wait_for_new()

    calls.assert_calls(
        "spending",
        {
            "content": IsPartialDict(
                total={"spent": 540.10, "budget": None},
                currency="SEK",
                display="spent",
            ),
        },
    )


async def test_categories(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.food_spending", "157.60")
    hass.states.async_set("sensor.vehicle_spending", "98.70")
    hass.states.async_set("sensor.hobby_spending", "unavailable")

    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "categories": [
                {
                    "label": "Food",
                    "spent": "sensor.food_spending",
                    "budget": 300,
                    "icon": "fork.knife",
                },
                {
                    "label": "Vehicle",
                    "spent": "sensor.vehicle_spending",
                    "color": "teal",
                },
                {
                    "label": "Hobby",
                    "spent": "sensor.hobby_spending",
                },
            ],
            "watched": [
                "sensor.food_spending",
                "sensor.vehicle_spending",
            ],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.food_spending", "160.00")
        await calls.wait_for_new()

    calls.assert_calls(
        "spending",
        {
            "content": IsPartialDict(
                categories=[
                    {
                        "label": "Food",
                        "spent": 160.0,
                        "budget": 300,
                        "icon": "fork.knife",
                        "color": None,
                    },
                    {
                        "label": "Vehicle",
                        "spent": 98.7,
                        "budget": None,
                        "icon": None,
                        "color": "teal",
                    },
                ],
            ),
        },
    )


async def test_categories_empty_by_default(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.monthly_spending", "540.10")
        await calls.wait_for_new()

    calls.assert_calls(
        "spending",
        {"content": IsPartialDict(categories=[])},
    )


async def test_skips_update_when_spent_unavailable(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.monthly_spending", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

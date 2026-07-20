from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness

BLUEPRINT = "widgets/energy"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.solar_power", "3200")
    hass.states.async_set("sensor.solar_energy_today", "12.4")
    hass.states.async_set("sensor.wind_power", "450")
    hass.states.async_set("sensor.grid_power", "-1400")
    hass.states.async_set("sensor.grid_energy_today", "3.1")
    hass.states.async_set("sensor.battery_power", "800")
    hass.states.async_set("sensor.battery_soc", "76")
    hass.states.async_set("sensor.home_power", "1000")
    hass.states.async_set("sensor.home_energy_today", "9.8")


def full_config() -> dict[str, Any]:
    return {
        "slug": "energy",
        "sources": [
            {
                "power": "sensor.solar_power",
                "today": "sensor.solar_energy_today",
            },
        ],
        "watched": ["sensor.solar_power"],
        "grid_power": "sensor.grid_power",
        "grid_today": "sensor.grid_energy_today",
        "battery_power": "sensor.battery_power",
        "battery_level": "sensor.battery_soc",
        "home_power": "sensor.home_power",
        "home_today": "sensor.home_energy_today",
    }


async def test_reports_all_nodes(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, full_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.solar_power", "3300")
        await calls.wait_for_new()

    calls.assert_calls(
        "energy",
        {
            "content": {
                "template": "energy",
                "sources": [
                    {
                        "name": None,
                        "power": 3300.0,
                        "today": 12.4,
                        "icon": None,
                        "color": None,
                    },
                ],
                "grid": {"power": -1400.0, "today": 3.1},
                "battery": {"power": 800.0, "level": 76.0},
                "home": {"power": 1000.0, "today": 9.8},
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_multiple_named_sources(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "energy",
            "sources": [
                {
                    "name": "Solar",
                    "power": "sensor.solar_power",
                    "today": "sensor.solar_energy_today",
                    "icon": "sun.max.fill",
                },
                {
                    "name": "Wind",
                    "power": "sensor.wind_power",
                    "color": "teal",
                },
            ],
            "watched": ["sensor.solar_power", "sensor.wind_power"],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.wind_power", "500")
        await calls.wait_for_new()

    calls.assert_calls(
        "energy",
        {
            "content": IsPartialDict(
                sources=[
                    {
                        "name": "Solar",
                        "power": 3200.0,
                        "today": 12.4,
                        "icon": "sun.max.fill",
                        "color": None,
                    },
                    {
                        "name": "Wind",
                        "power": 500.0,
                        "today": None,
                        "icon": None,
                        "color": "teal",
                    },
                ],
                grid=None,
                battery=None,
                home=None,
            ),
        },
    )


async def test_works_with_single_node(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "energy",
            "home_power": "sensor.home_power",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.home_power", "1200")
        await calls.wait_for_new()

    calls.assert_calls(
        "energy",
        {
            "content": IsPartialDict(
                sources=[],
                grid=None,
                battery=None,
                home={"power": 1200.0, "today": None},
            ),
        },
    )


async def test_node_omitted_when_power_unavailable(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, full_config())

    hass.states.async_set("sensor.grid_power", "unavailable")

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.home_power", "1200")
        await calls.wait_for_new()

    calls.assert_calls(
        "energy",
        {
            "content": IsPartialDict(
                grid=None,
                home=IsPartialDict(power=1200.0),
            ),
        },
    )


async def test_skips_update_when_no_node_available(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "energy",
            "sources": [{"power": "sensor.solar_power"}],
            "watched": ["sensor.solar_power"],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.solar_power", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

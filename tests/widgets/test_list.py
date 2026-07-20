from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness

BLUEPRINT = "widgets/list"


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set("lock.front_door", "locked")
    hass.states.async_set(
        "sensor.hallway_humidity",
        "54.3",
        {"unit_of_measurement": "%"},
    )
    hass.states.async_set(
        "sensor.mail_delivered",
        "2026-07-20T09:15:00+00:00",
        {"device_class": "timestamp"},
    )


def base_config() -> dict[str, Any]:
    return {
        "slug": "home",
        "row_1_label": "Front door",
        "row_1_entity": "lock.front_door",
        "row_1_color": "green",
        "row_1_icon": "lock.fill",
    }


async def test_reports_configured_rows(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "row_2_label": "Humidity",
            "row_2_entity": "sensor.hallway_humidity",
            "row_3_label": "Mail",
            "row_3_entity": "sensor.mail_delivered",
            "row_3_formatter": "time_since",
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("lock.front_door", "unlocked")
        await calls.wait_for_new()

    calls.assert_calls(
        "home",
        {
            "content": {
                "template": "list",
                "rows": [
                    {
                        "label": "Front door",
                        "value": {
                            "value": "unlocked",
                            "text_color": "green",
                            "formatter": None,
                        },
                        "icon": "lock.fill",
                    },
                    {
                        "label": "Humidity",
                        "value": {
                            "value": "54.3 %",
                            "text_color": None,
                            "formatter": None,
                        },
                        "icon": None,
                    },
                    {
                        "label": "Mail",
                        "value": {
                            "value": "2026-07-20T09:15:00+00:00",
                            "text_color": None,
                            "formatter": "time_since",
                        },
                        "icon": None,
                    },
                ],
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_skips_unavailable_rows(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "row_2_label": "Humidity",
            "row_2_entity": "sensor.hallway_humidity",
        },
    )

    hass.states.async_set("sensor.hallway_humidity", "unavailable")

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("lock.front_door", "unlocked")
        await calls.wait_for_new()

    calls.assert_calls(
        "home",
        {
            "content": IsPartialDict(
                rows=[IsPartialDict(label="Front door")],
            ),
        },
    )


async def test_skips_update_when_no_row_available(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("lock.front_door", "unavailable")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

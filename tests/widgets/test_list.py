import json
from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness

MAX_ROWS = 8
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
        "rows": [
            {
                "label": "Front door",
                "entity": "lock.front_door",
                "color": "green",
                "icon": "lock.fill",
            },
        ],
        "watched": ["lock.front_door"],
    }


async def test_reports_configured_rows(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "home",
            "rows": [
                {
                    "label": "Front door",
                    "entity": "lock.front_door",
                    "color": "green",
                    "icon": "lock.fill",
                },
                {
                    "label": "Humidity",
                    "entity": "sensor.hallway_humidity",
                },
                {
                    "label": "Mail",
                    "entity": "sensor.mail_delivered",
                    "formatter": "time_since",
                },
            ],
            "watched": [
                "lock.front_door",
                "sensor.hallway_humidity",
                "sensor.mail_delivered",
            ],
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


async def test_caps_at_eight_rows(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    for n in range(9):
        hass.states.async_set(f"sensor.value_{n}", str(n))

    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "home",
            "rows": [
                {"label": f"Row {n}", "entity": f"sensor.value_{n}"} for n in range(9)
            ],
            "watched": ["sensor.value_0"],
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.value_0", "42")
        await calls.wait_for_new()

    payload = calls.calls[-1].data["payload"]
    rows = json.loads(payload)["content"]["rows"]
    assert len(rows) == MAX_ROWS
    assert rows[-1]["label"] == "Row 7"


async def test_skips_unavailable_rows(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.hallway_humidity", "unavailable")

    await harness.setup_blueprint(
        BLUEPRINT,
        {
            "slug": "home",
            "rows": [
                {"label": "Front door", "entity": "lock.front_door"},
                {"label": "Humidity", "entity": "sensor.hallway_humidity"},
            ],
            "watched": ["lock.front_door"],
        },
    )

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

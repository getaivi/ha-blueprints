import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant

from tests.helpers.aivi import AiviTestHarness

BLUEPRINT = "widgets/prices"

ENTRIES_TEMPLATE = """
{% set raw = state_attr('sensor.electricity_prices', 'raw_today') or [] %}
[{% for e in raw %}
{"start": "{{ e.start }}", "price": {{ e.price }}}{{ "," if not loop.last }}
{% endfor %}]
"""


@pytest.fixture(autouse=True)
def setup_entities(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.electricity_prices",
        "14.2",
        {
            "raw_today": [
                {"start": "2026-07-20T10:00:00+00:00", "price": 14.2},
                {"start": "2026-07-20T11:00:00+00:00", "price": 16.4},
            ],
        },
    )


def base_config() -> dict[str, str | list]:
    return {
        "slug": "electricity",
        "entries_template": ENTRIES_TEMPLATE,
        "unit": "ct/kWh",
        "custom_triggers": [
            {
                "trigger": "state",
                "entity_id": "sensor.electricity_prices",
            },
        ],
    }


async def test_reacts_to_price_updates(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.electricity_prices",
            "12.8",
            {
                "raw_today": [
                    {"start": "2026-07-21T10:00:00+00:00", "price": 12.8},
                    {"start": "2026-07-21T11:00:00+00:00", "price": 11.9},
                ],
            },
        )
        await calls.wait_for_new()

    calls.assert_calls(
        "electricity",
        {
            "content": {
                "template": "prices",
                "entries": [
                    {"start": "2026-07-21T10:00:00+00:00", "price": 12.8},
                    {"start": "2026-07-21T11:00:00+00:00", "price": 11.9},
                ],
                "unit": "ct/kWh",
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_entries_with_levels(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {
            **base_config(),
            "entries_template": (
                "{{ [{'start': '2026-07-20T10:00:00+00:00',"
                " 'price': 14.2, 'level': 'high'}] }}"
            ),
        },
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.electricity_prices", "15.0")
        await calls.wait_for_new()

    calls.assert_calls(
        "electricity",
        {
            "content": IsPartialDict(
                entries=[
                    {
                        "start": "2026-07-20T10:00:00+00:00",
                        "price": 14.2,
                        "level": "high",
                    },
                ],
            ),
        },
    )


async def test_skips_update_when_entries_empty(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.electricity_prices",
            "0",
            {"raw_today": []},
        )
        await hass.async_block_till_done()

    assert len(calls.calls) == 0


async def test_skips_update_when_entries_not_a_list(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        {**base_config(), "entries_template": "{{ 'boom' }}"},
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.electricity_prices", "15.0")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0

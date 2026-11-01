import json
from typing import Any

import pytest
from dirty_equals import IsPartialDict
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.helpers.aivi import AiviTestHarness, icon_obj, value_obj

MAX_STATS = 6
MAX_LABEL = 24
BLUEPRINT = "widgets/showcase"
PICTURE = "https://example.com/aivi/car-side.png"
BATTERY = {"friendly_name": "Car Battery", "unit_of_measurement": "%"}


@pytest.fixture(autouse=True)
async def setup_entities(hass: HomeAssistant) -> None:
    # Loads the translations that turn "locked" into "Locked".
    for domain in ("lock", "binary_sensor"):
        assert await async_setup_component(hass, domain, {})
    hass.states.async_set("lock.car", "locked", {"friendly_name": "Car lock"})
    hass.states.async_set("sensor.car_battery", "78", BATTERY)
    hass.states.async_set(
        "sensor.car_range",
        "312",
        {"friendly_name": "Car Range", "unit_of_measurement": "km"},
    )
    hass.states.async_set(
        "binary_sensor.car_charging",
        "on",
        {"friendly_name": "Car Charging"},
    )


def base_config(**overrides: Any) -> dict[str, Any]:
    return {
        "slug": "car",
        "image_url": PICTURE,
        "state_entity": "lock.car",
        "readings": [{"entity": "sensor.car_battery", "label": "Battery"}],
        "watched": ["sensor.car_battery"],
        **overrides,
    }


def last_payload(calls: Any) -> dict[str, Any]:
    return json.loads(calls.calls[-1].data["payload"])


def reported_at(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state is not None
    return state.last_changed.isoformat()


async def test_reports_one_reading(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            image_alt="The car",
            badge_url="https://example.com/aivi/brand.png",
            state_icon="lock.fill",
            icon="car.fill",
            accent="blue",
            tap_url_template="https://example.com/car",
        ),
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "79", BATTERY)
        await calls.wait_for_new()

    calls.assert_calls(
        "car",
        {
            "content": {
                "template": "showcase",
                "image": {"url": PICTURE, "alt": "The car", "fit": "contain"},
                "badge": {"url": "https://example.com/aivi/brand.png", "alt": None},
                "state": {
                    "text": {"value": "Locked", "text_color": None},
                    "icon": "lock.fill",
                },
                "reported_at": reported_at(hass, "lock.car"),
                "stats": [
                    {"label": "Battery", "value": value_obj("79"), "unit": "%"},
                ],
                "icon": icon_obj("car.fill"),
                "accent": "blue",
                "tap_url": "https://example.com/car",
            },
        },
    )


async def test_reports_six_readings(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    for n in range(MAX_STATS + 1):
        hass.states.async_set(
            f"sensor.reading_{n}",
            str(n),
            {"friendly_name": f"Reading {n}", "unit_of_measurement": "kWh"},
        )

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            readings=[{"entity": f"sensor.reading_{n}"} for n in range(MAX_STATS + 1)],
            watched=["sensor.reading_0"],
        ),
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set(
            "sensor.reading_0",
            "10",
            {"friendly_name": "Reading 0", "unit_of_measurement": "kWh"},
        )
        await calls.wait_for_new()

    stats = last_payload(calls)["content"]["stats"]
    assert len(stats) == MAX_STATS
    assert stats == [
        {"label": "Reading 0", "value": value_obj("10"), "unit": "kWh"},
        *(
            {"label": f"Reading {n}", "value": value_obj(str(n)), "unit": "kWh"}
            for n in range(1, MAX_STATS)
        ),
    ]


async def test_label_override_and_fallbacks(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.unnamed", "5")
    hass.states.async_set(
        "sensor.long_name",
        "1",
        {"friendly_name": "A very long friendly name for a reading"},
    )

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            readings=[
                {"entity": "sensor.car_range", "label": "Range"},
                {"entity": "sensor.car_battery"},
                {"entity": "sensor.car_battery", "label": "  "},
                {"entity": "sensor.unnamed"},
                {"entity": "sensor.long_name"},
            ],
        ),
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "80", BATTERY)
        await calls.wait_for_new()

    labels = [s["label"] for s in last_payload(calls)["content"]["stats"]]
    assert labels == [
        # The override wins over the friendly name.
        "Range",
        # Without one, the friendly name is used, also for a blank override.
        "Car Battery",
        "Car Battery",
        # Without a friendly name, the entity ID.
        "sensor.unnamed",
        # Trimmed to the template's 24-character limit.
        "A very long friendly nam",
    ]
    assert all(len(label) <= MAX_LABEL for label in labels)


async def test_non_numeric_reading_uses_display_state(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(readings=[{"entity": "binary_sensor.car_charging"}]),
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("lock.car", "unlocked")
        await calls.wait_for_new()

    calls.assert_calls(
        "car",
        {
            "content": IsPartialDict(
                state={
                    "text": {"value": "Unlocked", "text_color": None},
                    "icon": None,
                },
                stats=[
                    # No unit: the display state, not the raw "on".
                    {"label": "Car Charging", "value": value_obj("On"), "unit": None},
                ],
            ),
        },
    )


async def test_skips_unavailable_and_missing_readings(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    hass.states.async_set("sensor.car_range", "unavailable")

    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(
            readings=[
                {"entity": "sensor.car_range", "label": "Range"},
                {"entity": "sensor.does_not_exist", "label": "Missing"},
                {"entity": "sensor.car_battery", "label": "Battery"},
            ],
        ),
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "77", BATTERY)
        await calls.wait_for_new()

    calls.assert_calls(
        "car",
        {
            "content": IsPartialDict(
                stats=[{"label": "Battery", "value": value_obj("77"), "unit": "%"}],
            ),
        },
    )


async def test_skips_update_when_no_reading_available(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "unavailable")
        await hass.async_block_till_done()
        hass.states.async_set("lock.car", "unlocked")
        await hass.async_block_till_done()

    assert len(calls.calls) == 0


async def test_omits_state_when_state_entity_unavailable(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config(state_icon="lock.fill"))

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("lock.car", "unavailable")
        await calls.wait_for_new()

    calls.assert_calls(
        "car",
        {"content": IsPartialDict(state=None, reported_at=None)},
    )


async def test_works_without_state_entity_or_picture(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    config = base_config()
    del config["state_entity"]
    del config["image_url"]
    await harness.setup_blueprint(BLUEPRINT, config)

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "76", BATTERY)
        await calls.wait_for_new()

    calls.assert_calls(
        "car",
        {
            "content": {
                "template": "showcase",
                "image": None,
                "badge": None,
                "state": None,
                "reported_at": None,
                "stats": [
                    {"label": "Battery", "value": value_obj("76"), "unit": "%"},
                ],
                "icon": None,
                "accent": None,
                "tap_url": None,
            },
        },
    )


async def test_passes_picture_url_through(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    url = "https://pictures.example.com/aivi/car-front.jpg?v=2"
    await harness.setup_blueprint(
        BLUEPRINT,
        base_config(image_url=f"  {url} ", image_fit="cover"),
    )

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "75", BATTERY)
        await calls.wait_for_new()

    calls.assert_calls(
        "car",
        {
            "content": IsPartialDict(
                image={"url": url, "alt": None, "fit": "cover"},
                badge=None,
            ),
        },
    )


async def test_triggers_on_state_entity(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config())

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("lock.car", "unlocked")
        await calls.wait_for_new()

    payload = last_payload(calls)
    assert payload["content"]["state"]["text"]["value"] == "Unlocked"
    assert payload["content"]["reported_at"] == reported_at(hass, "lock.car")


async def test_stale_after(
    hass: HomeAssistant,
    harness: AiviTestHarness,
) -> None:
    await harness.setup_blueprint(BLUEPRINT, base_config(stale_after=3600))

    with harness.widgets.record_calls() as calls:
        hass.states.async_set("sensor.car_battery", "74", BATTERY)
        await calls.wait_for_new()

    assert last_payload(calls)["stale_after"] == 3600  # noqa: PLR2004

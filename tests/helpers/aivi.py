import asyncio
import itertools
import json
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, Unpack

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

IconRenderingMode = Literal["monochrome", "hierarchical", "palette", "multicolor"]
IconColorRendering = Literal["flat", "gradient"]
IconColor = Literal[
    "red",
    "orange",
    "yellow",
    "green",
    "mint",
    "teal",
    "cyan",
    "blue",
    "indigo",
    "purple",
    "pink",
    "brown",
    "gray",
    "gray2",
    "gray3",
    "gray4",
    "gray5",
    "gray6",
]


def normalize_call_data(call_data: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(call_data, str):
        return json.loads(call_data)
    return call_data


class IconOverrides(TypedDict, total=False):
    rendering_mode: IconRenderingMode | None
    primary_color: IconColor | None
    secondary_color: IconColor | None
    tertiary_color: IconColor | None
    color_rendering: IconColorRendering | None


class IconPayload(IconOverrides):
    name: str


def icon_obj(name: str, **overrides: Unpack[IconOverrides]) -> IconPayload:
    """Expected shape of the icon object in a payload.

    Matches the blueprint's emission: a dict with `name` plus all optional
    fields defaulting to None. Pass overrides to populate specific fields.
    """
    return IconPayload(
        name=name,
        rendering_mode=overrides.get("rendering_mode"),
        primary_color=overrides.get("primary_color"),
        secondary_color=overrides.get("secondary_color"),
        tertiary_color=overrides.get("tertiary_color"),
        color_rendering=overrides.get("color_rendering"),
    )


class AiviAPIMock:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._calls = async_mock_service(
            self.hass,
            "rest_command",
            "update_live_activity",
            response={"status": "200"},
        )

    @property
    def calls(self) -> Sequence[ServiceCall]:
        return self._calls


class AiviCallHistory:
    def __init__(self, calls: Callable[[], Sequence[ServiceCall]]) -> None:
        self._calls = calls

    @property
    def calls(self) -> Sequence[ServiceCall]:
        return self._calls()

    def assert_calls(
        self,
        slug: str,
        *expected_payloads: dict[str, Any],
        deduplicate: bool = True,
    ) -> None:
        recorded_payloads = [
            normalize_call_data(call.data["payload"])
            for call in self.calls
            if call.data["slug"] == slug
        ]

        if deduplicate:
            recorded_payloads = [g for g, _ in itertools.groupby(recorded_payloads)]

        assert recorded_payloads == list(expected_payloads)

    async def wait_for_new(self, *, wait_for: int = 5) -> None:
        async with asyncio.timeout(wait_for):
            num_calls = len(self.calls)
            while len(self.calls) == num_calls:  # noqa: ASYNC110
                await asyncio.sleep(0.001)


@dataclass
class Bounds:
    start: int
    stop: int | None = None

    def as_slice(self) -> slice:
        return slice(self.start, self.stop)


class AiviTestHarness:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.mock = AiviAPIMock(self.hass)

    async def setup_blueprint(self, name: str, config: dict[str, Any]) -> None:
        await async_setup_component(
            self.hass,
            "automation",
            {
                "automation": {
                    "use_blueprint": {
                        "path": f"{name}/blueprint.yaml",
                        "input": config,
                    },
                },
            },
        )

    @contextmanager
    def record_calls(self) -> Generator[AiviCallHistory]:
        bounds = Bounds(start=len(self.mock.calls))
        yield AiviCallHistory(lambda: self.mock.calls[bounds.as_slice()])
        bounds.stop = len(self.mock.calls)

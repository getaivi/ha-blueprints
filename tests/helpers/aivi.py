import asyncio
import itertools
import json
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service


def normalize_call_data(call_data: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(call_data, str):
        return json.loads(call_data)
    return call_data


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

    async def wait_for_new(self) -> None:
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

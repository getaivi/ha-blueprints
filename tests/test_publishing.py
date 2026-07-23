"""Guards for the published blueprint namespace.

Blueprints publish to a flat registry (ha.getaivi.app/blueprints/): activity
blueprints as `<name>-vX.yaml`, widget blueprints as `widget-<name>-vX.yaml`.
These tests keep the two namespaces disjoint so a release can never overwrite
a blueprint from the other category.
"""

import pathlib
import re

REPO = pathlib.Path(__file__).parent.parent
ACTIVITIES = REPO / "blueprints" / "activities"
WIDGETS = REPO / "blueprints" / "widgets"

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def published_names() -> dict[str, pathlib.Path]:
    """Map each blueprint's published name to its blueprint.yaml.

    Mirrors the resolution in .github/workflows/cicd.yaml: a release tag
    `<published-name>-X.Y.Z` publishes the returned path.
    """
    names = {path.parent.name: path for path in ACTIVITIES.glob("*/blueprint.yaml")}
    names |= {
        f"widget-{path.parent.name}": path for path in WIDGETS.glob("*/blueprint.yaml")
    }
    return names


def test_every_blueprint_is_publishable() -> None:
    names = published_names()
    assert len(names) == len(list(REPO.glob("blueprints/*/*/blueprint.yaml")))


def test_published_names_are_valid_slugs() -> None:
    for name in published_names():
        assert SLUG_RE.match(name), f"{name} is not a valid published slug"


def test_activity_names_stay_out_of_the_widget_namespace() -> None:
    """An activity directory named `widget-*` would collide with a widget."""
    for path in ACTIVITIES.glob("*/blueprint.yaml"):
        assert not path.parent.name.startswith("widget-"), (
            f"Activity blueprint {path.parent.name!r} collides with the "
            "widget- published prefix"
        )

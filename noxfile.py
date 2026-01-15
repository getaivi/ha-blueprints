import nox

nox.options.default_venv_backend = "uv"


def uv_run(session: nox.Session, *args: str) -> None:
    assert isinstance(session.python, str)
    session.run("uv", "run", "--python", session.python, "--active", *args)


@nox.session(python=["3.13"])
@nox.parametrize("hass", ["2026.1.0"])
def test(session: nox.Session, hass: str) -> None:
    uv_run(
        session,
        "--with",
        f"homeassistant=={hass}",
        "--",
        "pytest",
        "--cov=tests",
        "--cov-report=term-missing",
        *session.posargs,
    )


@nox.session(python="3.13")
def lint(session: nox.Session) -> None:
    uv_run(session, "--", "ty", "check")
    uv_run(session, "--", "ruff", "check")
    uv_run(session, "--", "ruff", "format", "--check")

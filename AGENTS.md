# Repository Guidelines

## Project Structure & Module Organization
- Core runtime code lives in `src/nats_client/`, split into `broker.py`, `schema.py`, and `service.py`. The top-level `client.py` module simply re-exports `NatsBroker`, `ActionSchema`, and `CreateService` for backwards compatibility.
- Distribution scaffolding (`setup.py`, `setup.cfg`, `PKG-INFO`, `nats_client_py.egg-info/`) handles packaging; edit `setup.cfg` or add `pyproject.toml` for metadata updates.
- Documentation and planning artifacts belong under `docs/`; see `docs/TODO.md` for active maintenance tasks.
- Keep prospective test suites in a top-level `tests/` package mirroring the public API surface in `client.py`.

## Build, Test, and Development Commands
- `python -m pip install -e .` installs the package in editable mode so local changes are immediately importable.
- `python -m pip install nats-py pytest` ensures the NATS client and baseline test tooling are available during development.
- `python -m pytest` (from the repository root) runs all tests once the `tests/` directory contains suites.
- `python setup.py sdist bdist_wheel` creates source and wheel distributions for release validation when a `pyproject.toml` is not yet present.

## Coding Style & Naming Conventions
- Follow PEP 8 defaults: 4-space indentation, snake_case for functions/variables, PascalCase for classes.
- Prefer explicit type hints for public functions; `client.py` already targets Python 3.10+ features such as `list[str]`.
- Use `black` (line length 88) and `isort` to keep formatting consistent; run them before submitting changes.
- Limit logger usage to `logging` rather than `print` to aid observability in production deployments.

## Testing Guidelines
- Organize tests under `tests/` using `pytest`, naming files `test_<module>.py` and test functions `test_<behavior>()`.
- Aim to cover broker connection flows, request/response handling, validation hooks, and error paths.
- When adding async tests, leverage `pytest.mark.asyncio` or an equivalent fixture for event-loop management.
- Document any external dependencies (e.g., an embedded NATS server) within the test module docstring.

## Commit & Pull Request Guidelines
- Use imperative present-tense commit messages (e.g., `Add broker validation hook`) and keep subjects under 72 characters.
- Each PR should describe intent, summarize testing (`pytest`, linting), and link any tracked issues or TODO items it resolves.
- Include protocol-impact notes when changing wire formats (subjects, payload schema) so reviewers can gauge backward compatibility.
- Screenshots are unnecessary; concise reproduction steps and configuration notes are preferred for reviewer efficiency.

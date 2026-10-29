# Installation

[Table of Contents](toc.md)

> [!WARNING]
> This is still evolving and I expect it to change significantly over time.

## Overview

Although the ActivityPub server being tested can be written in any language, the test framework is implemented in Python.
The project is managed with [uv](https://docs.astral.sh/uv/) and requires Python 3.11 or newer.

All dependencies, including the development tools, are declared in `pyproject.toml` and pinned in `uv.lock`.
You don't need to install Python, a virtual environment or `pytest` by hand: `uv` creates and manages the
project environment in `./.venv` for you.

## Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation documentation](https://docs.astral.sh/uv/getting-started/installation/) for other
platforms and package managers.

## Use the test suite from a server-specific test project

The test suite is designed to be used from a server-specific test project that provides the
[server abstraction layer](sal.md) for the server under test.

* Create an empty Python project and initialize it with uv:

  ```bash
  uv init --package my-server-testing
  cd my-server-testing
  ```

* Add the activitypub-testsuite dependency from GitHub:

  ```bash
  uv add "git+https://github.com/steve-bate/activitypub-testsuite"
  ```

* Synchronize the environment (this also creates the `.venv`):

  ```bash
  uv sync
  ```

* Run the tests:

  ```bash
  uv run pytest
  ```

## Configure `pytest`

Add following to your pyproject.toml file.

```toml
[tool.pytest.ini_options]
addopts = [".", "--pyargs", "activitypub_testsuite.tests"]
markers = [
    "ap_reqlevel: ActivityPub requirements level",
    "ap_capability: ActivityPub/AS2 capability required for test",
]
asyncio_default_fixture_loop_scope = "function"
filterwarnings = [
    "ignore:'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16:DeprecationWarning:pytest_asyncio.plugin",
]
```

At this point you should be able to run `uv run pytest` from the command line although it will fail until you have a *server abstraction layer* to tell the framework how to interact
with your specific server implementation.

## Working on the test suite itself

Clone the repository and synchronize the development environment. The `dev` dependency group
(`black`, `ruff`, `pre-commit`) is installed by default; use `--no-dev` to skip it.

```bash
git clone https://github.com/steve-bate/activitypub-testsuite
cd activitypub-testsuite
uv sync
```

Common commands:

| Task | Command |
| --- | --- |
| Synchronize the environment after changing dependencies | `uv sync` |
| Update `uv.lock` | `uv lock` (or `uv lock --upgrade`) |
| Run the unit tests for the test utilities | `uv run pytest` |
| Generate an HTML report from `test-report.json` | `uv run aptest report --input test-report.json --output report.html` |
| Format and lint | `uv run black .` and `uv run ruff check .` |
| Run the configured git hooks | `uv run pre-commit run --all-files` |

The `aptest` command is registered as a project script (`[project.scripts]` in `pyproject.toml`), so it is
available through `uv run aptest` and, once the environment exists, directly as `.venv/bin/aptest`.

> [!NOTE]
> `uv.lock` is committed. Run `uv sync` after pulling changes instead of installing packages manually, and use
> `uv add` / `uv remove` to change dependencies so that `pyproject.toml` and `uv.lock` stay in sync.

## See Also

* [Server Testing Strategy](testing-strategy.md)
* [Server Abstraction Layer](sal.md)
* [Test Configuration (declaring server capabilities)](configuration.md)
* [Development Notes](devnotes.md)

---
[Table of Contents](toc.md)

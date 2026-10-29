# Development Notes

# uv and virtual environments

The project is managed with [uv](https://docs.astral.sh/uv/). `uv sync` creates the virtual environment in
`./.venv` and installs the project (plus the `dev` dependency group) into it. Run tools through uv
(`uv run pytest`, `uv run black .`) so they always use the locked environment. If an IDE or test runner asks for
an interpreter, point it at `./.venv/bin/python`.

# Visual Studio Code

I'm using Visual Studio Code on MacOS and run the tests in the test runner extension. However, sometimes I'm seeing unstable behavior with the latest VSCode when running unit test that start subprocesses and extra threads.

# Other IDEs and environments.

(I'll add more content here when it's available.)

---
[Table of Contents](toc.md)

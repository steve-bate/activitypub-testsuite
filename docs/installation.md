# Installation

[Table of Contents](toc.md)

> [!WARNING]
> This is still evolving and I expect it to change significantly over time.

## Create an empty Python project

Although the ActivityPub server being tested can be written in any language, the test framework is implemented in Python. 

* Create a PEP 621 `pyproject.toml`.
* Add activitypub-testsuite dependency
  * `git+https://github.com/steve-bate/activitypub-testsuite`
* Install the project

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

At this point you should be able to run `pytest` from the command line although it will fail until you have a *server abstraction layer* to tell the framework how to interact
with your specific server implementation.

## See Also

* [Server Testing Strategy](testing-strategy.md)
* [Server Abstraction Layer](sal.md)
* [Test Configuration (declaring server capabilities)](configuration.md)

---
[Table of Contents](toc.md)

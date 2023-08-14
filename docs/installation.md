# Installation

[Table of Contents](toc.md)

> [!WARNING]
> This is still evolving and I expect it to change significantly over time.

## Install the Test Suite

*NOTE: There are various ways to install this test suite. Currently, the guide is documenting how I have been using the suite for experimentation.*

Create a directory to hold the test-related repositories. For example:

```
testing
  ├── activitypub-testsuite
  ├── myserver-aptesting
```

Either clone or fork the [`activitypub-testsuite`](https://github.com/steve-bate/activitypub-testsuite) repository. Fork it and then clone if you are planning to make changes and contribute them back to the upstream project.

>[!Note]
> There are more detailed installation instructions in the server-related test projects.

## Create a Server Test Project

> [!WARNING]
> This is currently not well-documented. In the future, I may create a project template to make this easier to set up.*

(For now if you decide to do this, please reach out to me to work with you on it.)

This will hold the server-specific code (SAL) and possibly server-specific tests in addition to shared AP tests. It will depend on the `activitypub-testsuite` project. For initial development, you may want to use a *editable* project dependency to the sibling test suite directory.

Other options:
  * Depend on the git repo
  * Create a submodule and depend on that
  * (Currently, the activitypub-testsuite package is not published to PyPi)

---
[Table of Contents](toc.md)

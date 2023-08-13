# ActivityPub Test Suite (activitypub-testsuite)

Server-independent, full-automated test suite primary focused on ActivityPub server compliance testing.

> [!WARNING]
> This is an exploratory proof-of-concept. It works, but if you're looking for a simple, easy-to-use, low effort tool, this isn't it. The current documentation is minimal and mostly intended to support collaboration with server developers rather than to support the creation of new server-specific test support. If there's enough interest, that will change over time.

Note that this project is not a standalone test suite project. It is designed to be used by server-specific test projects that implement test support code (and possibly additional tests) specific to that server.

## Primary Goals

* Server-independent, reusable test framework
* Highly-configurable
* Fully automated
* Supports test isolation
* Supports local testing (no external servers required)
* Reasonably fast

The benefit of server-independence is that the tests can be re-used with multiple server implementation. Currently, the common approach is to write server-specific tests suites with varying degrees of coverage and automation. The test suite is implemented in Python ([`pytest`](https://docs.pytest.org/)), but supports testing servers written in any programming language.

The ActivityPub and ActivityStreams 2 specifications define many optional features and behaviors and there is room for reasonable people to disagree on the interpretation of required behaviors. This framework provides a way to configure the test suite for specific servers so that tests for unsupported features are skipped. Tests related to known bugs can also be skipped and documented, if needed.

There have been a few attempts to write server-independent tools, but they often require manual interaction with the testing tool. This is time consuming and tedious if you need to run the tests many times. The natural tendency for developers will be to take shortcuts in the testing process after they make changes, which can lead to errors in the release code (test regressions). A fully automated test suite is like having a QA team doing detailed testing whenever the code is modified.

For tests to be effective, the pre-test state should be known. Running multiple tests in a single server instance changes the state in ways that can affect subsequent tests (either falsely passing or failing). The tests in this suite are designed to run in a clean server state.

To encourage running the tests often, I want the test suite run as fast as possible while still testing the software effectively. Being integration tests, the test will typically run slower than unit tests, but there are server-specific techniques that can be used to optimize the speed.

Some secondary goals are to make it easy to add new tests and to make it as easy as possible to write a test driver layer for new server implementations.

See also: [Additional Documentation](docs/toc.md)

## Install

See: [Installation documentation](docs//installation.md)

## Usage

TBD

## Contributing

TBD

### License

[MIT License](LICENSE.txt)

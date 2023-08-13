
# Server Testing Strategy

The technique used to implement the Server Abstraction Layer (SAL) for a specific server implementation depends greatly on that server's implementation. The overall goal is to test the ActivityPub behaviors while minimizing overhead associated with non-AP functionality. For example, we don't need to test the TCP/IP stack so simulated network communication may be an option.

However, we don't necessarily want to skip the server-specific network request processing
since there may be errors in that code. For example, it will be less effective to skip all message processing and just test Activity handlers. That is more within the scope of unit testing.

Based on my experience testing various servers, two key considerations are:

1. How will the test suite communicate to the server under test (SUT).
1. How will the server state be reset between each test.

### Server Communication

There are typically two options here:

* Network communication
* Simulated network communication

The first option uses the full network stack to communicate to the server. This may be the only option for servers written in languages other than Python. The server may be run in a subprocess, a VM or container (future).

The second option can sometimes be used for Python-based servers. Here the HTTP endpoints are invoked without using the network stack. This tests the server-specific request processing behavior with starting a subprocess for a testing.

The advantage of the simulated communication is speed, but the disadvantage is that it may require more SAL code to support.

### Resetting Server State

Some options:

* Use an in-memory persistent store
* Reset an external store
* Add a test-related API

Sometimes more than one of these techniques will be required. The goal is to minimize any differences between the test environment and the "production" code while maximizing test effectiveness (coverage, reliability and speed).

#### Example scenarios:

* A node.js server uses sqlite3 for storage. The test environment uses the ":memory:" (in-memory) mode for sqlite3 and rebuilds the database schema for each test. This might require a simple API to force the server to reinitialize the schema for a test.

* A node.js server uses MongoDB for storage. However, it was designed to be modular and has a relatively simple abstract interface for the storage. Implement an in-memory store that replaces the MongoDB store implementation for testing and can be easily reset. Although it might not be difficult to clear the MongoDB containers, it's an extra server process that might be managed during the test execution. This assumes there's no AP-related behaviors that implemented directly in MongoDB queries. The abstract store interface implies this isn't the case.

* A server written in C uses the file system for storage. The storage implementation is not modular. The SAL will reset the file system state for each test. If there is in-memory state, this might require a test API be added to the server implementation to clear it. (Most servers maintain minimal in-memory state outside of persistent storage.)

## Other Considerations

For servers that rely on several external processes (database, Redis, task queue, full-text indexing, etc.), this is going to be much more difficult. It will probably require a VM or a set of containers (with an orchestrator of some kind) to manage the server environment. Implementing the server reset is TBD for this scenario.

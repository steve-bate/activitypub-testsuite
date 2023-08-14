# Test Configuration

[Table of Contents](toc.md)

The test configurations are stored in a TOML file with sections for the server and for individual tests.

## Server-related Configuration

### Server Capabilities

The server capabilities can be used to skip tests automatically if the specified capabilities are not declared. The capabilities are represented as a period-separated identifier where each level of the identifier can have a value defined for it. For example, `a.b.c` could have entries for `a`, `a.b` and `a.b.c`. The default for a level can be set by using the level name with a `.default` suffix. Setting `a.b.default=false`, would set the default for all levels under `a.b` to be false.

**Capability Identifiers**

| Capability            | Type | Description                                                 |
| --------------------- | ---- | ----------------------------------------------------------- |
| `c2s`                 | bool | Client-to-Server (C2S)                                      |
| `c2s.outbox`          | bool | C2S outbox                                                  |
| `c2s.outbox.get`      | bool | C2S outbox GET                                              |
| `c2s.outbox.post`     | bool | C2S outbox POST                                             |
| `c2s.inbox.post.<name>` | bool | Specific C2S Activity type                                |
| `s2s`                 | bool | Server-to-Server (S2S)                                      |
| `s2s.inbox`           | bool | S2S inbox                                                   |
| `s2s.inbox.get`       | bool | S2S inbox GET                                               |
| `s2s.inbox.post`      | bool | S2S inbox POST                                              |
| `s2s.inbox.post.<name>` | bool | A specific S2S Activity type                              |
| `s2s.sharedInbox`     | bool | Shared inboxes                                              |
| `tombstones`          | bool | The server supports Tombstones for deleted objects          |
| `collections`         | bool | Custom collections. Can also configure individual messages. |
| `webfinger`           | bool | Webfinger                                                   |
| `nodeinfo`            | bool | Nodeinfo                                                    |
| `x_nodeinfo_2`        | bool | Nodeinfo2                                                   |
| `host_meta`           | bool | Host Meta                                                   |
| `poco`                | bool | [Portable Contacts](https://indieweb.org/Portable_Contacts) |
| `robots_txt`          | bool | robots.txt                                                  |

### Server Capability Template

```toml
[server.capabilities]
# C2S
# c2s.default = false
# c2s.outbox.default = false
# c2s.outbox.get = false
# c2s.outbox.post = false
# c2s.outbox.post.Create = false
# c2s.outbox.post.Update = false
# c2s.outbox.post.Delete = false
# c2s.outbox.post.Follow = false
# c2s.outbox.post.Add = false
# c2s.outbox.post.Remove = false
# c2s.outbox.post.Like = false
# c2s.outbox.post.Block = false
# c2s.outbox.post.Undo = false

# S2S
# s2s.default = false
# s2s.inbox.default = false
# s2s.inbox.get = false
# s2s.inbox.post = false
# s2s.inbox.post.Create = false
# s2s.inbox.post.Update = false
# s2s.inbox.post.Delete = false
# s2s.inbox.post.Follow = false
# s2s.inbox.post.Accept = false
# s2s.inbox.post.Reject = false
# s2s.inbox.post.Add = false
# s2s.inbox.post.Remove = false
# s2s.inbox.post.Like = false
# s2s.inbox.post.Announce = false
# s2s.inbox.post.Undo = false
# s2s.inbox.shared = false

# Collections support - both spec'ed and custom
# collections.default = false
# collections.following = false
# ... similar for other collection types
# collections.custom = false

# Other AP featuress
# tombstones = false
# Some AP servers don't support standard audience processing
# audience = false

# Other non-AP features
# webfinger = false
# nodeinfo = false
# x-nodeinfo2 = false
# host-meta = false
# portable_contacts = false  # poco
# robots_txt = false
```

## Test Configuration

Depending on the test, there may be test-specific configuration available. For example, in many cases the ActivityPub specification is a bit vague about what HTTP status codes should be used in certain cases and even where a code is suggested, it's not a requirement. It might be an error code or even a success code (for a failure) if the implementer thinks that's good for some reason (security or privacy, for example). The test default may expect a status code based on the specification suggestions or common sense, but it's possible to override these on a per-test basis since there is so much room for developer-specific interpretation in these cases.

The per-test configuration is also stored in the `config.toml` file in a section named after the test. For example:

```toml
[test_nonowner_outbox_post_disallowed]
# Server wants to hide the failure code
status_code = 201
```

If a test is known to fail, then the test runner can be told to skip the test and optionally mark it as a bug. For example:

```toml
[test_outbox_partial_update]
skip = "Only merges. Does not remove properties."
bug = true
```

The `skip` value can be a description or just `true`. The description and the `bug` indicator will be used in test report generation (future).

For parameterized tests, the section will be the `[test_name.parameterized-key]`. This is similar to the `pytest` naming but they put the `parameterize-key` in square brackets. That is awkward with TOML so the square brackets are replaced with a leading period. This also has the advantage of being hierarchical so you can define a test configuration value for all the instances of the parameterized test by just specifying the test name.

----
[Table of Contents](toc.md)

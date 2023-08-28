# Writing Tests

[Table of Contents](toc.md)

## Primary fixtures and methods

There are two primary test fixtures used to write tests.

* `local_actor` - An authenticated actor in the server under test. (also, `local_actor2` for tests that need multiple local actors)
* `remote_actor` - An authenticated actor in a simulated remote server (also, `remote_actor2`, `remote_actor3`, `remote_actor4`)

(There's also an `unauthenticated_actor` for tests that need one.)

Both of these fixtures have similar interfaces but are implemented differently. The most common methods for both are:

| Method | Description |
| ------ | ----------- |
| `make_object` | Create an object (in memory only) |
| `setup_object` | Create a persistent object |
| `make_actvity` | Create an activity (in memory only) |
| `setup_activity` | Create a persistent activity |
| `get_json(url)` | Get a JSON document using the actor's credentials |
| `get(url)` | Do an HTTP request using the actor's credentials |
| `post(url, data)` | Post a JSON document to an HTTP endpoint |

Typically, `make_object` and `make_activity` will be used by the `local_actor` to create an in-memory object to `post` to its `outbox`. If an existing object is necessary (for a `Like` or `Follow`, for example), the that object should be created using `setup_object`, which will cause it to be created in the server's persistent storage.

The `remote_actor` will typically use `setup_object` and `setup_activity`. This will ensure the object can be dereferenced from the remote server simulator by the server under test. If the `remote_actor` uses `make_object` or `make_activity`, the object or activity cannot be dereferenced.

**Example**
```python
def test_example(local_actor, remote_actor):
    activity = local_actor.make_activity(
        {
            # actor, activity type, etc. will gb set automatically
            # default activity type is Create
            # default object type is Note
            "to": remote_actor.id,
            "object": local_actor.make_object(),
        }
    )

    # By default, the post will throw an exception if
    # there's an error response code. The response is
    # returned if the test needs to use it.
    local_actor.post(local_actor.outbox, activity)

    # Remainder of the test...
```

## Polling for asynchronous results

A common pattern is to expect an activity or object to be added to a collection in the server under test. Many servers uses asynchronous processing for the activities so it may not have been processed when the POST operation completes. The test suite has a few utilities for this situation.

The `assert_eventually_in_collection` actor method will poll a collection looking for an object with the specified URI.

**Example**
```python
    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
```

This method is a wrapper for `wait_for_collection_state(uri, predicate)`, which will poll a collection until the predicate is true.

**Example**
```python
        def item_uri_observed(uris):
            return item_uri in uris

        uris = self.wait_for_collection_state(collection_uri, item_uri_observed)
```

These methods operate on the URIs of the collection objects. If you need the object itself, the collection will still need to be dereferenced and the object will need to be located.

---
[Table of Contents](toc.md)

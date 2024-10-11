import pytest

from activitypub_testsuite.ap import AS2_CONTEXT, get_id
from activitypub_testsuite.interfaces import Actor
from activitypub_testsuite.support import dereference

@pytest.mark.skip("FIXME Can't validate cached remote objects")
@pytest.mark.ap_capability("s2s.inbox.post")
def test_remote_dereference(
    remote_actor: Actor,
    local_actor: Actor,
):
    """Tests that a server will dereference an object provided as a URI
    in a posted inbox activity. Basic linked data requirement."""

    remote_object = remote_actor.setup_object({"to": "as:Public"})

    activity = remote_actor.setup_activity(
        {"type": "Create", "object": remote_object["id"], "to": "as:Public"}
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)

    stored_activity = dereference(local_actor, items[0])
    stored_object = dereference(local_actor, stored_activity["object"])
    assert stored_object["id"] == remote_object["id"]


@pytest.mark.ap_capability("s2s.inbox.post")
def test_multityped_activity_is_delivered_to_inbox(
    local_actor2: Actor, local_actor: Actor
):
    """To support extensions, a server is expected to
    process (at least deliver) an AS2 activity with multiple types."""
    activity = local_actor2.setup_activity(
        {
            "@context": [AS2_CONTEXT, {"test": "https://custom.test"}],
            "type": ["Create", "test:InitiateChallenge"],
            "object": "https://custom.test/game",
            "to": local_actor.id,
        }
    )

    local_actor2.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)
    stored_activity = dereference(local_actor, items[0])
    assert set(stored_activity["type"]) == set(activity["type"])


@pytest.mark.ap_capability("s2s.outbox.post")
def test_multityped_activity_is_delivered_to_outbox(local_actor: Actor):
    """To support extensions, a server is expected to
    process (at least deliver) an AS2 activity with multiple types."""
    activity = local_actor.make_activity(
        {
            "@context": [AS2_CONTEXT, {"test": "https://custom.test"}],
            "type": ["Create", "test:InitiateChallenge"],
            "object": {
                "type": "Note",
                "name": "A game",
            },
            "to": "as:Public",
        }
    )

    response = local_actor.post(local_actor.outbox, activity)
    stored_activity = dereference(local_actor, response.headers["Location"])

    local_actor.assert_eventually_in_collection(
        local_actor.outbox, stored_activity["id"]
    )
    items = local_actor.get_collection_item_uris(local_actor.outbox)
    assert items[0] == stored_activity["id"]
    assert set(stored_activity["type"]) == set(activity["type"])


@pytest.mark.ap_capability("s2s.inbox.post")
def test_multityped_object_is_delivered_to_inbox(
    local_actor2: Actor, local_actor: Actor
):
    """To support extensions, a server is expected to
    process (at least deliver) an AS2 object with multiple types."""
    activity = local_actor2.setup_activity(
        {
            "@context": [AS2_CONTEXT, {"test": "https://custom.test"}],
            "type": "Create",
            "object": local_actor2.setup_object(
                {"type": ["Note", "https://custom.test#Frob"]}
            ),
            "to": "as:Public",
        }
    )

    local_actor2.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)
    stored_activity = dereference(local_actor, items[0])
    assert set(stored_activity["type"]) == set(activity["type"])


@pytest.mark.ap_capability("s2s.outbox.post")
def test_multityped_object_is_delivered_to_outbox(local_actor: Actor):
    """To support extensions, a server is expected to
    process (at least deliver) an AS2 activity with multiple types."""
    activity = local_actor.setup_activity(
        {
            "@context": [AS2_CONTEXT, {"test": "https://custom.test"}],
            "type": ["Create"],
            "object": local_actor.setup_object(
                {"type": ["Note", "https://custom.test#Frob"]}
            ),
            "to": "as:Public",
        }
    )

    response = local_actor.post(local_actor.outbox, activity)
    stored_activity = dereference(local_actor, response.headers["Location"])

    local_actor.assert_eventually_in_collection(
        local_actor.outbox, stored_activity["id"]
    )

    stored_object = dereference(local_actor, get_id(stored_activity["object"]))
    assert get_id(stored_activity["object"]) == get_id(stored_object)


@pytest.mark.ap_capability("s2s.inbox.post")
def test_activity_with_multiple_actors(
    remote_actor: Actor,
    local_actor: Actor,
):
    """The ActivityStreams 2.0 specification allows multiple actors for an activity.
    Section 4. Properties. "Describes one or more entities that either
    performed or are expected to perform the activity. Any single activity can
    have multiple actors." [link](https://www.w3.org/TR/activitystreams-vocabulary/#dfn-actor)
    """
    obj = remote_actor.setup_object({"audience": "as:Public"})

    activity = remote_actor.setup_activity(
        {"type": "Create", "object": obj, "audience": "as:Public"}
    )

    activity["actor"] = [activity["actor"], "https://server.test/another_actor"]

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)
    assert len(items) > 0
    # Can't dereference the cached remote objects
    # stored_activity = dereference(local_actor, items[0])
    # assert stored_activity["actor"] == activity["actor"]


def test_activity_with_multiple_objects(
    remote_actor: Actor,
    local_actor: Actor,
):
    """The ActivityStreams 2.0 specification defined "object" as *nonfunctional*
    (can have multiple values)."""
    obj1 = remote_actor.setup_object({"name": "obj1", "audience": "as:Public"})
    obj2 = remote_actor.setup_object({"name": "obj2", "audience": "as:Public"})

    activity = remote_actor.setup_activity(
        {
            "type": "Create",
            "object": [obj1, obj2],
            "audience": "as:Public",
        }
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)
    assert len(items) > 0
    # Can't dereference the cached remote objects
    # stored_activity = dereference(local_actor, items[0])
    # assert dereference(local_actor, stored_activity["object"][0])
    # assert dereference(local_actor, stored_activity["object"][1])
    # assert stored_activity["object"] == activity["object"]

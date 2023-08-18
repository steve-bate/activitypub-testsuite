import pytest

from activitypub_testsuite.ap import AS2_CONTEXT
from activitypub_testsuite.interfaces import Actor
from activitypub_testsuite.support import dereference

# FIXME (C) @tests make this portable
# async def test_inbox_autoaccept_follow(
#     local_actor: Actor,
#     remote_actor: Actor,
#     remote_communicator: RemoteCommunicator,
# ):
#     follow_activity = remote_actor.make_activity(
#         {"type": "Follow", "object": local_actor.id}
#     )

#     ap_plugins.AUTO_ACCEPT_FOLLOW = True
#     try:
#         remote_actor.post(
#             local_actor.inbox,
#             follow_activity,
#         )
#     finally:
#         ap_plugins.AUTO_ACCEPT_FOLLOW = False

#     # Assuming local_actor will use httpx to post response
#     request = next(
#         r for r in remote_communicator.requests if r.url == remote_actor.inbox
#     )
#     post = request.json
#     assert post["type"] == "Accept"
#     assert get_id(post["object"]) == follow_activity["id"]


def test_remote_dereference(
    remote_actor: Actor,
    local_actor: Actor,
):
    """Tests that a server will dereference an object provided as a URI
    in a posted inbox activity. Basic linked data requirement."""

    remote_object = remote_actor.setup_object()

    activity = remote_actor.setup_activity(
        {"type": "Create", "object": remote_object["id"], "audience": "as:Public"}
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)

    stored_activity = dereference(local_actor, items[0])
    stored_object = dereference(local_actor, stored_activity["object"])
    assert stored_object["id"] == remote_object["id"]


@pytest.mark.ap_capability("s2s.inbox.post")
def test_multityped_activity_is_delivered(remote_actor: Actor, local_actor: Actor):
    """To support extensions, a server is expected to
    process (at least deliver) an AS2 activity with multiple types."""
    activity = remote_actor.setup_activity(
        {
            "@context": [AS2_CONTEXT, {"test": "https://custom.test"}],
            "type": ["Create", "test:InitiateChallenge"],
            "object": "https://custom.test/game",
        }
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])
    items = local_actor.get_collection_item_uris(local_actor.inbox)
    stored_activity = dereference(local_actor, items[0])
    assert set(stored_activity["type"]) == set(activity["type"])


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
    stored_activity = dereference(local_actor, items[0])
    assert stored_activity["actor"] == activity["actor"]


@pytest.mark.ap_capability("s2s.inbox.post")
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
    stored_activity = dereference(local_actor, items[0])
    assert dereference(local_actor, stored_activity["object"][0])
    assert dereference(local_actor, stored_activity["object"][1])
    assert stored_activity["object"] == activity["object"]

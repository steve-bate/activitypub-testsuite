from activitypub_testsuite.ap import get_id
from activitypub_testsuite.interfaces import Actor

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

# TODO (B) @tests Need a inbox Create idempotency test.


def test_remote_dereference(
    remote_actor: Actor,
    local_actor: Actor,
):
    # Note that object and activity are not stored in local store

    remote_object = remote_actor.setup_object()

    activity = remote_actor.setup_activity(
        {"type": "Create", "object": remote_object["id"], "audience": "as:Public"}
    )

    remote_actor.post(local_actor.inbox, activity)

    items = local_actor.get_collection_item_uris(local_actor.inbox)
    assert len(items) > 0
    stored_activity = local_actor.get_json(items[0])
    assert stored_activity == activity


# class AuthorizerForTest(AuthorizationService):
#     async def is_activity_authorized(
#         self, principal: ActrillUser, activity: dict[str, Any]
#     ):
#         return AuthzDecision(True, "for testing")


# TODO (C) @tests Test processing of multityped activity
# This needs special authorization support
#
# def test_multityped_activity_is_stored(
#     remote_actor: Actor,
#     local_actor: Actor,
#     assertions: Assertions,
# ):
#     activity = remote_actor.make_activity(
#         {
#             "@context": [AS2_CONTEXT, {"test": "https://custom.test"}],
#             "type": ["Invite", "test:Challenge"],
#             "object": "https://custom.test/game",
#         }
#     )

#     CoreAuthorizationService.next_auth = AuthorizerForTest()

#     remote_actor.post(local_actor.inbox, activity)

#     assertions.collection_contains(
#         local_actor.inbox, activity["id"], auth=local_actor.auth
#     )


def test_activity_with_multiple_actors(
    remote_actor: Actor,
    local_actor: Actor,
):
    obj = remote_actor.setup_object({"audience": "as:Public"})

    activity = remote_actor.setup_activity(
        {"type": "Create", "object": obj, "audience": "as:Public"}
    )

    activity["actor"] = [activity["actor"], "https://server.test/another_actor"]

    remote_actor.post(local_actor.inbox, activity)

    items = local_actor.get_collection_item_uris(local_actor.inbox)
    assert len(items) > 0
    stored_activity = local_actor.get_json(items[0])
    # stored_object = local_actor.get_json(get_id(stored_activity["object"]))
    assert stored_activity["actor"] == activity["actor"]


def test_activity_with_multiple_objects(
    remote_actor: Actor,
    local_actor: Actor,
):
    obj1 = remote_actor.setup_object({"name": "obj1", "audience": "as:Public"})

    obj2 = remote_actor.setup_object({"name": "obj2", "audience": "as:Public"})

    activity = remote_actor.setup_activity(
        {"type": "Create", "object": [obj1, obj2], "audience": "as:Public"}
    )

    remote_actor.post(local_actor.inbox, activity)

    inbox = local_actor.get_collection_item_uris(local_actor.inbox)
    assert activity["id"] in inbox

    items = local_actor.get_collection_item_uris(local_actor.inbox)
    assert len(items) > 0
    stored_activity = local_actor.get_json(items[0])
    local_actor.get_json(get_id(stored_activity["object"][0]))
    local_actor.get_json(get_id(stored_activity["object"][1]))
    assert stored_activity["object"] == activity["object"]

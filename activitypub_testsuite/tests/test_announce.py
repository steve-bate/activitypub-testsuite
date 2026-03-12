import pytest

from activitypub_testsuite.ap import PUBLIC_URI, get_id
from activitypub_testsuite.interfaces import Actor


@pytest.mark.ap_reqlevel("SHOULD")
@pytest.mark.ap_capability("collections.shares")
def test_inbox_share_local_from_remote(
    remote_actor: Actor,
    local_actor: Actor,
):
    """Perform appropriate indication of the like being performed (See 7.10
    for examples)"""

    # AP Section 7.11 TUpon receipt of an Announce activity in an inbox, a server
    # SHOULD increment the object's count of shares by adding the received
    # activity to the shares collection if this collection is present.

    # local actor shares will be processed in the outbox code.
    # A remote actor sharing a local object is tested here.
    # A remote actor sharing of a remote object isn't so clear. Probably should
    # just refresh the local copy of the remote object or the object
    # shares collection (if any).

    shared_object = local_actor.setup_object(
        {
            "type": "Note",
            "to": "as:Public",
        }
    )

    if "shares" in shared_object:
        object_shares_uri = get_id(shared_object["shares"])
    else:
        pytest.skip("No object shares collection support")

    share_activity = remote_actor.make_activity(
        {
            "type": "Announce",
            "actor": remote_actor.id,
            "object": shared_object["id"],
        },
        with_id=True,
    )

    remote_actor.post(local_actor.inbox, share_activity)

    shares = local_actor.get_collection_item_uris(object_shares_uri)
    assert share_activity["id"] in shares


# There is no outbox Announce for some reason ???
#
# @pytest.mark.ap_reqlevel("SHOULD")
# def test_outbox_announce_local(
#     local_actor: Actor, assertions: Assertions
# ):
#     """Adds the object to the actor's Liked Collection."""

#     object_shares_collection = local_actor.setup_collection(name="announce")
#     shared_object = local_actor.setup_object(
#         {
#             "type": "Note",
#             "likes": object_shares_collection["id"],
#             "audience": "as:Public",
#         },
#         with_id=True,
#     )

#     response = local_actor.post(
#         local_actor.outbox,
#         local_actor.make_activity(
#             {
#                 "type": "Announce",
#                 "object": shared_object["id"],
#             }
#         ),
#     )

#     share_activity_uri = response.headers["Location"]

#     assertions.collection_contains(
#         object_shares_collection["id"], share_activity_uri, auth=local_actor.auth
#     )

#     assertions.collection_contains(
#         local_actor.shared, shared_object["id"], auth=local_actor.auth
#     )


@pytest.mark.skip("This requirement is not well-defined")
def test_inbox_undo_announce(
    local_actor: Actor,
    remote_actor: Actor,
):
    # Setup initial state

    # object_shares_collection = remote_actor.setup_collection(
    #     {
    #         "audience": "as:Public",
    #     },
    #     name="shares",
    # )

    shared_object = remote_actor.setup_object(
        {
            "type": "Note",
            # "shares": object_shares_collection["id"],
            "audience": "as:Public",
        }
    )

    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {
                "type": "Create",
                "to": PUBLIC_URI,  # Is this needed since the obj is public?
                "object": shared_object,
            }
        ),
    )

    # A remote actor is announcing a remote object
    share_activity = remote_actor.setup_activity(
        {
            "type": "Announce",
            "object": shared_object["id"],
        }
    )

    remote_actor.post(local_actor.inbox, share_activity)

    # local_actor.post(
    #     local_actor.outbox,
    #     local_actor.make_activity(
    #         {
    #             "type": "Add",
    #             "object": share_activity["id"],
    #             "target": object_shares_uri,
    #         }
    #     ),
    # )

    shared_object = local_actor.get_json(get_id(shared_object))
    shares = local_actor.get_collection_item_uris(shared_object["id"])
    assert share_activity["id"] in shares

    # # setup complete

    # remote_actor.post(
    #     local_actor.inbox,
    #     remote_actor.make_activity(
    #         {
    #             "type": "Undo",
    #             "object": get_id(share_activity),
    #         }
    #     ),
    # )

    # shares = local_actor.get_collection_item_uris(object_shares_uri)
    # assert len(shares) == 0

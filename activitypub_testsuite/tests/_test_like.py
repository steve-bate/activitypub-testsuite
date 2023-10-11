import pytest

from activitypub_testsuite.ap import get_id
from activitypub_testsuite.interfaces import Actor


@pytest.mark.ap_reqlevel("SHOULD")
# some cases need multiactor
@pytest.mark.ap_capability("collections.likes")
def test_inbox_like_local(
    remote_actor: Actor,
    local_actor: Actor,
):
    """Perform appropriate indication of the like being performed (See 7.10
    for examples)"""

    # AP Section 7.10 The side effect of receiving this in an inbox is that the
    # server SHOULD increment the object's count of likes by adding the received
    # activity to the likes collection if this collection is present.

    # A local actor liking an object will be processed in the outbox.
    # A remote actor liking a local object is tested here.
    # A remote actor like of a remote object isn't so clear. Probably should
    # just refresh the local copy of the remote object or the object
    # likes collection (if any).

    local_liked_object = local_actor.setup_object(
        {
            "type": "Note",
            "cc": "as:Public",
        }
    )

    if "likes" not in local_liked_object:
        pytest.skip("No like collection")

    remote_like_activity = remote_actor.setup_activity(
        {
            "type": "Like",
            "actor": remote_actor.id,
            "object": local_liked_object["id"],
        }
    )

    remote_actor.post(local_actor.inbox, remote_like_activity)

    likes = local_actor.get_collection_item_uris(get_id(local_liked_object["likes"]))
    assert remote_like_activity["id"] in likes


@pytest.mark.ap_reqlevel("SHOULD")
@pytest.mark.ap_capability("collections.liked", "collections.likes")
def test_outbox_like_local(local_actor: Actor):
    """Adds the object to the actor's Liked Collection."""

    liked_object = local_actor.setup_object(
        {
            "type": "Note",
            "to": "as:Public",
        },
        with_id=True,
    )

    response = local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {
                "type": "Like",
                "object": liked_object["id"],
            }
        ),
    )

    like_activity_uri = response.headers["Location"]

    local_actor.assert_eventually_in_collection(
        local_actor.liked,
        liked_object["id"],
    )

    if "likes" in liked_object:
        local_actor.assert_eventually_in_collection(
            get_id(liked_object["likes"]),
            like_activity_uri,
        )


# FIXME add capability decorator
def test_inbox_undo_like(
    local_actor: Actor,
    remote_actor: Actor,
):
    # Remote actor likes local object
    # Setup initial state

    local_liked_object = local_actor.setup_object(
        {
            "type": "Note",
            "cc": "as:Public",
        },
        with_id=True,
    )

    if "likes" not in local_liked_object:
        pytest.skip("No like collection")

    remote_like_activity = remote_actor.setup_activity(
        {
            "type": "Like",
            "actor": remote_actor.id,
            "object": local_liked_object["id"],
        },
        with_id=True,
    )

    remote_actor.post(local_actor.inbox, remote_like_activity)

    likes = local_actor.get_collection_item_uris(get_id(local_liked_object["likes"]))
    assert remote_like_activity["id"] in likes

    # Undo the like

    remote_actor.post(
        local_actor.inbox,
        remote_actor.make_activity(
            {
                "type": "Undo",
                "object": remote_like_activity["id"],
            }
        ),
        with_id=True,
    )

    likes = local_actor.get_collection_item_uris(get_id(local_liked_object))
    assert len(likes) == 0


def test_outbox_undo_like(
    local_actor: Actor,
    remote_actor: Actor,
):
    # Local actor likes remote object
    # Setup initial state

    liked_object = remote_actor.setup_object(
        {
            "type": "Note",
            "to": "as:Public",
        },
        with_id=True,
    )

    if "likes" not in liked_object:
        pytest.skip("No like collection")

    # Renote actor tells server that remote object has been created
    remote_actor.post(
        local_actor.inbox,
        {"type": "Create", "object": liked_object},
    )

    # Local actor likes the remote object
    response = local_actor.post(
        local_actor.outbox,
        {
            "type": "Like",
            "object": liked_object["id"],
        },
    )
    like_activity = local_actor.get_json(response.headers["Location"])

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {
                "type": "Undo",
                "object": like_activity["id"],
            },
        ),
    )

    # Smoke test? It's not clear what can be asserted
    # here since the liked remote object is not visible in
    # the local server.

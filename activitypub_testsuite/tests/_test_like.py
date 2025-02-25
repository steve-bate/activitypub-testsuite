import pytest

from activitypub_testsuite.ap import get_id
from activitypub_testsuite.interfaces import Actor


@pytest.mark.ap_capability("s2s.inbox.post.Like")
@pytest.mark.ap_reqlevel("SHOULD")
def test_inbox_like_local(
    remote_actor: Actor,
    local_actor: Actor,
):
    """AP Section 7.10 The side effect of receiving this in an inbox is that the
    server SHOULD increment the object's count of likes by adding the received
    activity to the likes collection if this collection is present.

    A local actor liking an object will be processed in the outbox.
    A remote actor liking a local object is tested here.
    A remote actor like of a remote object isn't so clear. Probably should
    just refresh the local copy of the remote object or the object
    likes collection (if any)."""

    # A remote actor likes a local actor's object

    local_liked_object = local_actor.setup_object(
        {
            "type": "Note",
            "cc": "as:Public",
        }
    )

    if "likes" not in local_liked_object:
        pytest.skip("No likes collection in local object")

    likes_collection_uri = get_id(local_liked_object["likes"])

    remote_like_activity = remote_actor.setup_activity(
        {
            "type": "Like",
            "actor": remote_actor.id,
            "object": local_liked_object["id"],
        }
    )

    remote_actor.post(local_actor.inbox, remote_like_activity)

    local_actor.assert_eventually_in_collection(
        likes_collection_uri, remote_like_activity["id"]
    )


@pytest.mark.ap_capability("s2s.inbox.post.Like")
@pytest.mark.ap_reqlevel("SHOULD")
def test_outbox_like_local(local_actor):
    """AP 6.8 Like Activity. The Like activity indicates the actor likes the object.
    The side effect of receiving this in an outbox is that the server SHOULD
    add the object to the actor's liked Collection."""

    # A local actor likes another local actor's object

    # The local actor must have a liked Collection
    if not local_actor.liked:
        pytest.skip("No liked collection in actor document")

    liked_object = local_actor.setup_object(
        {
            "type": "Note",
            "to": "as:Public",
        },
        with_id=True,
    )

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {
                "type": "Like",
                "object": liked_object["id"],
            }
        ),
    )

    local_actor.assert_eventually_in_collection(
        local_actor.liked,
        liked_object["id"],
    )

    # like_activity_uri = response.headers["Location"]
    # if "likes" in liked_object:
    #     local_actor.assert_eventually_in_collection(
    #         get_id(liked_object["likes"]),
    #         like_activity_uri,
    #     )


@pytest.mark.ap_capability("s2s.inbox.post.Like")
@pytest.mark.ap_reqlevel("SHOULD")
def test_inbox_undo_like(
    local_actor: Actor,
    remote_actor: Actor,
):
    """AP Section 7.10 The side effect of receiving this in an inbox is
    that the server SHOULD increment the object's count of likes by
    adding the received activity to the likes collection if
    this collection is present."""

    # Remote actor undoes like of local object

    local_liked_object = local_actor.setup_object(
        {
            "type": "Note",
            "cc": "as:Public",
        },
        with_id=True,
    )

    # The local actor (server under test) has created a local object
    # This object may or may not have an optional references to a "likes"
    # collection (most don't). If it's not there, the test is skipped.
    if "likes" not in local_liked_object:
        pytest.skip("No likes collection exposed on object")

    likes_collection_uri = get_id(local_liked_object["likes"])

    remote_like_activity = remote_actor.setup_activity(
        {
            "type": "Like",
            "actor": remote_actor.id,
            "object": local_liked_object["id"],
        },
        with_id=True,
    )

    # Remote actor likes the local object
    remote_actor.post(local_actor.inbox, remote_like_activity)

    # Watch for the remote activity URI to be added to the likes collection
    local_actor.assert_eventually_in_collection(
        likes_collection_uri, remote_like_activity["id"]
    )

    # Undo the like

    remote_actor.post(
        local_actor.inbox,
        remote_actor.make_activity(
            {
                "type": "Undo",
                "object": remote_like_activity["id"],
            },
            with_id=True,
        ),
    )

    # There should only be one like, so watch for the like collection size
    # to go to zero.
    local_actor.wait_for_collection_state(
        likes_collection_uri, lambda likes: remote_like_activity["id"] not in likes
    )


@pytest.mark.ap_capability("s2s.inbox.post.Like")
@pytest.mark.ap_capability("s2s.inbox.post.Undo")
def test_outbox_undo_like(
    local_actor: Actor,
    remote_actor: Actor,
):
    # Local actor undoes like of remote object

    # The only specified side-effects are related to the
    # local actor's liked collection. If this is not exposed,
    # then skip the test.
    if not local_actor.liked:
        # TODO Investigate wrapping some of the skips in a MissingCapability exception
        pytest.skip("No liked collection for local actor")

    # Start of test setup

    liked_object = remote_actor.setup_object(
        {
            "type": "Note",
            "to": "as:Public",
        },
        with_id=True,
    )

    # Remote actor tells server that remote object has been created
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {
                "type": "Create",
                "object": liked_object,
            },
            with_id=True,
        ),
    )

    # End of test setup
    # The remote actor has created an object and notified the local
    # actor that it has been created.

    # Local actor likes the remote object
    response = local_actor.post(
        local_actor.outbox,
        {
            "type": "Like",
            "object": liked_object["id"],
        },
    )

    # Should be added to the local actor's "liked" collection
    local_actor.assert_eventually_in_collection(local_actor.liked, liked_object["id"])

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

    # The previously liked object has been removed
    local_actor.wait_for_collection_state(
        local_actor.liked, lambda liked: liked_object["id"] not in liked
    )

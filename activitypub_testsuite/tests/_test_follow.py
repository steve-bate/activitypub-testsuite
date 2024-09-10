import time

import pytest

from activitypub_testsuite.interfaces import Actor, RemoteCommunicator


@pytest.mark.ap_reqlevel("SHOULD")
@pytest.mark.ap_capability(
    "s2s.inbox.post.Accept",
    "collections.following",
)
def test_inbox_accept_local_follow_add_actor_to_following(
    local_actor: Actor, remote_actor: Actor
):
    """If in reply to a Follow activity, adds actor to
    receiver's Following Collection"""

    # Set up pending follow of remote actor
    follow_activity = local_actor.setup_activity(
        {
            "type": "Follow",
            "object": remote_actor.id,
        }
    )

    # Remote actor accepts the follow
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {
                "type": "Accept",
                "object": follow_activity["id"],
            }
        ),
    )

    print(local_actor.following)
    following = local_actor.get_collection_item_uris(local_actor.following)
    assert remote_actor.id in following


@pytest.mark.ap_reqlevel("SHOULD")
@pytest.mark.ap_capability(
    "s2s.inbox.post.Accept",
    "collections.followers",
)
def test_inbox_accept_remote_follow_add_actor_to_followers(
    local_actor: Actor, remote_actor: Actor
):
    """Add the actor to the object user's Followers Collection."""

    follow_activity = remote_actor.setup_activity(
        {
            "type": "Follow",
            "object": local_actor.id,
        }
    )

    remote_actor.post(local_actor.inbox, follow_activity)

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {
                "type": "Accept",
                "object": follow_activity["id"],
            }
        ),
    )

    items = local_actor.get_collection_item_uris(local_actor.followers)
    assert len(items) == 1
    assert remote_actor.id in items


@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability(
    "s2s.inbox.post.Reject",
    "collections.following",
)
def test_inbox_reject_of_local_follow_doesnt_add_actor_to_following(
    local_actor: Actor,
    remote_actor: Actor,
):
    """If in reply to a Follow activity, a Reject MUST NOT add actor to receiver's
    Following Collection"""

    # Set up pending follow of remote actor
    follow = local_actor.setup_activity(
        {
            "type": "Follow",
            "object": remote_actor.id,
        }
    )

    # Remote actor rejects us. So sad. :-(
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {
                "type": "Reject",
                "object": follow["id"],
            }
        ),
    )

    following = local_actor.get_collection_item_uris(local_actor.following)
    assert remote_actor.id not in following


@pytest.mark.ap_capability(
    "s2s.inbox.post.Undo.Follow",
    "collections.followers",
)
def test_inbox_undo_follow(
    remote_actor: Actor, local_actor: Actor, remote_communicator: RemoteCommunicator
):
    follow_activity = remote_actor.setup_activity(
        {
            "type": "Follow",
            "object": local_actor.id,
        }
    )

    # Remote actor request to follow local actor
    remote_actor.post(local_actor.inbox, follow_activity)

    # Local actor accepts remote follow
    local_actor.post(
        local_actor.outbox,
        {
            "type": "Accept",
            "to": remote_actor.id,
            "object": follow_activity["id"],
        },
    )

    # Wait for Accept
    post = remote_communicator.get_most_recent_post()
    assert post.json["type"] == "Accept"

    followers = local_actor.get_collection_item_uris(local_actor.followers)
    assert remote_actor.id in followers

    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {
                "type": "Undo",
                "object": follow_activity,
            }
        ),
    )

    # There's no reply to an undo so we must poll
    for _ in range(5):
        print("POLL")
        followers = local_actor.get_collection_item_uris(local_actor.followers)
        if len(followers) == 0:
            break
        time.sleep(1)

    assert len(followers) == 0, "Follower not removed"


@pytest.mark.ap_capability(
    "s2s.outbox.post.Undo.Follow",
    "collections.following",
)
def test_outbox_undo_follow(local_actor: Actor, remote_actor: Actor):
    follow_activity = local_actor.setup_activity(
        {
            "type": "Follow",
            "object": remote_actor.id,
        }
    )

    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {"type": "Accept", "object": follow_activity["id"]}
        ),
    )

    following = local_actor.get_collection_item_uris(local_actor.following)
    assert remote_actor.id in following

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity({"type": "Undo", "object": follow_activity}),
    )

    following = local_actor.get_collection_item_uris(local_actor.following)
    assert len(following) == 0

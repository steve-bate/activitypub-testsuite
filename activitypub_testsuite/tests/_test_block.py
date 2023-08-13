import pytest


@pytest.mark.ap_capability("c2s.outbox.post.Block")
def test_actor_blocking(local_actor, remote_actor, remote_actor2):
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity({"object": remote_actor.setup_object()}),
    )

    remote_actor2.post(
        local_actor.inbox,
        remote_actor2.setup_activity({"object": remote_actor2.setup_object()}),
    )

    inbox_items = local_actor.get_collection_item_uris(local_actor.inbox)
    assert len(inbox_items) == 2

    # Block the remote_actor
    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity({"type": "Block", "object": remote_actor.id}),
    )

    # Check that block was not delivered

    remote_inbox_items = remote_actor.get_collection_item_uris(remote_actor.inbox)
    assert len(remote_inbox_items) == 0

    # More post attempts

    # This actor should be blocked
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity(
            {
                "object": remote_actor.setup_object(),
                "to": remote_actor2.actor_id,
                "cc": "as:Public",
            }
        ),
        exception=False,
    )

    # Some servers (apex) return a 200 OK for a blocked post
    # TODO (B) @tests Make this status configurable
    # assert response.status_code == HTTPStatus.FORBIDDEN.value

    # This post should not reach the recipient's inbox
    remote_actor2.post(
        local_actor.inbox,
        remote_actor2.setup_activity({"object": remote_actor2.setup_object()}),
    )

    inbox_items = local_actor.get_collection_item_uris(local_actor.inbox)

    # Only one more in the inbox
    assert len(inbox_items) == 3

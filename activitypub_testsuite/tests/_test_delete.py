import time
from http import HTTPStatus

import pytest

from activitypub_testsuite.interfaces import Actor


@pytest.mark.skip("How can internal state of local server be tested for this?")
def test_inbox_delete(remote_actor: Actor, local_actor: Actor):
    obj = remote_actor.setup_object(
        {
            "audience": "Public",
            "attributedTo": remote_actor.id,
        }
    )

    # Able to get the object
    local_actor.get_json(obj["id"])

    # simulate remote deletion
    remote_actor.delete_object(obj["id"])

    remote_actor.post(
        local_actor.inbox,
        remote_actor.make_activity(
            {
                "type": "Delete",
                "object": obj["id"],
            }
        ),
    )

    response = local_actor.get(obj["id"])
    assert response.status_code == HTTPStatus.NOT_FOUND.value


@pytest.mark.ap_capability("s2s.outbox.post.Delete")
def test_outbox_delete(local_actor: Actor):
    obj = local_actor.setup_object(
        {
            "audience": "Public",
            "attributedTo": local_actor.id,
        }
    )

    # Able to get the object
    local_actor.get_json(obj["id"])

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {
                "type": "Delete",
                "object": obj["id"],
            }
        ),
        exception=False,
    )

    # TODO create polling utility
    data = None
    for i in range(5):
        response = local_actor.get(obj["id"])
        if response.is_success:
            # Some servers return tombstone with success code
            if "json" in response.headers["content-type"]:
                data = response.json()
                break
            print(f"polling {i+1}")
            time.sleep(1)
            continue

    if data and "type" in data and data["type"] == "Tombstone":
        tombstone = data
        assert "@context" in tombstone
        assert "id" in tombstone
        assert tombstone["id"] == obj["id"]
        assert "type" in tombstone
    # This is a little looser than what the spec recommends
    assert response.status_code in [
        HTTPStatus.NOT_FOUND.value,
        HTTPStatus.GONE.value,
    ]

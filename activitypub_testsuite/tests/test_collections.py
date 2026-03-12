import pytest

from activitypub_testsuite.interfaces import Actor


@pytest.mark.ap_capability("collections.custom")
def test_inbox_add(remote_actor: Actor, local_actor: Actor):
    collection = remote_actor.setup_collection({"audience": "as:Public"})
    obj = remote_actor.setup_object()

    remote_actor.post(
        local_actor.inbox,
        remote_actor.make_activity(
            {"type": "Add", "object": obj, "target": collection["id"]}
        ),
    )

    item_uris = local_actor.get_collection_item_uris(collection["id"])
    assert obj["id"] in item_uris


@pytest.mark.ap_capability("collections.custom")
def test_inbox_remove(remote_actor: Actor, local_actor: Actor):
    obj = remote_actor.setup_object()
    collection = remote_actor.setup_collection(
        {"audience": "as:Public", "items": [obj["id"]]}
    )

    remote_actor.post(
        local_actor.inbox,
        remote_actor.make_activity(
            {"type": "Remove", "object": obj, "target": collection["id"]}
        ),
    )

    item_uris = local_actor.get_collection_item_uris(collection["id"])
    assert len(item_uris) == 0


@pytest.mark.ap_capability("collections.custom")
def test_outbox_add(local_actor: Actor):
    collection = local_actor.setup_collection({"audience": "as:Public"})
    obj = local_actor.setup_object()

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {"type": "Add", "object": obj, "target": collection["id"]}
        ),
    )

    item_uris = local_actor.get_collection_item_uris(collection["id"])
    assert obj["id"] in item_uris


@pytest.mark.ap_capability("collections.custom")
def test_outbox_remove(local_actor: Actor):
    obj = local_actor.setup_object()
    collection = local_actor.setup_collection(
        {"audience": "as:Public", "items": [obj["id"]]}
    )

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {"type": "Remove", "object": obj, "target": collection["id"]}
        ),
    )

    item_uris = local_actor.get_collection_item_uris(collection["id"])
    assert len(item_uris) == 0

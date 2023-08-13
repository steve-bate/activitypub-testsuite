from http import HTTPStatus

import pytest

from activitypub_testsuite.ap import PUBLIC_VALUES, RECIPIENT_FIELDS, get_id
from activitypub_testsuite.interfaces import Actor


@pytest.mark.parametrize(
    "field,value,value_type",
    [
        (
            (field, value, value_type)
            if field != "audience"
            else pytest.param(
                field,
                value,
                value_type,
                marks=pytest.mark.ap_capability("audience"),
            )
        )
        for field in RECIPIENT_FIELDS
        # test both string and list values
        for value in PUBLIC_VALUES
        for value_type in ["str", "list"]
    ],
    ids=lambda x: x.replace("#", "_"),
)
def test_get_public_object_allowed(
    field: str,
    value: str,
    value_type: str,
    local_actor: Actor,
    remote_actor: Actor,
):
    value = value if value_type == "str" else [value]
    local_obj = local_actor.setup_object({field: value}, with_id=True)
    response = remote_actor.get(local_obj["id"])
    assert response.is_success


def test_get_nonpublic_object_forbidden(
    local_actor: Actor, unauthenticated_actor: Actor
):
    local_obj = local_actor.setup_object()
    response = unauthenticated_actor.get(local_obj["id"])
    assert response.status_code in [
        HTTPStatus.UNAUTHORIZED.value,
        HTTPStatus.FORBIDDEN.value,
    ]


def test_get_object_by_attributedTo(local_actor: Actor):
    local_obj = local_actor.setup_object({"attributedTo": local_actor.id}, with_id=True)
    response = local_actor.get(local_obj["id"])
    assert response.is_success


def test_get_actor_allowed(unauthenticated_actor: Actor, local_actor: Actor):
    response = unauthenticated_actor.get(local_actor.id)
    print(response)
    assert response.is_success


def test_get_outbox_allowed(unauthenticated_actor: Actor, local_actor: Actor):
    response = unauthenticated_actor.get(local_actor.outbox)
    assert response.is_success


def test_get_inbox_nonauth_filtered(
    unauthenticated_actor: Actor,
    remote_actor: Actor,
    local_actor: Actor,
):
    # 2 messages in inbox, one public and one private
    private_obj = remote_actor.setup_object()
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity({"type": "Create", "object": private_obj}),
    )

    public_obj = remote_actor.setup_object(
        {"to": "https://www.w3.org/ns/activitystreams#Public"}
    )
    remote_actor.post(
        local_actor.inbox,
        remote_actor.setup_activity({"type": "Create", "object": public_obj}),
    )

    # Unauthenticated actor should only see one
    response = unauthenticated_actor.get(local_actor.inbox)
    if response.status_code == HTTPStatus.FORBIDDEN.value:
        # We'll allow NO access to inbox by unauthenticated actor
        pass
    elif response.is_success:
        inbox = unauthenticated_actor.get_collection_item_uris(local_actor.inbox)
        assert private_obj["id"] not in inbox


@pytest.mark.parametrize("box", ["inbox", "outbox"])
def test_get_box_by_owner(box: str, local_actor: Actor):
    response = local_actor.get(get_id(local_actor.profile[box]))
    assert response.is_success


def test_get_object_by_posting_actor(local_actor: Actor):
    object_ = local_actor.setup_object({"attributedTo": local_actor.id})
    response = local_actor.get(object_["id"])
    assert response.is_success


def test_anon_inbox_post_disallowed(unauthenticated_actor: Actor, local_actor: Actor):
    activity = unauthenticated_actor.make_activity(
        {"object": unauthenticated_actor.make_object(with_id=True)}, with_id=True
    )
    response = unauthenticated_actor.post(local_actor.inbox, activity, exception=False)
    assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN.value]


def test_nonowner_outbox_post_disallowed(
    local_actor: Actor, local_actor2: Actor, test_config
):
    activity = local_actor.make_activity({"object": local_actor.make_object()})
    response = local_actor.post(local_actor2.outbox, activity, exception=False)
    assert response.status_code == test_config.get("status_code") or (
        response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN.value]
    )

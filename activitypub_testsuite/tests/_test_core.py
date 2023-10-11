# import json
# import time
# from datetime import datetime
# from threading import Barrier, Condition

# import httpx
from http import HTTPStatus
from typing import Any, cast

import pytest

from activitypub_testsuite.ap import (
    ACCEPTED_MEDIA_TYPES,
    ALLOWED_AP_MEDIA_TYPES,
    AS2_CONTEXT,
    SECURITY_CONTEXT,
    assert_id_and_type,
    get_id,
    is_ordered_collection,
)
from activitypub_testsuite.interfaces import Actor
from activitypub_testsuite.support import rfc3339_datetime

# AP Section 3.2 - The HTTP GET method may be dereferenced against
# an object's id property to retrieve the activity.
# (assuming this is a must.)


@pytest.mark.parametrize("media_type", ALLOWED_AP_MEDIA_TYPES)
def test_get_object_allowed_media_types(local_actor: Actor, media_type):
    local_obj = local_actor.setup_object(
        {
            "to": "as:Public",
            "type": "Note",
            "content": "Just a test...",
        },
        with_id=True,
    )
    response = local_actor.get(local_obj["id"], media_type=media_type)
    assert response.is_success
    response_object = response.json()
    # Be sure the payload looks reasonable
    assert response_object["content"] == "Just a test..."
    content_type = response.headers["Content-Type"]
    assert (
        content_type in ACCEPTED_MEDIA_TYPES
        or content_type.split(";")[0] in ACCEPTED_MEDIA_TYPES
    )
    assert_id_and_type(cast(dict[str, Any], response.json()))


# TODO (B) @tests Test missing @context filling
# Move test to activitystreams module

# AS2 Section 2.1.3 When a JSON-LD enabled Activity Streams 2.0
# implementation encounters a JSON document identified using the
# " application/activity+json" MIME media type, and that document
# does not contain a @context property whose value includes a
# reference to the normative Activity Streams 2.0 JSON-LD
# @context definition, the implementation must assume that
# the normative @context definition still applies.
# (Does this apply to other AP media types?)

# AS2 requirement
# Add @context if it's missing


def test_missing_context_is_added(local_actor):
    activity = local_actor.make_activity(
        {
            "type": "Create",
            "object": local_actor.make_object(),
        }
    )
    del activity["@context"]
    del activity["object"]["@context"]
    response = local_actor.post(local_actor.outbox, activity)
    activity_uri = response.headers["Location"]
    activity = local_actor.get_json(activity_uri)
    assert "@context" in activity
    obj = local_actor.get_json(get_id(activity["object"]))
    assert "@context" in obj


@pytest.mark.ap_reqlevel("MUST")
def test_required_actor_properties(local_actor):
    profile = local_actor.get_json(local_actor.id)
    assert profile["id"] == local_actor.id
    assert_id_and_type(profile)
    assert "@context" in profile
    assert AS2_CONTEXT in profile["@context"]
    if "publicKey" in profile:
        assert SECURITY_CONTEXT in profile["@context"]
    assert "inbox" in profile
    assert "outbox" in profile


@pytest.mark.ap_capability("c2s.outbox.get")
def test_outbox_get(local_actor):
    outbox = local_actor.get_json(local_actor.outbox)
    assert outbox is not None  # smoke test


# AP Section 6. Client to server interaction takes place through clients posting
# Activities to an actor's outbox. To do this, clients MUST discover the URL
# of the actor's outbox from their profile and then MUST make an HTTP
# POST request to this URL with the Content-Type of application/ld+json;
# profile="https://www.w3.org/ns/activitystreams".
#
# AP Section 6. unless the activity is transient, MUST include
# the new id in the Location header.
#
# AP Section 6. The server MUST then add this new Activity to the outbox collection.
# Confusing caveat and wording: (However, there is no guarantee that time the Activity
# may appear in the outbox. The Activity might appear after a delay or
# disappear at any period).
# The delay makes sense because of async processing. Not sure about the disappearing
# part. They may be saying that the outbox contains all *non-transient* activities
# produced by an actor.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize("media_type", ALLOWED_AP_MEDIA_TYPES)
def test_outbox_post(local_actor: Actor, media_type: str):
    activity = local_actor.make_activity({"object": local_actor.make_object()})
    response = local_actor.post(local_actor.outbox, activity, media_type=media_type)
    assert response.status_code in [
        200,
        201,
    ]  # TODO (B) @tests Make the status_code configurable
    activity_uri = response.headers["Location"]

    local_actor.assert_eventually_in_collection(local_actor.outbox, activity_uri)


def test_outbox_post_bad_media_type(
    local_actor: Actor,
):
    activity = local_actor.make_activity({"object": local_actor.make_object()})
    response = local_actor.post(
        local_actor.outbox,
        activity,
        media_type="text/plain",
        exception=False,
    )
    assert response.is_error


# AP Section 6.2 When a Create activity is posted, the actor of the activity
# SHOULD be copied onto the object's attributedTo field.
@pytest.mark.ap_reqlevel("SHOULD")
@pytest.mark.parametrize("case", ["with_actor", "without_actor"])
def test_outbox_create_sets_attributedTo(case, local_actor):
    activity = local_actor.make_activity(
        {"type": "Create", "object": local_actor.make_object()}
    )
    if "attributedTo" in activity:
        del activity["attributedTo"]
    if case == "without_actor" and "actor" in activity:
        del activity["actor"]
    response = local_actor.post(local_actor.outbox, activity)
    activity = local_actor.get_json(response.headers["Location"])
    assert "attributedTo" in activity["object"]


# AP Section 6.2 A mismatch between addressing of the Create activity
# and its object is likely to lead to confusion. As such, a server
# SHOULD copy any recipients of the Create activity to its
# object upon initial distribution, and likewise with copying
# recipients from the object to the wrapping Create activity.
@pytest.mark.ap_reqlevel("SHOULD")
def test_outbox_create_merges_recipients(
    # only using one local actor for single user instance-compatibility
    local_actor,
    remote_actor,
    remote_actor2,
    remote_actor3,
    remote_actor4,
):
    activity = local_actor.make_activity(
        {
            "type": "Create",
            "to": remote_actor4.id,
            "cc": remote_actor3.id,
            "bcc": "as:Public",
            "bto": remote_actor.id,
            "audience": local_actor.id,
            "object": local_actor.make_object(
                {"to": remote_actor2.id, "bcc": remote_actor3.id}
            ),
        }
    )
    response = local_actor.post(local_actor.outbox, activity)
    activity = local_actor.get_json(response.headers["Location"])

    def assert_merged_recipients(obj):
        assert isinstance(obj["to"], list) and sorted(obj["to"]) == sorted(
            [remote_actor4.id, remote_actor2.id]
        )
        # TODO (B) @tests Make bcc access by owner configurable
        # bcc cannot be retrieved, even by owner
        # assert sorted(obj["bcc"]) == sorted(["as:Public", remote_actor3.id])
        assert obj["cc"] == remote_actor3.id
        # TODO (B) @tests Make bcc access by owner configurable
        # bto cannot be retrieved, even by owner
        # assert obj["bto"] == remote_actor.id
        assert obj["audience"] == local_actor.id

    assert_merged_recipients(activity)
    obj = local_actor.get_json(get_id(activity["object"]))
    assert_merged_recipients(obj)


# AP Section 5 - An OrderedCollection MUST be presented consistently
# in reverse chronological order.
# AP Section 5.1 - The outbox MUST be an OrderedCollection.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.activity.Create", "c2s.outbox.post", "c2s.outbox.get")
def test_outbox_reverse_chrono(
    local_actor: Actor,
):
    """An OrderedCollection MUST be presented consistently
    in reverse chronological order."""
    activity_ids = []

    for i in range(5):
        activity = local_actor.make_activity(
            {
                "type": "Create",
                "object": local_actor.make_object(),
            }
        )
        response = local_actor.post(local_actor.outbox, activity)
        activity_ids.append(response.headers["Location"])

    outbox = local_actor.get_json(local_actor.outbox)
    assert is_ordered_collection(outbox)

    outbox_items = local_actor.get_collection_item_uris(local_actor.outbox)
    assert outbox_items == list(map(str, reversed(activity_ids)))


# AP Section 6. The request MUST be authenticated with the credentials
# of the user to whom the outbox belongs.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize("other_actor", ["local_actor2", "unauthenticated_actor"])
def test_outbox_authentication(local_actor, other_actor, test_config, request):
    other_actor = request.getfixturevalue(other_actor)
    activity = other_actor.make_activity({"object": other_actor.make_object()})
    # Attempt to post to local_actor outbox, should not be allowed
    response = other_actor.post(local_actor.outbox, activity, exception=False)
    assert response.status_code == test_config.get("status_code") or (
        response.status_code
        in [HTTPStatus.UNAUTHORIZED.value, HTTPStatus.FORBIDDEN.value]
    )


# AP Section 6. If an Activity is submitted with a value in the id property,
# servers MUST ignore this and generate a new id for the Activity.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
def test_outbox_ignore_activity_id(local_actor):
    activity = local_actor.make_activity(
        {"object": local_actor.make_object()},
        with_id=True,
    )
    original_uri = activity["id"]
    response = local_actor.post(local_actor.outbox, activity)
    assert response.is_success
    activity_uri = response.headers["Location"]
    assert original_uri != activity_uri


# AP Section 6.1 - Clients submitting the following activities to
# an outbox MUST provide the object property in the activity:
# Create, Update, Delete, Follow, Add, Remove, Like, Block, Undo.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize(
    ["activity_type", "case"],
    [
        pytest.param(
            activity_type,
            case,
            marks=pytest.mark.ap_capability(f"c2s.outbox.post.{activity_type}"),
        )
        for activity_type in [
            "Create",
            "Update",
            "Delete",
            "Follow",
            "Add",
            "Remove",
            "Like",
            "Block",
            "Undo",
        ]
        for case in ["with_object", "without_object"]
    ],
)
def test_outbox_requires_object_for_certain_activities(
    activity_type: str, case: str, local_actor: Actor, remote_actor: Actor
):
    """Delivers activity with 'object' property if the Activity type is one
    of Create, Update, Delete, Follow, Add, Remove, Like, Block, Undo"""

    with_object = case == "with_object"

    activity_properties = {
        "type": activity_type,
    }

    if with_object:
        if activity_type == "Undo":
            object_ = local_actor.setup_activity(
                {
                    "type": "Follow",
                    "object": remote_actor.id,
                }
            )
        else:
            object_ = local_actor.make_object(
                {
                    "type": "Note",
                    "object": local_actor.id,  # For follow
                    "attributedTo": local_actor.id,
                },
                with_id=False,
            )
            if activity_type != "Create":
                response = local_actor.post(
                    local_actor.outbox,
                    local_actor.make_activity(
                        {
                            "type": "Create",
                            "object": object_,
                        }
                    ),
                )
                create_activity_uri = response.headers["Location"]
                create_activity = local_actor.get_json(create_activity_uri)
                # Retrieve the object with the server-assigned id
                object_ = create_activity["object"]
                if isinstance(object_, str):
                    object_ = local_actor.get_json(object_)

        activity_properties["object"] = object_

    activity = local_actor.make_activity(activity_properties)

    # Add and Remove also require target
    if activity_type in ["Add", "Remove"]:
        collection = local_actor.setup_collection({"attributedTo": local_actor.id})
        activity["target"] = collection["id"]

    # Remove requires the object to have been added to the collection
    if with_object and activity_type == "Remove":
        local_actor.post(
            local_actor.outbox,
            {
                "type": "Add",
                "actor": local_actor.id,
                "object": object_,
                "target": collection["id"],
            },
        )

    response = local_actor.post(local_actor.outbox, activity, exception=False)

    # FIXME (C) @tests Can't assume synchronous processing
    # Response may be success even if object is ignored. Need to poll outbox
    if with_object:
        assert response.is_success
    else:
        assert response.is_error


# AP Section 5.1 - clients submitting the following activities to an outbox
# MUST also provide the target property: Add, Remove.


@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize(
    ["case"],
    [
        pytest.param(
            case,
            marks=pytest.mark.ap_capability(
                "c2s.outbox.post.Add", "collections.custom"
            ),
        )
        for case in ["with_target", "without_target"]
    ],
)
def test_outbox_requires_target_for_add(case: str, local_actor: Actor):
    """Delivers activity with 'target' property if the Activity type is one
    of Add, Remove"""

    with_target = case == "with_target"

    activity = local_actor.make_activity(
        {
            "type": "Add",
            "object": local_actor.make_object(),
        }
    )

    if with_target:
        collection_uri = local_actor.setup_collection({"attributedTo": local_actor.id})
        activity["target"] = collection_uri

    response = local_actor.post(local_actor.outbox, activity, exception=False)

    # FIXME (C) @tests Can't assume synchronous processing
    # Response may be success even if object is ignored. Need to poll outbox
    if with_target:
        assert response.is_success
    else:
        assert response.is_error


@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize(
    ["case"],
    [
        pytest.param(
            case,
            marks=pytest.mark.ap_capability(
                "c2s.outbox.post.Remove", "collections.custom"
            ),
        )
        for case in ["with_target", "without_target"]
    ],
)
def test_outbox_requires_target_for_remove(case: str, local_actor: Actor):
    """Delivers activity with 'target' property if the Activity type is one
    of Add, Remove"""

    with_target = case == "with_target"

    object_ = local_actor.setup_object()

    activity = local_actor.make_activity(
        {
            "type": "Remove",
            "object": object_,
        }
    )

    if with_target:
        collection_uri = local_actor.setup_collection({"attributedTo": local_actor.id})
        activity["target"] = collection_uri
        # Must add object to collection so it can be removed
        # Otherwise, unrelated errors might cause invalid test results
        local_actor.post(
            local_actor.outbox,
            local_actor.make_activity(
                {
                    "type": "Add",
                    "object": object_,
                    "target": collection_uri,
                }
            ),
        )

    response = local_actor.post(local_actor.outbox, activity, exception=False)

    # FIXME (C) @tests Can't assume synchronous processing
    # Response may be success even if object is ignored. Need to poll outbox
    if with_target:
        assert response.is_success
    else:
        assert response.is_error


# AP Section 6.2.1 - The server MUST accept a valid [ActivityStreams]
# object that isn't a subtype of Activity in the POST request to the outbox.
#
# AP Section 6.2.1 - Any to, bto, cc, bcc, and audience properties
# specified on the object MUST be copied over to the new Create activity by the server.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("s2s.outbox-post")
def test_outbox_wraps_object_and_copies_recipients(
    local_actor: Actor,
    remote_actor: Actor,
):
    # These recipients don't make sense but they should not break anything
    obj = local_actor.make_object(
        {
            "to": remote_actor.id,
            "cc": remote_actor.id,
            "bto": remote_actor.id,
            "bcc": [local_actor.id, remote_actor.id],
            "audience": [remote_actor.id, "as:Public"],
            "name": "test object",
        }
    )

    response = local_actor.post(local_actor.outbox, obj)

    activity_uri = response.headers["Location"]
    activity = local_actor.get_json(activity_uri)
    assert activity["type"] == "Create"
    activity_object = activity["object"]
    if isinstance(activity_object, str):
        activity_object = local_actor.get_json(obj)
    assert activity_object["name"] == obj["name"]
    # FIXME (B) @tests The single values could be wrapped in a list
    assert activity["to"] == obj["to"], "wrong to"
    assert activity["cc"] == obj["cc"], "wrong cc"
    # TODO (B) @tests bcc, bto cannot be retrieved even by owner. Make it configurable.
    # assert activity["bto"] == obj["cc"], "wrong bto"
    # assert sorted(activity["bcc"]) == sorted(obj["bcc"]), "wrong bcc"
    assert sorted(activity["audience"]) == sorted(obj["audience"]), "wrong audience"


@pytest.mark.ap_capability("s2s.inbox.get")
def test_inbox_get(local_actor):
    inbox = local_actor.get_collection_item_uris(local_actor.inbox)
    assert inbox is not None  # smoke test


# AP Section 7.1 This Activity is added by the receiver as an item
# in the inbox OrderedCollection.
@pytest.mark.ap_reqlevel("UNSPECIFIED")
@pytest.mark.ap_capability("s2s.inbox.post")
@pytest.mark.parametrize("media_type", ALLOWED_AP_MEDIA_TYPES)
def test_inbox_post(remote_actor, local_actor, media_type: str):
    # No recipients other than inbox owner
    activity = remote_actor.setup_activity(
        {
            "to": local_actor.id,
            "object": remote_actor.make_object({"published": rfc3339_datetime()}),
        }
    )

    activity["object"]["content"] = activity["id"]

    remote_actor.post(local_actor.inbox, activity, media_type=media_type)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])


# AP Section 7.1 An HTTP POST request (with authorization of the submitting user)
# is then made to the inbox, with the Activity as the body of the request.
@pytest.mark.ap_reqlevel("UNSPECIFIED")
@pytest.mark.ap_capability("c2s.outbox.post")
def test_inbox_authorization(local_actor, unauthenticated_actor, test_config):
    # Only authenticated actors can post to inbox
    activity = unauthenticated_actor.make_activity(
        {"object": unauthenticated_actor.make_object(with_id=True)}, with_id=True
    )
    # Attempt to post to local_actor inbox, should not be allowed
    response = unauthenticated_actor.post(local_actor.inbox, activity, exception=False)
    assert (
        # TODO (B) @tests Create a utility for forbidden/unauthorized
        response.status_code
        == test_config.get("expected_status_code", HTTPStatus.FORBIDDEN.value)
        or response.status_code == HTTPStatus.UNAUTHORIZED.value
    )


@pytest.mark.ap_capability("s2s.inbox.post")
def test_inbox_post_bad_media_type(remote_actor, local_actor):
    # No recipients other than inbox owner
    activity = remote_actor.make_activity(
        {
            "to": local_actor.id,
            "object": remote_actor.make_object({"published": rfc3339_datetime()}),
        }
    )

    response = remote_actor.post(
        local_actor.inbox, activity, media_type="text/plain", exception=False
    )

    # FIX specific status code
    assert response.is_error


@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("s2s.activity.Create")
def test_inbox_reverse_chrono(local_actor: Actor, remote_actor: Actor):
    """An OrderedCollection MUST be presented consistently
    in reverse chronological order."""

    activity_ids = []

    for i in range(5):
        activity = remote_actor.setup_activity(
            {
                # Custom ID makes failure diagnosis easier
                "type": "Create",
                "object": remote_actor.setup_object(),
            }
        )
        activity_ids.append(activity["id"])
        remote_actor.post(local_actor.inbox, activity)

    inbox = local_actor.get_json(local_actor.inbox)
    assert is_ordered_collection(inbox)

    inbox_items = local_actor.get_collection_item_uris(local_actor.inbox)

    assert inbox_items == list(map(str, reversed(activity_ids)))


# AP Section 5.1 -- The server MUST perform de-duplication of activities
# returned by the inbox. Such deduplication MUST be performed by comparing
# the id of the activities and dropping any activities already seen
@pytest.mark.ap_reqlevel("MUST")
def test_inbox_accept_deduplicate(local_actor: Actor, remote_actor: Actor):
    """Deduplicates activities returned by the inbox by comparing activity `id`s"""

    activity = remote_actor.setup_activity(
        {
            "type": "Create",
            "object": remote_actor.setup_object(),
            "to": "as:Public",
        }
    )

    # Simulate a double-post of the activity (same IRI)
    remote_actor.post(local_actor.inbox, activity)
    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])

    # Should only be one activity in inbox
    inbox = local_actor.get_collection_item_uris(local_actor.inbox)
    assert inbox == [activity["id"]]

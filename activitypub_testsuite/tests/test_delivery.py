from urllib.parse import urlparse

import pytest

from activitypub_testsuite.ap import ACCEPTED_MEDIA_TYPES, assert_id_and_type
from activitypub_testsuite.interfaces import Actor, RemoteCommunicator


@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize(
    "recipient_key",
    [
        "to",
        "cc",
        "bcc",
        "bto",
        pytest.param("audience", marks=pytest.mark.ap_capability("c2s.audience.delivery")),
    ],
)
def test_outbox_delivery_local(local_actor, recipient_key, local_actor2):
    activity = local_actor.make_activity(
        {
            recipient_key: local_actor2.id,
            "object": local_actor.make_object(),
        }
    )

    response = local_actor.post(local_actor.outbox, activity)
    activity_uri = response.headers["Location"]

    # TODO Review all collection queries to be sure their using polling
    # FIXME This should be using polling
    inbox = local_actor2.get_collection_item_uris(local_actor2.inbox)
    assert activity_uri in inbox


# AP Section 6. The server MUST remove the bto and/or bcc properties,
# if they exist, from the ActivityStreams object before delivery, but MUST
# utilize the addressing originally stored on the bto / bcc properties for
# determining recipients in delivery.
# (need delivery tests)

# For bcc, bto, it's not clear what removing them "for delivery" means
# for local delivery. Does that mean we need another copy of the activity if
# we want to keep the bto, bcc fields for future reference or do we just filter
# the fields during retrieval?
#
# Maybe they mean removing them for retrieval?

# if recipient_key in ["bcc", "bto"]:
#     activity = local_actor2.get(activity_uri)


@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post")
@pytest.mark.parametrize(
    "recipient_key",
    [
        "to",
        "cc",
        "bto",
        "bcc",
        pytest.param("audience", marks=pytest.mark.ap_capability("c2s.audience.delivery")),
    ],
)
def test_outbox_delivery_remote(
    local_actor: Actor,
    recipient_key: str,
    remote_actor: Actor,
    remote_communicator: RemoteCommunicator,
):
    activity = local_actor.make_activity(
        {
            recipient_key: remote_actor.id,
            "object": local_actor.make_object(),
        }
    )

    response = local_actor.post(local_actor.outbox, activity)
    activity_uri = response.headers["Location"]

    # remote_actor inbox should receive a post
    post = remote_communicator.get_most_recent_post()
    assert post is not None, "No post"
    assert post.path == urlparse(remote_actor.inbox).path
    content_type = post.headers["Content-Type"]
    assert (
        content_type in ACCEPTED_MEDIA_TYPES
        or content_type.split(";")[0] in ACCEPTED_MEDIA_TYPES
    )
    delivered_activity = post.json
    assert_id_and_type(delivered_activity)
    assert delivered_activity["id"] == activity_uri


# TODO (B) @review AP Section 7. - Servers performing delivery to the inbox or
# sharedInbox properties of actors on other servers MUST provide the object property
# in the activity: Create, Update, Delete, Follow, Add, Remove, Like, Block, Undo.
# (delivery)

# TODO (B) @review AP Section 7. Additionally, servers performing server to server
# delivery of the following activities MUST also provide
# the target property: Add, Remove.

# TODO (B) @review AP Section 7.1. If a recipient is a Collection or OrderedCollection,
# then the server MUST dereference the collection (with the user's credentials)
# and discover inboxes for each item in the collection.

# TODO (B) @review AP Section 7.1 Servers MUST limit the number of layers of
# indirections through collections which will be performed, which MAY be one.

# TODO (B) @review AP Section 7.1 Servers MUST de-duplicate the final recipient list.

# TODO (B) @review AP Section 7.1 Servers MUST also exclude actors from the list
# which are the same as the actor of the Activity being notified about.
#  That is, actors shouldn't have their own activities delivered to themselves.

# TODO (B) @review 7.1.1 When objects are received in the outbox (for servers which
# support both Client to Server interactions and Server to Server Interactions),
# tthe server MUST target and deliver the: to, bto, cc, bcc or audience fields
# if their values are individuals or Collections owned by the actor.

# TODO (B) @review 7.1.2 Fowarding from inbox. When Activities are received
# in the inbox, the server needs to forward these to recipients that the origin
# was unable to deliver them to. To do this, the server MUST target and deliver to the
# values of to, cc, and/or audience if and only if all of the following are true:
#
# * This is the first time the server has seen this Activity.
# * The values of to, cc, and/or audience contain a Collection owned by the server.
# * The values of inReplyTo, object, target and/or tag are objects owned by the server.
# The server SHOULD recurse through these values to look for linked objects
# owned by the server, and SHOULD set a maximum limit for recursion (ie. the
# point at which the thread is so deep the recipients followers may not mind
# if they are no longer getting updates that don't directly involve the
#  recipient). The server MUST only target the values of to, cc, and/or
# audience on the original object being forwarded, and not pick up any
# new addressees whilst recursing through the linked objects (in case
# these addressees were purposefully amended by or via the client).

# TODO (B) @review AP B.11 - bto and bcc already must be removed for delivery,
# but servers are free to decide how to represent the object
# in their own storage systems.

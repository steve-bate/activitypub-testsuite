"""Tests for the shared inbox (AP 4.1 `endpoints` and AP 7.1.3 delivery)."""

import pytest

from activitypub_testsuite.ap import PUBLIC_URI
from activitypub_testsuite.interfaces import Actor


def shared_inbox_uri(actor: Actor) -> str:
    """The shared inbox the server advertises in the actor document's `endpoints`.

    AP 4.1 defines `sharedInbox` as an endpoint of the actor document, so the address
    is read from the document the server publishes rather than assumed by the test.
    """
    endpoints = actor.profile.get("endpoints") or {}
    uri = endpoints.get("sharedInbox")
    if not isinstance(uri, str) or not uri:
        raise AssertionError("The actor document has no endpoints.sharedInbox (AP 4.1)")
    return uri


# AP 4.1 -- `sharedInbox` endpoints SHOULD also be publicly readable OrderedCollection
# objects containing objects addressed to the Public special collection. Reading from
# the sharedInbox endpoint MUST NOT present objects which are not addressed to the
# Public endpoint.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("s2s.inbox.shared")
def test_shared_inbox_read_presents_only_public_activities(
    local_actor: Actor, local_actor2: Actor, remote_actor: Actor
):
    """The shared inbox presents public activities and no private ones.

    Both activities are accepted through the shared inbox, so the collection that
    omits the private one was delivered the same way as the collection that serves
    the public one.
    """
    shared_inbox = shared_inbox_uri(local_actor)

    public_activity = remote_actor.setup_activity(
        {
            "type": "Create",
            "to": [PUBLIC_URI],
            "cc": [local_actor.id],
            "object": remote_actor.setup_object(),
        }
    )
    remote_actor.post(shared_inbox, public_activity)
    local_actor.assert_eventually_in_collection(
        local_actor.inbox, public_activity["id"]
    )

    # Not public: addressed to one actor only, and delivered through the same inbox.
    private_activity = remote_actor.setup_activity(
        {
            "type": "Create",
            "to": [local_actor2.id],
            "object": remote_actor.setup_object(),
        }
    )
    remote_actor.post(shared_inbox, private_activity)
    local_actor2.assert_eventually_in_collection(
        local_actor2.inbox, private_activity["id"]
    )

    # The addressee reads the shared inbox: the reader most likely to be shown a
    # private activity, and the read that must still not present one.
    presented = local_actor2.get_collection_item_uris(shared_inbox)
    assert public_activity["id"] in presented
    assert private_activity["id"] not in presented, (
        "The shared inbox presented an activity that is not addressed to the Public "
        "collection, to an actor it was addressed to (AP 4.1)"
    )


# AP 7.1.3 -- Origin servers sending publicly addressed activities to `sharedInbox`
# endpoints MUST still deliver to actors and collections otherwise addressed (through
# to, bto, cc, bcc, and audience) which do not have a `sharedInbox` and would not
# otherwise receive the activity through the sharedInbox mechanism.
@pytest.mark.ap_reqlevel("MUST")
@pytest.mark.ap_capability("c2s.outbox.post.delivery.remote", "s2s.inbox.shared")
def test_public_delivery_to_a_shared_inbox_still_reaches_other_addressees(
    local_actor: Actor,
    remote_actor_with_shared_inbox: Actor,
    remote_actor2: Actor,
    remote_communicator,
):
    """A public activity sent to a shared inbox also reaches an addressee without one.

    Both recipients are on the same origin server and both are addressed directly, so
    the shared inbox is the only mechanism that could have replaced either delivery.
    """
    shared_inbox = shared_inbox_uri(remote_actor_with_shared_inbox)

    activity = local_actor.make_activity(
        {
            "type": "Create",
            "to": [PUBLIC_URI, remote_actor_with_shared_inbox.id],
            "cc": [remote_actor2.id],
            "object": local_actor.make_object(),
        }
    )
    activity_uri = local_actor.post(local_actor.outbox, activity).headers["Location"]

    def post_to(uri: str):
        return remote_communicator.get_request(
            lambda request: request.method.lower() == "post" and str(request.url) == uri
        )

    delivered = post_to(shared_inbox)
    assert delivered is not None, "The activity was not delivered to the sharedInbox"
    assert delivered.json["id"] == activity_uri

    delivered = post_to(remote_actor2.inbox)
    assert delivered is not None, (
        "An addressee without a sharedInbox did not receive the publicly addressed "
        "activity that was delivered to a sharedInbox endpoint (AP 7.1.3)"
    )
    assert delivered.json["id"] == activity_uri

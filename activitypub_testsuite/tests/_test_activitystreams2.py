#
# Activity Streams 2.0
#

import pytest

from activitypub_testsuite.ap import SECURITY_CONTEXT
from activitypub_testsuite.interfaces import Actor
from activitypub_testsuite.support import get_id


def test_empty_array_is_omitted_or_null(local_actor: Actor):
    """AS2 Section 2. If a property has an array value, the absence
    of any items in that array must be represented by omitting
    the property entirely or by setting the value to null."""
    inbox = local_actor.get_json(local_actor.inbox)
    if "orderedItems" not in inbox:
        if "first" in inbox:
            inbox = local_actor.get_json(get_id(inbox["first"]))
    if "orderedItems" in inbox:
        assert inbox["orderedItems"] != []
    # Missing orderedItems property is a pass


@pytest.mark.ap_capability("s2s.inbox.post")
def test_assumes_default_context(remote_actor: Actor, local_actor: Actor):
    """AS2 2.1.3 When a JSON-LD enabled Activity Streams 2.0
    implementation encounters a JSON document identified using the
    "application/activity+json" MIME media type, and that document
    does not contain a @context property whose value includes a
    reference to the normative Activity Streams 2.0 JSON-LD @context
    definition, the implementation must assume that the normative
    @context definition still applies."""
    remote_object = remote_actor.setup_object()

    activity = remote_actor.setup_activity(
        {
            "@context": SECURITY_CONTEXT,
            "type": "Create",
            "object": {"id": remote_object["id"], "type": "Note"},
            "audience": "as:Public",
        }
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])


@pytest.mark.skip("TODO Requirement is unclear")
@pytest.mark.ap_capability("s2s.inbox.post", "iri_mapping")
def test_map_iris(remote_actor: Actor, local_actor: Actor):
    """AS2 2.2 - when an IRI that is not also a URI is given
    for dereferencing, it must be mapped to a URI using the
    steps in Section 3.1 of [RFC3987] and (2) when an IRI is
    serving as an "id" value, it must not be so mapped."""

    # This requirement is not clear. It seems that any URI "given"
    # for dereferencing" would be an "id" for some object. It's
    # not clear if "dereferencing" is being used in the sense of
    # retrieval, in general. This test currently assumes that
    # interpretation.

    remote_object = remote_actor.setup_object()
    remote_object["url"] = "https://en.wiktionary.org/wiki/Ῥόδος"
    # maps to...
    # https://en.wiktionary.org/wiki/%E1%BF%AC%CF%8C%CE%B4%CE%BF%CF%82
    # https://en.wikipedia.org/wiki/Internationalized_Resource_Identifier

    activity = remote_actor.setup_activity(
        {
            "type": "Create",
            "object": remote_object["id"],
            "audience": "as:Public",
        }
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])

    # It's not clear what the local actor is expected to do here.

    # local_actor.assert_eventually_in_collection(local_actor.inbox, activity[])
    # inbox = local_actor.get_json(local_actor.inbox)
    # if "orderedItems" not in inbox and "first" in inbox:
    #     inbox = local_actor.get_json(inbox["first"])
    # activity = dereference(local_actor, inbox["orderedItems"][0])
    # obj = dereference(local_actor, activity["object"])
    # mapped_uri = "https://en.wiktionary.org/wiki/%E1%BF%AC%CF%8C%CE%B4%CE%BF%CF%82"
    # assert obj["url"] == mapped_uri


@pytest.mark.ap_capability("s2s.inbox.post", "iri_mapping")
def test_dont_map_iris_for_ids(remote_actor: Actor, local_actor: Actor):
    """AS2 2.2 - when an IRI that is not also a URI is given
    for dereferencing, it must be mapped to a URI using the
    steps in Section 3.1 of [RFC3987] and (2) when an IRI is
    serving as an "id" value, it must not be so mapped."""
    remote_object = remote_actor.setup_object()
    remote_object["id"] = "https://en.wiktionary.org/wiki/Ῥόδος"
    # maps to...
    # https://en.wiktionary.org/wiki/%E1%BF%AC%CF%8C%CE%B4%CE%BF%CF%82
    # https://en.wikipedia.org/wiki/Internationalized_Resource_Identifier

    activity = remote_actor.setup_activity(
        {
            "type": "Create",
            "object": remote_object["id"],
            "audience": "as:Public",
        }
    )

    remote_actor.post(local_actor.inbox, activity)

    local_actor.assert_eventually_in_collection(local_actor.inbox, activity["id"])


# No requirement actually mandates a datetime field in a message
# Ideally we'd automatically check each activity and object being returned by
# the local actor (server under test) for proper date times and not clutter up
# the tests themselves.

# TODO Integrate an activity / object validator that has special checks for dates, etc.

# Is this testable?
# Apparently, the only requirements for link relations is that the string
# is space-delimited and case insensitive. It seems like *any* string will
# be valid without further knowledge of the actual link relation types that
# are expected.
#
# AS2 4.2 - To promote interoperability, Activity Streams
# 2.0 implementations must only use link relations that are
# syntactically valid in terms of both the [RFC5988]
# and [HTML5] definitions.

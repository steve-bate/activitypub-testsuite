import pytest

# AP Section 6.1 - The Update activity is used when updating an already
# existing object. The side effect of this is that the object MUST
# be modified to reflect the new structure as defined in the update activity,
# assuming the actor has permission to update this object.

# AP Section 6.3.1 Partial Updates. For client to server interactions, updates are
# partial; rather than updating the document all at once, any key value pair supplied
# is used to replace the existing value with the new value. This only applies to the
# top-level fields of the updated object. A special exception is for when the value
# is the json null type; this means that this field should be removed from the
# server's representation of the object.


@pytest.mark.ap_reqlevel("NOT_CLEAR")
def test_outbox_partial_update(local_actor):
    original_object = local_actor.setup_object(
        {
            "type": "Note",
            "name": "test note",
            "content": "original content",
            "attributedTo": local_actor.id,
        }
    ).copy()

    local_actor.post(
        local_actor.outbox,
        local_actor.make_activity(
            {
                "type": "Update",
                "object": {
                    "id": original_object["id"],
                    "type": "Note",
                    "summary": "test summary",
                    "name": None,
                    "preview": None,  # Not in original object
                    "content": "modified content",
                },
            }
        ),
    )

    modified_object = local_actor.get_json(original_object["id"])
    assert modified_object["content"] == "modified content"
    assert modified_object["summary"] == "test summary"
    assert "name" not in modified_object


# AP Section 7.3 Update Activity - For server to server interactions,
# an Update activity means that the receiving server SHOULD
# update its copy of the object of the same id to the
# copy supplied in the Update activity. Unlike the
# client to server handling of the Update activity,
# this is not a partial update but a complete replacement of the object.

# The receiving server MUST take care to be sure that the Update
# is authorized to modify its object. At minimum, this may
# be done by ensuring that the Update and its object are of same origin.


@pytest.mark.skip("Requires access to internal local copies of remote objects")
@pytest.mark.ap_reqlevel("SHOULD")
def test_inbox_replace(remote_actor, local_actor):
    original_object = remote_actor.setup_object(
        {
            "type": "Note",
            "name": "test note",
            "content": "original content",
            "attributedTo": remote_actor.id,
            "to": "as:Public",
        }
    )

    updated_object = original_object.copy()
    updated_object.update(
        {
            # Can type and attribution be changed ???
            "id": original_object["id"],
            "summary": "test summary",
            "content": "modified content",
        }
    )
    del updated_object["name"]

    remote_actor.post(
        local_actor.inbox,
        remote_actor.make_activity(
            {
                "type": "Update",
                "object": updated_object,
            }
        ),
    )

    replacement = local_actor.get_json(original_object["id"])
    assert replacement["content"] == "modified content"
    assert replacement["summary"] == "test summary"
    assert replacement["attributedTo"] == remote_actor.id
    assert replacement["cc"] == "as:Public"
    assert "name" not in replacement

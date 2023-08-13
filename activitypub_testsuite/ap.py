"""
Various constants and utilties related to AP/AS2/JSONLD, etc.
"""

from typing import Any, Iterable

PUBLIC_URI = "https://www.w3.org/ns/activitystreams#Public"

DEFAULT_AP_MEDIA_TYPE = (
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
)

ALLOWED_AP_MEDIA_TYPES = {
    DEFAULT_AP_MEDIA_TYPE,
    "application/activity+json",
}

OTHER_AP_MEDIA_TYPES = {
    # TODO (C) @config Support customizing AP media types
    # These is not official AP media type strings but
    # ExpressJS apps seems to provide them.
    "application/ld+json",
}

ACCEPTED_MEDIA_TYPES = set(list(ALLOWED_AP_MEDIA_TYPES) + list(OTHER_AP_MEDIA_TYPES))

AS2_CONTEXT = "https://www.w3.org/ns/activitystreams"
SECURITY_CONTEXT = "https://w3id.org/security/v1"
ACTOR_CONTEXT = [AS2_CONTEXT, SECURITY_CONTEXT]

PUBLIC_VALUES = {
    "Public",
    "as:Public",
    f"{AS2_CONTEXT}#Public",
}

RECIPIENT_FIELDS = {
    "to",
    "bto",
    "cc",
    "bcc",
    "audience",
}

COLLECTION_TYPES = {
    "Collection",
    "CollectionPage",
    "OrderedCollection",
    "OrderedCollectionPage",
}


def get_id(x: dict | str) -> str:
    return x["id"] if isinstance(x, dict) else x


def get_types(activity: dict) -> list[str]:
    types = activity.get("type", [])
    if isinstance(types, str):
        types = [types]
    return types


def is_type(activity, activity_type: str) -> bool:
    types_ = activity["type"]
    return (
        activity_type == types_ if isinstance(types_, str) else activity_type in types_
    )


def is_type_any(activity, activity_types: Iterable[str]) -> bool:
    return any(is_type(activity, t) for t in activity_types)


def is_collection(activity: dict) -> bool:
    return len(set(get_types(activity)).intersection(COLLECTION_TYPES)) > 0


def is_ordered_collection(collection: dict[str, Any]) -> bool:
    return is_type_any(collection, ("OrderedCollection", "OrderedCollectionPage"))


# AP Section 3.1 -- All objects have the following properties: id and type
# (unless intentionally transient)
def assert_id_and_type(obj: dict[str, Any]):
    assert "id" in obj
    assert "type" in obj

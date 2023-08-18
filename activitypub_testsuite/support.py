import socket
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable

from .ap import AS2_CONTEXT, get_id, get_types
from .interfaces import DEFAULT_AP_MEDIA_TYPE, Actor, HttpResponse


class BaseActor(ABC, Actor):
    def __init__(
        self,
        profile: dict[str, Any],
        base_url: str,
        auth: Any = None,
    ):
        self.profile = profile
        self.base_url = base_url
        # A kludge to allow early auth registration
        # Sometimes the auth is needed to get the profile
        # to complete the actor creation.
        if not hasattr(self, "auth"):
            self.auth = auth

    def make_uri(self, for_object: dict[str, Any] | None = None) -> str:
        """Make a IRI with an optional namespace scope"""
        type_ns = "_".join(get_types(for_object)).lower()
        return f"{self.base_url}/{type_ns}/{uuid.uuid4()}"

    def make_object(self, properties: dict | None = None, with_id: bool = True) -> dict:
        """Create a JSON-LD object"""
        object_ = dict(properties or {})
        if "@context" not in object_:
            object_["@context"] = AS2_CONTEXT
        if "type" not in object_:
            object_["type"] = "Note"
        if with_id and "id" not in object_:
            object_["id"] = self.make_uri(object_)
        return object_

    def make_activity(
        self, properties: dict | None = None, with_id: bool = False
    ) -> dict:
        """Make an JSON-LD activity."""
        properties = {} if properties is None else properties
        if "@context" not in properties:
            properties["@context"] = "https://www.w3.org/ns/activitystreams"
        type_ = properties.get("type")
        if not type_:
            type_ = "Create"
            properties["type"] = type_
        if "actor" not in properties:
            properties["actor"] = self.id
        # if "object" not in properties and type_ not in ["Add", "Remove"]:
        #     properties["object"] = self.make_object()
        activity = {
            "@context": AS2_CONTEXT,
        }
        activity.update(properties)
        if with_id and "id" not in activity:
            activity["id"] = self.make_uri(activity)
        return activity

    def setup_activity(
        self, properties: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError()

    def make_collection(
        self,
        properties: dict | None = None,
        ordered: bool = False,
        name: str = "collection",
        collection_type: str = "Collection",
    ) -> str:
        """Make a collection object (no paging)"""
        collection = {}
        # FIXME (B) This should use with_id
        if "id" not in collection:
            collection["id"] = f"{self.id}/{name}/{uuid.uuid4()}"
        type_ = collection.get("type")
        if not type_:
            type_ = "OrderedCollection" if ordered else collection_type
        if "type" not in collection:
            collection["type"] = type_
        ordered = type_.startswith("Ordered")
        items_key = "orderedItems" if ordered else "items"
        if items_key not in collection:
            collection[items_key] = []
        collection["totalItems"] = len(collection[items_key])
        if properties:
            collection.update(properties)
        return collection

    def setup_collection(
        self,
        properties: dict | None = None,
        ordered: bool = False,
        name: str = "collection",
        collection_type: str = "Collection",
        for_object_id: str | None = None,
    ) -> str:
        """Make a collection object and add it to the object storage."""
        # Subclass must implement "persistence"
        raise NotImplementedError()

    def add_to_collection(self, collection_uri: str, item_uri: str) -> None:
        """Add an item to a collection."""
        raise NotImplementedError()

    def wait_for_collection_state(
        self,
        collection_uri,
        state_predicate: Callable[[list[str]], bool],
        tries=5,
        period=1,
    ) -> list[str]:
        """Assert that an item uri shows up in the specified collection.
        This can be async on the server side so polling is required."""
        for _ in range(tries):
            uris = self.get_collection_item_uris(collection_uri)
            if state_predicate(uris):
                break
            time.sleep(period)
        return uris

    def assert_eventually_in_collection(
        self, collection_uri, item_uri, tries=5, period=1
    ):
        def item_uri_observed(uris):
            return item_uri in uris

        uris = self.wait_for_collection_state(collection_uri, item_uri_observed)
        assert item_uri in uris

    def get_collection_item_uris(self, collection_uri: str):
        items = []
        self._get_collection_item_uris(collection_uri, items)
        return items

    def _get_collection_item_uris(
        self,
        collection_uri: str,
        items: list[str],
        max_count: int | None = None,
        count: int = 0,
    ):
        collection = self.get_json(collection_uri)
        for item_key in ["items", "orderedItems"]:
            # We can't rely on the collection "type". It's compliant to
            # have a Collection with orderedItems or a collection with multiple
            # types or even a collection with both items and orderedItems.
            # It might be insane, but... that's a different discussion.
            if item_key in collection:
                i = collection[item_key]
                if not isinstance(i, list):
                    i = [i]
                for item in i:
                    item_uri = get_id(item)
                    if item_uri is not None:
                        items.append(item_uri)
                        count += 1
                        if count == max_count:
                            return
        for page_key in ["first", "next"]:
            if page_key in collection:
                page_uri = get_id(collection[page_key])
                self._get_collection_item_uris(page_uri, items, max_count, count)

    # Object modification

    # TODO (C) @cleanup Check if obj mod methods are still used.
    def add_property(self, subject: str, pred: str, obj: Any) -> None:
        """Add a property to an object."""
        raise NotImplementedError()

    def set_property(self, subject: str, pred: str, obj: Any) -> None:
        """Set a property on an object."""
        raise NotImplementedError()

    def set_properties(self, subject: str, properties: dict) -> None:
        """Set properties on an object."""
        raise NotImplementedError()

    def get_json(self, url: str | dict, proxy=False, exception=True) -> dict:
        """Get an object as a JSON-LD document. Handles authentication."""
        response = self.get(url)
        if response.is_error and exception:
            response.raise_for_status()
        return response.json()

    @property
    def id(self):
        return self.profile["id"]

    @property
    def inbox(self):
        return get_id(self.profile["inbox"])

    @property
    def outbox(self):
        return get_id(self.profile["outbox"])

    @property
    def following(self):
        return get_id(self.profile.get("following"))

    @property
    def followers(self):
        return get_id(self.profile.get("followers"))

    @property
    def liked(self):
        return get_id(self.profile.get("liked"))

    @abstractmethod
    def get(
        self, url: str, proxy: bool = False, media_type: str = DEFAULT_AP_MEDIA_TYPE
    ) -> HttpResponse:
        """Get an object and return the web response. Handles authentication."""
        ...

    @abstractmethod
    def post(
        self, url, data, exception=True, media_type: str = DEFAULT_AP_MEDIA_TYPE
    ) -> HttpResponse:
        """Post a JSON-LD document. Handles authentication."""
        ...


def find_available_tcp_port(start_port: int, end_port: int) -> int | None:
    for port in range(start_port, end_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("localhost", 0))
            return port
        except:  # noqa
            pass
        finally:
            sock.close()
    return None


def dereference(actor: Actor, obj: [dict | str]):
    if isinstance(obj, str):
        return actor.get_json(obj)
    if "type" in obj and obj["type"] == "Link":
        return actor.get_json(obj["href"])
    return obj

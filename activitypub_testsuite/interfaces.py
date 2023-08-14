from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from activitypub_testsuite.ap import DEFAULT_AP_MEDIA_TYPE

URI = str


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int:
        ...

    @property
    def headers(self) -> Mapping[str, str]:
        ...

    def json(self) -> Any:
        ...

    @property
    def is_success(self) -> bool:
        ...

    @property
    def is_error(self) -> bool:
        ...


class HttpRequestError(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response  #


# Simulated Remote Communication
#


@dataclass
class RemoteRequest:
    method: str
    url: str
    path: str
    json: Mapping[str, Any]
    headers: Mapping[str, str]
    kwargs: Mapping[str, Any]


@dataclass
class RemoteResponse:
    method: str
    json: dict[str, Any]
    status_code: int = 200


class RemoteCommunicator(ABC):
    @abstractmethod
    def get_request(self, selector: Callable[..., RemoteRequest]):
        ...

    @abstractmethod
    def get_most_recent_post(self):
        ...


class Actor(Protocol):
    # Tell pytest this is not a test
    __test__ = False

    # @property
    # def auth(self) -> Any:
    #     ...

    def make_uri(self, for_object: dict[str, Any] | None = None) -> str:
        """Make a IRI with an optional namespace scope"""
        ...

    # Create objects and activities

    def make_object(
        self, properties: dict[str, Any] | None = None, with_id: bool = True
    ) -> dict[str, Any]:
        """Create a JSON-LD object"""
        ...

    def setup_object(
        self, properties: dict[str, Any] | None = None, with_id: bool = True
    ) -> dict[str, Any]:
        """Create a JSON-LD object"""
        ...

    def make_activity(
        self, properties: dict[str, Any] | None = None, with_id: bool = False
    ) -> dict[str, Any]:
        """Make an JSON-LD activity."""
        ...

    def setup_activity(
        self, properties: dict[str, Any] | None = None, with_id: bool = False
    ) -> dict[str, Any]:
        """Create a JSON-LD object"""
        ...

    def make_collection(
        self,
        properties: dict | None = None,
        ordered: bool = False,
        name: str = "collection",
        collection_type: str = "Collection",
    ) -> dict[str, Any]:
        """Make a collection object (no paging)"""
        ...

    def setup_collection(
        self,
        properties: dict | None = None,
        ordered: bool = False,
        name: str = "collection",
        collection_type: str = "Collection",
        for_object_id: str | None = None,
    ) -> dict[str, Any]:
        """Make a collection object and add it to the object storage."""
        ...

    def add_to_collection(self, collection_uri: URI, item_uri: URI) -> None:
        """Add an item to a collection."""
        ...

    # Object modification

    def get_collection_item_uris(
        self, collection_uri: URI
    ) -> list[dict[str, Any] | URI]:
        """Get the items from a collection with the actor's credentials"""
        ...

    def assert_eventually_in_collection(
        self, collection_uri, item_uri, tries=5, period=1
    ) -> None:
        """Assert that an item uri shows up in the specified collection.
        This can be async on the server side so polling is required."""

    def wait_for_collection_state(
        self,
        collection_uri,
        state_predicate: Callable[[list[str]], bool],
        tries=5,
        period=1,
    ) -> None:
        """Poll a collection until the state_predicate is true or there is a timeout."""

    # TODO (A) @cleanup These may not be used any more
    def add_property(self, subject: URI, pred: URI, obj: Any) -> None:
        """Add a property to an object."""
        ...

    def set_property(self, subject: URI, pred: URI, obj: Any) -> None:
        """Set a property on an object."""
        ...

    def set_properties(self, subject: URI, properties: dict[str, Any]) -> None:
        """Set properties on an object."""
        ...

    # Network communication

    def get(
        self, url: URI, proxy: bool = False, media_type: str = DEFAULT_AP_MEDIA_TYPE
    ) -> HttpResponse:
        """Get an object and return the web response. Handles authentication."""
        ...

    def get_json(
        self, url: URI, proxy: bool = False, exception: bool = True
    ) -> dict[str, Any]:
        """Get an object as a JSON-LD document. Handles authentication."""
        ...

    def post(
        self, url: str, data: dict[str, Any], exception: bool = True
    ) -> HttpResponse:
        """Post a JSON-LD document. Handles authentication."""
        ...


class ServerTestSupport(Protocol):
    def get_local_actor(self, actor_name: str) -> Actor:
        ...

    def get_remote_actor(self, actor_name: str) -> Actor:
        ...

    def get_unauthenticated_actor(self, actor_name: str) -> Actor:
        ...

    def get_remote_communicator(self) -> RemoteCommunicator:
        ...


class Assertions(Protocol):
    # FIXME (B) @fixtures @cleanup DEPRECATED - Assertions WILL BE REMOVED SOON
    def collection_contains(
        self,
        collection_uri: URI,
        expected_item: URI,
        auth: Any = None,
        proxy: bool = False,
    ):
        """Assert that a stored collection contains an item."""
        # TODO (D) @fixtures determine how to handle auth and proxy behavior
        ...

    def collection_equals(
        self, collection_uri: URI, expected_items: list[URI], auth: Any = None
    ) -> None:
        """Assert the contents of a collection."""
        ...

    def collection_is_empty(self, collection_uri: URI, auth: Any = None) -> None:
        ...

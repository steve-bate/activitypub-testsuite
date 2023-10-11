"""
This is functionality that allows test fixtures to access the
server-under-test as a client.
"""

import os
import uuid
from functools import lru_cache
from http.server import HTTPServer
from threading import Condition
from typing import Any, Callable

import httpx

from activitypub_testsuite.ap import (
    AS2_CONTEXT,
    RECIPIENT_FIELDS,
    SECURITY_CONTEXT,
    get_id,
    get_types,
)
from activitypub_testsuite.http.signatures import HTTPSignatureAuth, get_key_pair
from activitypub_testsuite.interfaces import (
    DEFAULT_AP_MEDIA_TYPE,
    Actor,
    HttpRequestError,
    HttpResponse,
    RemoteCommunicator,
    RemoteRequest,
    ServerTestSupport,
)
from activitypub_testsuite.support import BaseActor


class HttpxServerTestSupport(ServerTestSupport):
    def __init__(
        self,
        local_base_url,
        remote_base_url,
        request,
        *,
        communicator=None,
        default_media_type=DEFAULT_AP_MEDIA_TYPE,
    ):
        self.local_base_url = local_base_url
        self.remote_base_url = remote_base_url
        self._remote_communicator = communicator or HttpxRemoteCommunicator(self)
        self.request = request
        self._httpd = None
        self.default_media_type = default_media_type

    @lru_cache
    def get_local_actor(self, actor_name: str = "local_actor_1") -> Actor:
        return HttpxLocalActor(self, actor_name)

    @property
    def httpd(self) -> HTTPServer:
        # lazy create
        if self._httpd is None:
            self._httpd = self.request.getfixturevalue("remote_http_server")
        return self._httpd

    @lru_cache
    def get_remote_actor(self, actor_name: str = "remote_actor") -> Actor:
        return HttpxRemoteActor(self, actor_name)

    @lru_cache
    def get_unauthenticated_actor(
        self, actor_name: str = "unauthenticated_actor"
    ) -> Actor:
        return HttpxRemoteActor(self, actor_name, authenticated=False)

    def get_remote_communicator(self) -> RemoteCommunicator:
        return self._remote_communicator


class HttpxRemoteCommunicator(RemoteCommunicator):
    def __init__(self, server: HttpxServerTestSupport) -> None:
        self.server = server

    def _wait_for_post(self):
        httpd = self.server.httpd
        # TODO (C) @cleanup improve the post wait function
        # This has evolved in a messy way
        with httpd.post_received:
            if len([r for r in httpd.requests if r.method == "post"]) > 0:
                return
            debugging = os.environ.get("APTEST_DEBUGGING") in ["True", "true", "1"]
            if debugging:
                # Wait forever
                httpd.post_received.wait()
            # TODO (C) @config Make timeout configurable
            elif not httpd.post_received.wait(5):
                raise Exception("No post received in timeout period")

    def get_request(self, selector: Callable[..., RemoteRequest]):
        httpd = self.server.httpd
        self._wait_for_post()
        for request in httpd.requests:
            # Maybe this should be pushed into the HTTPServer?
            if selector(request):
                return request

    def get_most_recent_post(self):
        httpd = self.server.httpd
        self._wait_for_post()
        for request in reversed(httpd.requests):
            # Maybe this should be pushed into the HTTPServer?
            if request.method == "post":
                return request


#
# Methods to help with actor bootstrapping
#


def httpx_get(
    url: str, auth: Any = None, media_type: str = DEFAULT_AP_MEDIA_TYPE
) -> httpx.Response:
    """Get an object and return the web response. Handles authentication."""
    headers = {"Accept": media_type}
    return httpx.get(url, timeout=None, headers=headers, verify=False, auth=auth)


def httpx_get_json(url: str, auth: Any = None, media_type: str = DEFAULT_AP_MEDIA_TYPE):
    response = httpx_get(url, auth, media_type)
    response.raise_for_status()
    return response.json()


class HttpxBaseActor(BaseActor):
    def __init__(
        self,
        server: HttpxServerTestSupport,
        profile: dict,
        auth: Any = None,
    ):
        self.server = server
        super().__init__(profile, server.local_base_url, auth)

    def get(
        self, url: str, proxy: bool = False, media_type: str | None = None
    ) -> HttpResponse:
        """Get an object and return the web response. Handles authentication."""
        return httpx_get(url, self.auth, media_type or self.server.default_media_type)

    def post(
        self, url, data, exception=True, media_type: str | None = None
    ) -> HttpResponse:
        """Post a JSON-LD document. Handles authentication."""
        headers = {
            "Content-Type": media_type or self.server.default_media_type,
        }
        response = httpx.post(
            url,
            json=data,
            headers=headers,
            timeout=None,
            auth=self.auth,
            verify=False,
        )
        if response.is_error and exception:
            raise HttpRequestError(
                f"POST error: {response.status_code} "
                f"{response.reason_phrase} {response.text}",
                response,
            )
        return response

    def setup_object(
        # TODO (C) Revisit whether the setup methods need with_id in the signature
        self,
        properties: dict[str, Any] | None = None,
        with_id: bool = True,
    ) -> dict | str:
        """Create a test object and add it to the object storage."""
        object_ = self.make_object(properties, with_id=False)
        create_activity = self.setup_activity({"type": "Create", "object": object_})
        activity_object = create_activity["object"]
        if isinstance(activity_object, str):
            return self.get_json(activity_object)
        return activity_object

    def setup_activity(
        self, properties: dict[str, Any] | None = None, with_id: bool = False
    ) -> dict:
        activity = self.make_activity(properties, with_id=with_id)
        if "object" in properties:
            object_ = activity["object"]
            if isinstance(object_, dict):
                # TODO (B) This should not be needed. Remove?
                for field in RECIPIENT_FIELDS:
                    if field in object_ and field not in activity:
                        activity[field] = object_[field]
        response = self.post(get_id(self.outbox), activity)
        assert response.is_success, "node server error"
        assert "Location" in response.headers, "Missing Location header"
        stored_activity = self.get_json(response.headers["Location"])
        return stored_activity

    def setup_collection(
        self,
        properties: dict | None = None,
        ordered: bool = False,
        name: str = "collection",
        collection_type: str = "Collection",
        for_object_id: str | None = None,
    ) -> dict[str, Any]:
        """Make a collection object and add it to the object storage."""
        collection = self.make_collection(properties, ordered, name, collection_type)
        create_activity = self.setup_activity({"type": "Create", "object": collection})
        return create_activity["object"]


class HttpxLocalActor(HttpxBaseActor):
    def __init__(
        self, server: HttpxServerTestSupport, actor_name: str, auth: Any = None
    ):
        profile = self.get_profile(server, actor_name)
        super().__init__(server, profile, auth=auth)

    def get_profile(self, server, actor_name) -> dict:
        """Get the actor profile. Create the actor, if needed."""
        actor_uri = self.get_actor_uri(server, actor_name)
        return httpx_get_json(actor_uri)

    def get_actor_uri(self, server, actor_name) -> str:
        raise NotImplementedError()

    def make_collection(
        self,
        properties: dict | None = None,
        ordered: bool = False,
        name: str = "collection",
        collection_type: str = "Collection",
    ) -> str:
        # Remove identifier for local collection -- needs to be fixed
        collection = super().make_collection(properties, ordered, name, collection_type)
        del collection["id"]
        return collection


class HttpxRemoteActor(HttpxBaseActor):
    def __init__(
        self,
        server: HttpxServerTestSupport,
        actor_name: str,
        authenticated: bool = True
        # Local endpoint for serving remote actor requests (host, port)
    ):
        self.actor_base_url = server.remote_base_url
        self.actor_id = f"{server.remote_base_url}/{actor_name}"
        key_id = f"{self.actor_id}#main-key"
        self.public_key, self.private_key = get_key_pair()
        auth = HTTPSignatureAuth(key_id, self.private_key) if authenticated else None
        super().__init__(server, self.get_profile(key_id, actor_name), auth)
        self.httpd = server.httpd
        self.httpd.serve_objects(
            self.profile,
            self._make_ordered_collection("inbox"),
            self._make_ordered_collection("outbox"),
        )

    def _make_ordered_collection(self, name: str):
        return {
            "id": f"{self.actor_id}/{name}",
            "type": "OrderedCollection",
            "attributedTo": self.actor_id,
            "totalItems": 0,
        }

    def make_uri(self, for_object: dict[str, Any] | None = None) -> str:
        """Make a IRI with an optional namespace scope"""
        type_ns = "_".join(get_types(for_object)).lower()
        return f"{self.actor_base_url}/{type_ns}/{uuid.uuid4()}"

    def get_profile(self, key_id: str, actor_name: str):
        return {
            "@context": [AS2_CONTEXT, SECURITY_CONTEXT],
            "id": self.actor_id,
            "type": "Person",
            "inbox": f"{self.actor_id}/inbox",
            "outbox": f"{self.actor_id}/outbox",
            # snac will show the post as anonymous if this is not set
            "preferredUsername": actor_name,
            "publicKey": {
                "id": key_id,
                "owner": self.actor_id,
                "publicKeyPem": self.public_key,
            },
        }

    def expect_request(self):
        self._request_received = Condition()

        def request_monitor(method, handler):
            with self._request_received:
                self._request_received.notify_all()

        self.httpd.listeners.append(request_monitor)

    def wait_for_request(self):
        with self._request_received:
            self._request_received.wait(15)

    def setup_object(
        self, properties: dict[str, Any] | None = None, with_id: bool = True
    ) -> dict | str:
        """Create a test object and add it to the object storage."""
        object_ = self.make_object(properties, with_id=with_id)
        self.httpd.serve_objects(object_)
        return object_

    def delete_object(self, uri: str):
        self.httpd.serve_objects({"id": uri, "type": "Tombstone"})

    def setup_activity(
        self, properties: dict[str, Any] | None = None, with_id: bool = True
    ) -> dict:
        if "id" not in properties:
            activity_type = properties.get("type") or "Create"
            activity_type = (
                "_".join(activity_type)
                if isinstance(activity_type, list)
                else activity_type
            )
            properties["id"] = f"{self.actor_id}/{activity_type}/{uuid.uuid4()}"
        activity = self.make_activity(properties, with_id=with_id)
        self.httpd.serve_objects(activity)
        return activity

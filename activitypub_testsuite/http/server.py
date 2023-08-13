"""
This module implements a simulated AP server for receiving
mesages from the server-under-test.
"""

import asyncio
import http.server
import json
from asyncio import Barrier
from threading import Condition, Thread
from typing import Any, Callable, Tuple
from urllib.parse import urlparse

from activitypub_testsuite.interfaces import RemoteRequest


class HTTPServer(Thread):
    class Server(http.server.HTTPServer):
        def __init__(self, server_action: Callable, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.server_action = server_action

        def server_actions(self):
            self.server_action()

    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def __init__(
            self,
            request,
            client_address,
            server,
            documents,
            requests,
            listeners,
            post_received,
        ):
            self._documents = documents
            self._requests = requests
            self._listeners = listeners
            self._post_received = post_received
            super().__init__(request, client_address, server)

        def do_GET(self):
            netloc = ":".join(map(str, self.server.server_address))
            self._requests.append(
                RemoteRequest(
                    method="get",
                    url=f"http://{netloc}{self.path}",
                    path=self.path,
                    json=None,
                    headers=self.headers,
                    kwargs={},
                )
            )
            obj = self._documents.get(self.path)
            if obj:
                status_code = 200
                if "type" in obj and obj["type"] == "Tombstone":
                    status_code = 410
                self.send_response(status_code)  # Set the response status code
                self.send_header("Content-type", "application/activity+json")
                self.end_headers()
                # print(json.dumps(obj, indent=2))
                self.wfile.write(json.dumps(obj).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"")
            for listener in self._listeners:
                listener("GET", self)

        def do_POST(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            post_payload = json.loads(post_data.encode())
            netloc = ":".join(map(str, self.server.server_address))
            self._requests.append(
                RemoteRequest(
                    method="post",
                    url=f"http://{netloc}{self.path}",
                    path=self.path,
                    json=post_payload,
                    headers=self.headers,
                    kwargs={},
                )
            )
            self.wfile.write('"OK"'.encode())
            for listener in self._listeners:
                listener("POST", self)
            with self._post_received:
                self._post_received.notify_all()

    def __init__(self, host, port):
        Thread.__init__(self)
        self.server_address = (host, port)
        self.httpd = None
        self.httpd_running = Barrier(1)
        self._documents = {}
        self.requests: list[RemoteRequest] = []
        self.listeners = []
        self.post_received = Condition()

    def reset(self):
        self._documents = {}
        self.requests = []
        self.listeners = []
        self.post_received = Condition()

    def serve_objects(self, *objects: Tuple[dict]) -> None:
        for obj in objects:
            self.serve_document(obj["id"], obj)

    def serve_document(self, url: str, document: Any) -> None:
        doc_url = urlparse(url)
        doc_path = doc_url.path
        if doc_url.query:
            doc_path += f"?{doc_url.query}"
        self._documents[doc_path] = document

    def start(self):
        super().start()
        asyncio.run(self.httpd_running.wait())

    def server_action(self):
        self.httpd_running.set()

    def run(self):
        self.httpd = self.Server(
            self.server_action,
            self.server_address,
            lambda *args: self.RequestHandler(
                *args,
                self._documents,
                self.requests,
                self.listeners,
                self.post_received,
            ),
        )
        print("HTTP server started on port", self.server_address[1])
        self.httpd.serve_forever()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()

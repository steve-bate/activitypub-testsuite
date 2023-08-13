# SPDX-FileCopyrightText: © 2023 Dominik George <nik@naturalnet.de>
#
# SPDX-License-Identifier: LGPL-3.0-or-later

from base64 import b64decode, b64encode
from email.utils import formatdate
from functools import lru_cache
from hashlib import sha256
from time import time
from typing import Any, Tuple
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes

try:
    # TODO (C) Clean up the requests usage
    from requests import Request
    from requests.auth import AuthBase
except ModuleNotFoundError:
    Request = Any
    AuthBase = httpx.Auth


# These are slow to create so they are cached
@lru_cache
def get_key_pair(username: str = "shared") -> Tuple[str, str]:
    pair = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )

    return (
        pair.public_key()
        .public_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode(),
        pair.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.PKCS8,
            crypto_serialization.NoEncryption(),
        ).decode(),
    )


class HTTPSignatureAuth(AuthBase):
    _headers: list[str] | None = None

    _key_id: str | None = None
    _private_key: PrivateKeyTypes | None = None

    def __init__(
        self,
        key_id: str,
        private_key: str,
        headers: list[str] | None = None,
    ):
        self._key_id = key_id
        self._headers = headers or ["(request-target)", "host", "date", "digest"]
        self._private_key = crypto_serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            password=None,
            backend=crypto_default_backend(),
        )

    @staticmethod
    def get_signature_fields(signature_header: str) -> dict[str, str]:
        signature_fields = {}
        for field in signature_header.split(","):
            name, value = field.split("=", 1)
            if name in signature_fields:
                raise KeyError(f"Duplicate field {name} in signature")
            signature_fields[name] = value.strip('"')
        return signature_fields

    @classmethod
    def from_signed_request(cls, request: Request) -> str:
        signature_text = None
        if "Signature" in request.headers:
            signature_text = request.headers["Signature"]
        elif "Authorization" in request.headers:
            scheme, parameters = request.headers["Authorization"].split(" ", 1)
            if scheme.lower() == "signature":
                signature_text = parameters
        if signature_text is None:
            raise KeyError("No signature found in headers")
        signature_fields = cls.get_signature_fields(signature_text)

        if "keyId" not in signature_fields:
            raise KeyError("keyId missing in signature")
        if "signature" not in signature_fields:
            raise KeyError("signature missing")

        if "created" in signature_fields:
            created_time = int(signature_fields["created"])
            if created_time > time.time():
                raise ValueError("created time is in the future")

        if "expires" in signature_fields:
            expires_time = int(signature_fields["expires"])
            if expires_time < time.time():
                raise ValueError("expires time is in the past")

        if "headers" in signature_fields:
            headers = signature_fields["headers"].split(" ")
        else:
            headers = ["(created)"]

        return cls(request.state.graph, headers, key_id=signature_fields["keyId"])

    def synthesize_headers(self, request: Request) -> None:
        for header in self._headers:
            if header not in request.headers:
                if header.lower() == "date":
                    request.headers["Date"] = formatdate(
                        timeval=None, localtime=False, usegmt=True
                    )
                elif header.lower() == "digest" and request.content is not None:
                    request.headers["Digest"] = "SHA-256=" + b64encode(
                        sha256(request.content).digest()
                    ).decode("utf-8")
                elif header.lower() == "host":
                    request.headers["Host"] = urlparse(request.url).netloc

    def construct_signature_data(self, request: Request) -> tuple[str, str]:
        signature_data = []
        used_headers = []
        for header in self._headers:
            if header.lower() == "(request-target)":
                method = request.method.lower()
                if hasattr(request, "path_url"):
                    path = request.path_url
                else:
                    path = request.url.path
                signature_data.append(f"(request-target): {method} {path}")
                used_headers.append("(request-target)")
            elif header in request.headers:
                name = header.lower()
                value = request.headers[header]
                signature_data.append(f"{name}: {value}")
                used_headers.append(name)
            else:
                print(self._headers)
                raise KeyError("Header %s not found", header)

        signature_text = "\n".join(signature_data)
        headers_text = " ".join(used_headers)
        return signature_text, headers_text

    async def verify_request(self, request: Request) -> str:
        signature_text, headers_text = self.construct_signature_data(request)

        if headers_text != " ".join(self._headers):
            raise ValueError("Headers listed in signature mismatch with request")

        signature_fields = self.get_signature_fields(request.headers["Signature"])
        signature = b64decode(signature_fields["signature"].encode("utf-8"))

        self._public_key.verify(
            signature,
            signature_text.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        if "digest" in self._headers and request.content is not None:
            body = await request.content
            digest = "SHA-256=" + b64encode(sha256(body).digest()).decode("utf-8")
            if request.headers["Digest"] != digest:
                raise ValueError("Digest of body is invalid")

        return signature_fields["keyId"]

    # FIXME (B) This is a mix of requests and httpx. Should be cleaned up
    def __call__(self, request: Request) -> Request:
        return next(self.auth_flow(request))

    def auth_flow(self, request: Request) -> Request:
        if not self._private_key:
            raise Exception("Private key unknown. Skipping signature.")

        self.synthesize_headers(request)
        signature_text, headers_text = self.construct_signature_data(request)

        signature = b64encode(
            self._private_key.sign(
                signature_text.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
            )
        ).decode("utf-8")

        signature_fields = [
            f'keyId="{self._key_id}"',
            'algorithm="rsa-sha256"',
            f'headers="{headers_text}"',
            f'signature="{signature}"',
        ]

        signature_header = ",".join(signature_fields)

        request.headers["Signature"] = signature_header

        yield request

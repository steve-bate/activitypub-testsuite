import httpx


class HTTPTokenAuth(httpx.Auth):
    def __init__(self, token):
        self.token = token
        self.header = f"Bearer {token}"

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        request.headers["Authorization"] = self.header
        yield request

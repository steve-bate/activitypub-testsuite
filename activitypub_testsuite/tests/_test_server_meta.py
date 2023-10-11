from typing import Callable
from urllib.parse import urlparse

import pytest

from activitypub_testsuite.interfaces import Actor


@pytest.mark.ap_capability("webfinger")
def test_webfinger(
    local_base_url: str,
    local_actor: Actor,
    local_get_json: Callable[[str], dict],
):
    if "alsoKnownAs" in local_actor.profile:
        resource = local_actor.profile["alsoKnownAs"]
    elif "preferredUsername" in local_actor.profile:
        netloc = urlparse(local_base_url).netloc
        username = local_actor.profile["preferredUsername"]
        resource = f"acct:{username}@{netloc}"
    else:
        pytest.fail("Can't determine resource to query")
    # TODO (C) @tests How to locate or generate the webfinger resource identifier
    data = local_get_json(f"{local_base_url}/.well-known/webfinger?resource={resource}")
    assert data["subject"] == resource
    assert any(
        link.get("type") == "application/activity+json" for link in data["links"]
    )
    for link in data["links"]:
        if link.get("type") == "application/activity+json":
            assert link["href"] == local_actor.id


@pytest.mark.ap_capability("nodeinfo")
def test_nodeinfo(local_base_url, local_get_json, instance_metadata):
    data = local_get_json(f"{local_base_url}/.well-known/nodeinfo")
    assert len(data["links"]) > 0
    for link in data["links"]:
        version = link["rel"][link["rel"].rindex("/") + 1 :]
        link_data = local_get_json(link["href"])
        assert link_data["version"] == version
        assert link_data["software"]["name"] == instance_metadata["software"]
        assert "activitypub" in link_data["protocols"]
        for key in ["services", "openRegistrations", "usage", "metadata"]:
            assert key in link_data


@pytest.mark.ap_capability("x-nodeinfo2")
def test_x_nodeinfo2(instance_metadata, local_base_url, local_get_json):
    data = local_get_json(f"{local_base_url}/.well-known/x-nodeinfo2")
    assert data["server"]["baseUrl"] == local_base_url + (
        "/" if not local_base_url.endswith("/") else ""
    )
    assert data["server"]["name"] == instance_metadata["name"]
    assert data["server"]["software"] == instance_metadata["software"]
    assert "activitypub" in data["protocols"]
    assert "openRegistrations" in data


@pytest.mark.ap_capability("host-meta")
def test_host_meta(local_base_url, local_get):
    # Smoke test
    response = local_get(f"{local_base_url}/.well-known/host-meta")
    assert response.is_success


@pytest.mark.ap_capability("robots_txt")
def test_robots_txt(local_base_url, local_get):
    response = local_get(f"{local_base_url}/robots.txt")
    # Smoke test
    assert response.is_success


# Queried by Mastodon (poco)
@pytest.mark.ap_capability("portable_contacts")
def test_portable_contacts(local_base_url, local_get):
    response = local_get(f"{local_base_url}/poco")
    # Smoke test
    assert response.is_success

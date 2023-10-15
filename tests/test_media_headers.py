from activitypub_testsuite.support import (
    MediaDescriptor,
    parse_accept_header,
    parse_content_type,
)


def assert_accept(
    accepted: list[MediaDescriptor],
    i: int,
    media_type: str,
    media_subtype: str,
    q: float,
    # Parameters other than q
    expected_params: dict | None = None,
):
    assert accepted[i].mime_type == media_type
    assert accepted[i].mime_subtype == media_subtype
    assert accepted[i].params["q"] == q
    if expected_params is None:
        # q is always there
        assert len(accepted[i].params) == 1
    else:
        for key, value in expected_params.items():
            if key == "q":
                continue
            assert accepted[i].params.get(key) == value
        assert len(accepted[i].params) == len(expected_params) + 1


def test_accept_header_parsing():
    accepted = parse_accept_header("audio/*; q=0.2, audio/basic")
    assert_accept(accepted, 0, "audio", "basic", 1)
    assert_accept(accepted, 1, "audio", "*", 0.2)
    assert len(accepted) == 2


def test_accept_header_parsing_2():
    accepted = parse_accept_header(
        "text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c"
    )
    assert_accept(accepted, 0, "text", "x-c", 1)
    assert_accept(accepted, 1, "text", "html", 1)
    assert_accept(accepted, 2, "text", "x-dvi", 0.8)
    assert_accept(accepted, 3, "text", "plain", 0.5)
    assert len(accepted) == 4


def test_accept_header_parsing_3():
    accepted = parse_accept_header(
        "text/*;q=0.3, text/html;q=0.7, text/html;level=1, "
        "text/html;level=2;q=0.4, */*;q=0.5"
    )
    assert_accept(accepted, 0, "text", "html", 1, {"level": "1"})
    assert_accept(accepted, 1, "text", "html", 0.7)
    assert_accept(accepted, 2, "*", "*", 0.5)
    assert_accept(accepted, 3, "text", "html", 0.4, {"level": "2"})
    assert_accept(accepted, 4, "text", "*", 0.3)
    assert len(accepted) == 5


def test_content_type_parsing():
    content_type = parse_content_type(
        'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
    )
    assert content_type.mime_type == "application"
    assert content_type.mime_suffix == "json"
    assert content_type.mime_subtype == "ld"
    assert content_type.mime_tree is None
    assert content_type.params["profile"] == "https://www.w3.org/ns/activitystreams"
    assert len(content_type.params) == 1

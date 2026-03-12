def test_server_support(server_support):
    assert server_support is not None


def test_local_actor(server_support):
    actor = server_support.get_local_actor()
    assert actor is not None, "No local actor provided by server support"

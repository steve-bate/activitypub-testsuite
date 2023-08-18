from urllib.parse import quote


def get_metadata_value(test, key, default_value=""):
    metadata = test.get("metadata")
    if metadata:
        value = metadata.get(key)
        if value:
            return value[0] if len(value) == 1 else value
    return default_value


def test_duration(test):
    duration = 0
    for stage in ["setup", "call", "teardown"]:
        if stage in test:
            duration += test[stage]["duration"]
    return duration


def format_duration(x):
    return format(x, "0.3f" if x > 0.001 else "0.6f")


def test_name(test):
    return test["nodeid"].split("::")[1] if "::" in test["nodeid"] else test["nodeid"]


def test_slug(test):
    return quote(test_name(test))


def configure_filters(template_env):
    template_env.filters["test_name"] = test_name
    template_env.filters["test_slug"] = test_slug
    template_env.filters["metadata_value"] = get_metadata_value
    template_env.filters["test_duration"] = test_duration
    template_env.filters["format_duration"] = format_duration

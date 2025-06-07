import asyncio
import glob
import os
import re
import socketserver
import subprocess
import sys
import tomllib
from collections import ChainMap
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from threading import Event, Thread
from typing import Any, Callable, Coroutine, Mapping
from urllib.parse import urlparse

import dictlib
import pytest
from pytest_metadata.plugin import metadata_key

from activitypub_testsuite import tests
from activitypub_testsuite.http.client import httpx_get
from activitypub_testsuite.http.server import HTTPServer
from activitypub_testsuite.support import find_available_tcp_port

from .interfaces import Actor, RemoteCommunicator, ServerTestSupport


@pytest.fixture
def server_support() -> ServerTestSupport:
    raise NotImplementedError("Must implement server test support")


@pytest.fixture(scope="session")
def server_test_directory():
    raise NotImplementedError("server_test_directory fixture is required")


# Local server


@pytest.fixture(scope="session")
def local_server_port() -> int:
    return find_available_tcp_port(50000, 51000)


@pytest.fixture(scope="session")
def local_server_url_scheme():
    return "http"


@pytest.fixture(scope="session")
def local_base_url(local_server_port, local_server_url_scheme):
    return f"{local_server_url_scheme}://localhost:{local_server_port}"


# Local actor clients


@pytest.fixture
def local_actor(server_support) -> Actor:
    return server_support.get_local_actor("local_actor")


@pytest.fixture
def local_actor2(server_support) -> Actor:
    return server_support.get_local_actor("local_actor_2")


# Can be overridden in project-specific configs for servers that
# use other techniques.
@pytest.fixture
def local_get():
    def _get(url: str, media_type: str = "application/json"):
        response = httpx_get(url, media_type=media_type)
        response.raise_for_status()
        return response

    return _get


@pytest.fixture
def local_get_json(local_get):
    def _get_json(url: str, media_type: str = "application/json"):
        response = local_get(url, media_type)
        return response.json()

    return _get_json


# Remote actors


@pytest.fixture
def remote_actor(server_support) -> Actor:
    return server_support.get_remote_actor()


@pytest.fixture
def remote_actor2(server_support) -> Actor:
    return server_support.get_remote_actor("remote_actor2")


@pytest.fixture
def remote_actor3(server_support) -> Actor:
    return server_support.get_remote_actor("remote_actor3")


@pytest.fixture
def remote_actor4(server_support) -> Actor:
    return server_support.get_remote_actor("remote_actor4")


@pytest.fixture
def unauthenticated_actor(server_support) -> Actor:
    return server_support.get_unauthenticated_actor()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.stop()
    loop.close()


@pytest.fixture
def asynctosync(event_loop):
    def _asynctosync(coro: Coroutine):
        def sync_adapter(*args, **kwargs):
            future = coro if isinstance(coro, Coroutine) else coro(*args, **kwargs)
            try:
                return event_loop.run_until_complete(future)
            finally:
                pending_tasks = asyncio.all_tasks(event_loop)
                event_loop.run_until_complete(asyncio.gather(*pending_tasks))

        return sync_adapter

    return _asynctosync


@pytest.fixture(scope="session")
def remote_base_url(testsuite_config):
    server_config = testsuite_config.get("server", {})
    url = server_config.get("remote_base_url")
    if url:
        return url
    port = find_available_tcp_port(54000, 55000)
    return f"http://localhost:{port}"


@pytest.fixture
def remote_communicator(server_support) -> RemoteCommunicator:
    return server_support.get_remote_communicator()


# Use this to determine if fixture was created
_remote_http_server = None

# TODO (C) @fixtures Consider starting this on-demand and then stopping it
# in pytest_sessionfinish


@pytest.fixture(scope="session")
def remote_http_server(remote_base_url):
    global _remote_http_server
    url = urlparse(remote_base_url)
    print(f"test: starting http server: {remote_base_url}")
    httpd = HTTPServer(url.hostname, url.port)
    socketserver.TCPServer.allow_reuse_address = True
    httpd.start()
    _remote_http_server = httpd
    yield httpd
    print("test: stopping http server")
    httpd.stop()
    _remote_http_server = None


@pytest.fixture(autouse=True)
def reset_remote_http_server():
    # The global is needed because if reset_http_server
    # depends on http_srever, it will trigger the creation
    # of the http_server fixture unnecessary for skipped tests
    # (and lead to some other race conditions.)
    if _remote_http_server:
        _remote_http_server.reset()


# It can be useful to manually start the node server
# to run in a debugger.
AUTO_START_LOCAL_SERVER = os.environ.get("AUTO_START_LOCAL_SERVER") not in [
    "False",
    "false",
    "0",
]


@dataclass
class ServerSubprocessConfig:
    args: list[str]
    cwd: str
    start_matcher: Callable[[str], bool] | None = None
    error_matcher: Callable[[str], bool] | None = None


_server_error: bool = False


def monitor_server_output(
    server: subprocess.Popen,
    start_event: Event,
    config: ServerSubprocessConfig,
):
    def readline():
        global _server_error
        line = server.stdout.readline().decode()
        if config.error_matcher and config.error_matcher(line):
            _server_error = True
            raise Exception(f"local server error detected: {line}")
        return line

    line = readline()
    sys.stdout.write(f"local server: {line}")
    try:
        if config.start_matcher:
            while not config.start_matcher(line):
                line = readline()
                sys.stdout.write(f"local server (pending match): {line}")
        start_event.set()
        while line:
            line = readline()
            sys.stdout.write(f"local server: {line}")
    except:  # noqa
        print(f"test: server error: {sys.exc_info()}")
    finally:
        print("test: server monitoring thread exit")


@pytest.fixture(scope="session", autouse=True)
def local_server_subprocess(request) -> subprocess.Popen[str]:
    if AUTO_START_LOCAL_SERVER:
        # If there is a server config, then start the server
        try:
            server_config = request.getfixturevalue("server_subprocess_config")
            with subprocess.Popen(
                server_config.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=server_config.cwd,
            ) as server:
                start_event = Event()
                server_output_thread = Thread(
                    target=monitor_server_output,
                    args=[server, start_event, server_config],
                )
                server_output_thread.start()
                start_event.wait(10)
                print("test: server subprocess started")
                yield server
                server.kill()
                server_output_thread.join(10)
                print("test: server subprocess  stopped")
        except pytest.FixtureLookupError:
            # No fixture, we don't start the server
            yield
    else:
        yield


@pytest.fixture(autouse=True)
def check_server_state(test_config):
    global _server_error
    _server_error = False
    yield
    if "xfail" not in test_config and _server_error:
        pytest.fail("Server error detected")


def install_as_link():
    test_dir = os.path.dirname(tests.__file__)
    for src_file in sorted(glob.glob(os.path.join(test_dir, "_test*.py"))):
        src_file = src_file
        dest_file = re.sub("^_test_", "test_fedi_", os.path.basename(src_file))
        if not os.path.exists(dest_file):
            os.symlink(src_file, dest_file)
            print(f"Linked {dest_file}")


# TODO (C) @fixtures will need a 2-way sync for this?
def install_fedi_tests(test_dir: str):
    """Install AP/Fedi tests into the specified directory"""
    try:
        cwd = os.getcwd()
        os.chdir(test_dir)
        install_as_link()
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="session")
def testsuite_config(server_test_directory):
    config_path = os.path.join(server_test_directory, "config.toml")
    if os.path.exists(config_path):
        with open(config_path, "rb") as fp:
            return tomllib.load(fp)
    return {}


@pytest.fixture
def test_config(request, testsuite_config) -> Mapping:
    test_name = request.node.name
    if "[" not in test_name:
        return testsuite_config.get(test_name) or {}
    else:
        configs = []
        m = re.match(r"(.*)\[(.*)]", test_name)
        if m.group(1) in testsuite_config:
            config = testsuite_config[m.group(1)]
            configs.append(config)
            if m.group(2) in config:
                configs.insert(0, config[m.group(2)])
        return ChainMap(*configs)


@pytest.fixture(autouse=True)
def conditionally_skip_test(request: pytest.FixtureRequest, test_config: Mapping):
    if test_config:
        # Resolve chained maps
        request.node.stash["config"] = dict(test_config)
    skip = test_config.get("skip")
    if skip:
        pytest.skip(skip if isinstance(skip, str) else "(configured)")
    xfail = test_config.get("xfail")  # expected failure
    if xfail:
        pytest.xfail(xfail if isinstance(xfail, str) else "(configured)")


def dig(data: dict, key: str, default_value: Any = None):
    try:
        return dictlib.dig(data, key)
    except KeyError:
        return default_value


def is_env_set(key: str, default_value: Any = None):
    if key not in os.environ:
        return default_value
    return str().lower(os.environ.get(key)) in ["true", "1"]


@pytest.fixture  # can be overridden in project-specific config
def fail_on_unknown_capability() -> bool:
    return is_env_set("APTEST_STRICT_CAPABILITIES", False)


@pytest.fixture(autouse=True)
def skip_without_server_capabilities(
    testsuite_config,
    request: pytest.FixtureRequest,
    fail_on_unknown_capability: bool,
):
    capabilities = dig(testsuite_config, "server.capabilities")
    if capabilities:
        for marker in request.node.iter_markers("ap_capability"):
            for capability_id in marker.args:
                capability = None
                while capability is None:
                    capability = dig(capabilities, capability_id)
                    if capability is None or isinstance(capability, dict):
                        capability = dig(capabilities, f"{capability_id}.default")
                    if capability is None:
                        if "." in capability_id:
                            capability_id = capability_id[: capability_id.rfind(".")]
                            continue
                        else:
                            break
                if capability is None and fail_on_unknown_capability:
                    # Otherwise, assume capabilities not mentioned in config
                    pytest.fail(f"Server capability not specified: {marker.args[0]}")
                if isinstance(capability, bool) and not capability:
                    pytest.skip(
                        reason=f"Missing required server capability: {marker.args[0]}"
                    )


#
#  Test metadata
#

# This is to compensate for a known unfixed bug in the json report library.
# I wasn't motivated enough to fork the repo and fix it.
# If there are side-effects of doing this, then I'll reconsider.
CONFIG = None

PROJECT_METADATA = None


@pytest.fixture(scope="session", autouse=True)
def store_report_project_metadata(report_project_metadata):
    global PROJECT_METADATA
    PROJECT_METADATA = report_project_metadata


def pytest_runtestloop(session):
    global CONFIG
    CONFIG = session.config


@pytest.hookimpl(optionalhook=True)
def pytest_json_modifyreport(json_report):
    if CONFIG:
        env = json_report["environment"]
        if PROJECT_METADATA:
            env["Project"] = PROJECT_METADATA
        env["StartTime"] = datetime.now(timezone.utc).astimezone().isoformat()
        env.update(CONFIG.stash[metadata_key])
        packages = env["Packages"]
        packages["activitypub-testsuite"] = package_version("activitypub-testsuite")
        try:
            server_package = os.path.basename(CONFIG.rootpath)
            packages[server_package] = package_version(server_package)
        except:  # noqa
            pass


@pytest.hookimpl(optionalhook=True)
def pytest_json_runtest_stage(report: pytest.TestReport):
    # Apparently accessing skip and xfail data is not well-supported
    # by pytest, hence these kludges.
    if report.outcome == "skipped":
        metadata = report._json_report_extra.get("metadata")
        if metadata is None:
            metadata = {}
            report._json_report_extra["metadata"] = metadata
        if not hasattr(report, "wasxfail"):
            metadata["reason"] = report.longrepr[2].replace("Skipped: ", "")
        else:
            metadata["reason"] = report.wasxfail.replace("reason: ", "")


@pytest.hookimpl(optionalhook=True)
def pytest_json_runtest_metadata(item, call):
    if call.when == "setup":
        metadata = {}
        if "config" in item.stash:
            metadata["config"] = item.stash["config"]

        def append(key, value):
            if key not in metadata:
                metadata[key] = value
            else:
                metadata[key] += value

        if isinstance(item, pytest.Function):
            fn_name = item.name
            if "[" in fn_name:
                fn_name = fn_name[: fn_name.index("[")]
            fn = getattr(item.module, fn_name)
            if fn.__doc__:
                metadata["documentation"] = fn.__doc__
        for marker in item.iter_markers():
            if marker.name in ["ap_reqlevel", "ap_capability"]:
                append(marker.name, marker.args)

        return metadata


@pytest.fixture(autouse=True)
def record_parametrize_data(json_metadata, request):
    if "pytestmark" in request.node.keywords:
        parametrize_marks = [
            m for m in request.node.keywords["pytestmark"] if m.name == "parametrize"
        ]
        if parametrize_marks:
            mark = parametrize_marks[0]
            param_data = mark.args
            param_names = (
                param_data[0].split(",")
                if isinstance(param_data[0], str)
                else param_data[0]
            )
            json_metadata["params"] = {
                p: request.getfixturevalue(p) for p in param_names
            }


@pytest.fixture(scope="session")
def report_project_metadata():
    # Anything in this dictionary will be added to the
    # first metadata table for the test session. Some
    # recommended data:
    #
    #   - "Project Name"
    #   - "Project Description"
    #   - "Project URL"
    #   - "Project Notes"
    return None

"""Plugin-only ASGI composition without a GsCore or project-runtime installation."""

import importlib.util
import json
import sys
from functools import wraps
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "adapters/Dota2UID/src/Dota2UID/host_config.py.template"
SDK = Path(__file__).with_name("_config_sdk.py")
CANARY = "synthetic-config-secret-canary"
PAYLOAD = json.dumps({"value": CANARY, "default": CANARY, "secret": True}).encode()


def async_test(function):
    @wraps(function)
    def run(*args, **kwargs):
        coroutine = function(*args, **kwargs)
        try:
            coroutine.send(None)
        except StopIteration as complete:
            return complete.value
        finally:
            coroutine.close()
        raise AssertionError("synthetic ASGI execution unexpectedly suspended")

    return run


@pytest.fixture
def guard(tmp_path, monkeypatch):
    helper_name = "synthetic_trace_guard_sdk"
    spec = importlib.util.spec_from_file_location(helper_name, SDK)
    helper = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, helper_name, helper)
    spec.loader.exec_module(helper)
    helper.install_config_sdk(monkeypatch)
    source = tmp_path / "host_config.py"
    source.write_bytes(SOURCE.read_bytes())

    def load(name="synthetic_trace_guard"):
        spec = importlib.util.spec_from_file_location(name, source)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    return SimpleNamespace(module=load(), load=load)


class Middleware:
    def __init__(self, cls, *args, **kwargs):
        self.cls, self.args, self.kwargs = cls, args, kwargs


class SurroundingMiddleware:
    def __init__(self, app, events, name):
        self.app, self.events, self.name = app, events, name

    async def __call__(self, scope, receive, send):
        self.events.append(self.name)
        await self.app(scope, receive, send)


class HttpTraceMiddleware:
    def __init__(self, app, events, *args, **kwargs):
        self.app, self.events = app, events
        self.options = (args, kwargs)

    async def __call__(self, scope, receive, send):
        self.events.append(("trace_start", scope.get("path")))

        async def captured_send(message):
            if message["type"] == "http.response.body":
                self.events.append(("trace_body", message["body"]))
            await send(message)

        await self.app(scope, receive, captured_send)


HttpTraceMiddleware.__module__ = "gsuid_core.http_trace_middleware"


class App:
    def __init__(self, endpoint, events):
        self.user_middleware = [
            Middleware(SurroundingMiddleware, events, "gzip"),
            Middleware(HttpTraceMiddleware, events, "positional", keep="keyword"),
            Middleware(SurroundingMiddleware, events, "auth-and-errors"),
        ]
        self.middleware_stack = None
        self.endpoint = endpoint

    def build(self):
        node = self.endpoint
        for record in reversed(self.user_middleware):
            node = record.cls(node, *record.args, **record.kwargs)
        self.middleware_stack = node

    async def __call__(self, scope, receive, send):
        if self.middleware_stack is None:
            self.build()
        await self.middleware_stack(scope, receive, send)


def app_fixture():
    events = []

    async def endpoint(scope, receive, send):
        events.append(("endpoint_scope", dict(scope)))
        authorized = scope.get("authorized", False)
        await send(
            {
                "type": "http.response.start",
                "status": 200 if authorized else 401,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": PAYLOAD if authorized else b"denied",
            }
        )

    return App(endpoint, events), events


async def request(app, path, *, method="GET", authorized=True, protocol="http"):
    messages = []
    scope = {"type": protocol, "path": path, "method": method, "authorized": authorized}

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    return messages, scope


@pytest.mark.parametrize("built", [False, True])
@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    "path",
    [
        "/api/plugins/Dota2UID",
        "/api/plugins/dota2uid/",
        "/api/plugins/DoTa2UiD///",
        "/api/plugins/Dota2UID/config",
        "/api/plugins/Dota2UID/config/",
        "/api/plugins/Dota2UID/config/Dota2UID/stratz_token",
        "/api/plugins/Dota2UID/config/Dota2UID/asset_proxy/",
    ],
)
@async_test
async def test_cold_and_hot_composition_preserves_full_response_without_trace(
    guard,
    built,
    method,
    path,
):
    app, events = app_fixture()
    if built:
        app.build()
    outer = app.middleware_stack
    records = list(app.user_middleware)
    assert guard.module.protect_config_traces(app) is True
    messages, scope = await request(app, path, method=method)
    assert messages[-1]["body"] == PAYLOAD
    assert messages[0]["status"] == 200
    assert "gzip" in events and "auth-and-errors" in events
    assert ("endpoint_scope", scope) in events
    assert not any(isinstance(item, tuple) and item[0].startswith("trace_") for item in events)
    assert app.user_middleware[0] is records[0]
    assert app.user_middleware[2] is records[2]
    if built:
        assert app.middleware_stack is outer
    assert guard.module.protect_config_traces(app) is False


@pytest.mark.parametrize(
    "path",
    [
        "/api/plugins/AnotherPlugin",
        "/api/plugins/Dota2UIDOther",
        "/api/plugins/Dota2UIDOther/config/Dota2UID/stratz_token",
        "/api/plugins/Dota2UID/configOther",
        "/api/plugins/Dota2UID/reload",
        "/api/plugins/Dota2UID/service",
        "/api/dota2uid/status",
        "/api/other",
    ],
)
@async_test
async def test_other_apis_still_use_original_trace_with_exact_factory_arguments(guard, path):
    app, events = app_fixture()
    guard.module.protect_config_traces(app)
    await request(app, path)
    assert ("trace_start", path) in events
    assert ("trace_body", PAYLOAD) in events
    gate = app.middleware_stack.app
    assert gate.trace.options == (("positional",), {"keep": "keyword"})


@async_test
async def test_native_authentication_remains_required(guard):
    app, events = app_fixture()
    guard.module.protect_config_traces(app)
    messages, _ = await request(app, "/api/plugins/Dota2UID", authorized=False)
    assert messages[0]["status"] == 401
    assert messages[-1]["body"] == b"denied"
    assert "auth-and-errors" in events
    assert CANARY.encode() not in repr(events).encode()


@async_test
async def test_scope_is_not_changed_and_receive_is_not_consumed(guard):
    app, events = app_fixture()
    guard.module.protect_config_traces(app)
    scope = {"type": "http", "path": "/api/plugins/Dota2UID", "authorization": CANARY}
    original = dict(scope)

    async def receive():
        raise AssertionError("middleware must not read request body")

    async def send(message):
        pass

    await app(scope, receive, send)
    assert scope == original
    assert ("endpoint_scope", original) in events


@async_test
async def test_non_http_protocol_is_never_bypassed(guard):
    app, events = app_fixture()
    guard.module.protect_config_traces(app)
    await request(app, "/api/plugins/Dota2UID", protocol="websocket")
    assert ("trace_start", "/api/plugins/Dota2UID") in events


@async_test
async def test_module_reload_reuses_installed_guard_after_stack_build(guard):
    app, events = app_fixture()
    guard.module.protect_config_traces(app)
    await request(app, "/api/plugins/Dota2UID")
    old_stack, old_record = app.middleware_stack, app.user_middleware[1]
    reloaded = guard.load("synthetic_trace_guard_reloaded")
    assert reloaded.protect_config_traces(app) is False
    assert app.middleware_stack is old_stack
    assert app.user_middleware[1] is old_record
    assert old_record.cls is guard.module.ConfigTraceGate
    events.clear()
    await request(app, "/api/plugins/Dota2UID/config/Dota2UID/stratz_token")
    assert not any(isinstance(item, tuple) and item[0].startswith("trace_") for item in events)


@async_test
async def test_duplicate_trace_nodes_are_both_guarded(guard):
    app, events = app_fixture()
    app.user_middleware.insert(2, Middleware(HttpTraceMiddleware, events))
    app.build()
    assert guard.module.protect_config_traces(app)
    await request(app, "/api/plugins/Dota2UID")
    assert not any(isinstance(item, tuple) and item[0].startswith("trace_") for item in events)
    events.clear()
    await request(app, "/api/other")
    assert sum(item == ("trace_start", "/api/other") for item in events) == 2


def test_host_without_trace_is_untouched(guard):
    app, _ = app_fixture()
    app.user_middleware.pop(1)
    app.build()
    original_stack, original_records = app.middleware_stack, list(app.user_middleware)
    assert guard.module.protect_config_traces(app) is False
    assert app.middleware_stack is original_stack
    assert app.user_middleware == original_records


def test_same_named_foreign_middleware_is_not_changed(guard):
    class HttpTraceMiddleware(SurroundingMiddleware):
        pass

    app, events = app_fixture()
    app.user_middleware[1] = Middleware(HttpTraceMiddleware, events, "foreign-trace")
    app.build()
    original_stack, original_record = app.middleware_stack, app.user_middleware[1]
    assert guard.module.protect_config_traces(app) is False
    assert app.middleware_stack is original_stack
    assert app.user_middleware[1] is original_record


def test_cycle_and_invalid_registration_fail_closed_without_partial_change(guard):
    app, _ = app_fixture()
    original_records = list(app.user_middleware)
    node = SimpleNamespace()
    node.app = node
    app.middleware_stack = node
    with pytest.raises(guard.module.ConfigBridgeError, match="^invalid_host_config$"):
        guard.module.protect_config_traces(app)
    assert app.user_middleware == original_records
    assert app.middleware_stack is node
    app.middleware_stack = None
    app.user_middleware[1].args = ["bad-record"]
    with pytest.raises(guard.module.ConfigBridgeError, match="^invalid_host_config$"):
        guard.module.protect_config_traces(app)
    assert app.user_middleware == original_records

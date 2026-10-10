"""Offline bootstrap tests: hostile wheels, immutable publication and owned workers."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType, SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest
import pytest_socket

from scripts import gscore_bundled_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {name: "0.1.0a6" for name in runtime.PACKAGES}


@pytest.fixture(autouse=True)
def owned_offline_loop(monkeypatch):
    # Only asyncio's wakeup sockets are created; application networking stays blocked.
    pytest_socket.enable_socket()
    try:
        loop = asyncio.new_event_loop()
    finally:
        pytest_socket.disable_socket()
    monkeypatch.setattr(asyncio, "run", loop.run_until_complete)
    try:
        yield
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


def wheel_files(name, version="0.1.0a6"):
    dist = f"{name.replace('-', '_')}-{version}.dist-info"
    files = {
        f"{runtime.PACKAGES[name]}/__init__.py": b'"""Synthetic test package."""\n',
        f"{dist}/METADATA": (
            f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\nRequires-Python: >=3.12\n"
        ).encode(),
        f"{dist}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{dist}/RECORD": b"",
        f"{dist}/licenses/LICENSE": b"Synthetic fixture license",
    }
    if name == "dota2forge-core":
        files.update(
            {
                "dota2forge_core/infrastructure/sqlite.py": (
                    b"_APPLICATION_ID = 0x44324647\n_SCHEMA_VERSION = 1\n"
                ),
                "dota2forge_core/infrastructure/subscriptions.py": (
                    b"_APPLICATION_ID = 0x44325355\n_SCHEMA_VERSION = 3\n"
                ),
            }
        )
    return files


def write_wheel(path, files):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as output:
        for name, data in files.items():
            info = ZipInfo(name)
            info.filename = name  # Preserve hostile backslashes on Windows for validation.
            info.compress_type = ZIP_DEFLATED
            output.writestr(info, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "runtime-wheels").mkdir()
    wheels = {}
    for name, version in VERSIONS.items():
        filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        digest = write_wheel(root / "runtime-wheels" / filename, wheel_files(name, version))
        wheels[name] = {"filename": filename, "sha256": digest}
    (root / "release.json").write_text(
        json.dumps({"schema_version": 1, "plugin": "Dota2UID", "versions": VERSIONS}), "utf-8"
    )
    manifest = {
        "schema_version": 1,
        "repository": "https://github.com/HBLADEH/Dota2UID",
        "release_tag": "v0.1.0a6",
        "wheels": wheels,
    }
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")
    deployment(root)
    monkeypatch.setattr(
        runtime, "_probe", lambda generation, versions, stop: runtime._check_stop(stop)
    )
    return root, tmp_path / "data", manifest


def deployment(root):
    digest = hashlib.sha256((root / "runtime-wheels.json").read_bytes()).hexdigest()
    (root / "deployment.json").write_text(
        json.dumps({"schema_version": 1, "mode": "bundled", "manifest_sha256": digest}), "utf-8"
    )


def test_local_preparation_reuses_snapshot_and_preserves_resources(plugin, monkeypatch):
    root, data, _ = plugin
    manager = runtime.BundledRuntime(root, data)
    calls = []
    monkeypatch.setattr(runtime, "_download", lambda *args: calls.append(args))
    first = asyncio.run(manager.prepare())
    assert first is not None and manager.state == "prepared"
    assert (first / "dota2forge_renderer-0.1.0a6.dist-info/licenses/LICENSE").read_bytes()
    pointer = (data / "runtime/current.json").read_bytes()
    assert asyncio.run(manager.prepare(allow_download=True)) == first
    assert (data / "runtime/current.json").read_bytes() == pointer
    assert calls == []
    assert len(list(first.parent.glob("[0-9a-f]" * 32))) == 1
    assert str(data) not in manager.status_text() and str(data) not in str(manager.status())
    assert manager.status()["prepared"] is True
    asyncio.run(manager.close())
    assert manager.status()["state"] == "stopped"
    assert asyncio.run(manager.prepare()) is None


def test_missing_runtime_requires_explicit_download_permission(plugin, monkeypatch):
    root, data, manifest = plugin
    original = {path.name: path.read_bytes() for path in (root / "runtime-wheels").iterdir()}
    shutil.rmtree(root / "runtime-wheels")
    calls = []

    def download(url, destination, stop):
        calls.append(url)
        runtime._check_stop(stop)
        destination.write_bytes(original[destination.name])

    monkeypatch.setattr(runtime, "_download", download)
    manager = runtime.BundledRuntime(root, data)
    assert asyncio.run(manager.prepare()) is None
    assert manager.state == "missing_runtime" and calls == []
    assert not (data / "runtime/current.json").exists()
    assert asyncio.run(manager.prepare(allow_download=True)) is not None
    assert calls == [
        f"{manifest['repository']}/releases/download/{manifest['release_tag']}/{entry['filename']}"
        for entry in manifest["wheels"].values()
    ]


def test_corrupted_local_wheel_can_be_recovered_from_pinned_release(plugin, monkeypatch):
    root, data, _ = plugin
    wheel = next((root / "runtime-wheels").iterdir())
    original = wheel.read_bytes()
    wheel.write_bytes(b"damaged")
    manager = runtime.BundledRuntime(root, data)
    assert asyncio.run(manager.prepare()) is None
    assert manager.error == "invalid_wheel"
    monkeypatch.setattr(
        runtime, "_download", lambda url, destination, stop: destination.write_bytes(original)
    )
    assert asyncio.run(manager.prepare(allow_download=True)) is not None
    assert wheel.read_bytes() == b"damaged"


def test_failed_repair_preserves_pointer_and_existing_generation(plugin, monkeypatch):
    root, data, _ = plugin
    manager = runtime.BundledRuntime(root, data)
    first = asyncio.run(manager.prepare())
    pointer = (data / "runtime/current.json").read_bytes()
    assert first is not None
    original = first / "dota2forge_core/__init__.py"
    original.write_bytes(b"damaged")
    monkeypatch.setattr(
        runtime,
        "_probe",
        lambda *args: (_ for _ in ()).throw(runtime.BootstrapError("runtime_probe_failed")),
    )
    assert asyncio.run(manager.prepare()) is None
    assert manager.error == "runtime_probe_failed"
    assert (data / "runtime/current.json").read_bytes() == pointer
    assert original.read_bytes() == b"damaged"
    assert not list(first.parent.glob(".staging-*"))


def test_repair_uses_new_generation_and_does_not_overwrite_active_files(plugin):
    root, data, _ = plugin
    manager = runtime.BundledRuntime(root, data)
    first = asyncio.run(manager.prepare())
    assert first is not None
    (first / "dota2forge_core/__init__.py").write_bytes(b"damaged")
    second = asyncio.run(manager.prepare())
    assert second is not None and second != first and first.exists()
    assert (first / "dota2forge_core/__init__.py").read_bytes() == b"damaged"
    assert (second / "dota2forge_core/__init__.py").read_bytes() != b"damaged"
    assert json.loads((data / "runtime/current.json").read_bytes())["generation"] == second.name


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "missing_package",
        "repository",
        "credentials",
        "tag",
        "filename",
        "hash",
        "version",
        "deployment",
    ],
)
def test_invalid_manifests_never_start_extraction(plugin, change):
    root, data, manifest = plugin
    release = json.loads((root / "release.json").read_text("utf-8"))
    if change == "schema":
        manifest["schema_version"] = True
    elif change == "missing_package":
        del manifest["wheels"]["dota2uid"]
    elif change == "repository":
        manifest["repository"] = "https://evil.invalid/Dota2UID"
    elif change == "credentials":
        manifest["repository"] = "https://user:secret@github.com/HBLADEH/Dota2UID"
    elif change == "tag":
        manifest["release_tag"] = "v99"
    elif change == "filename":
        manifest["wheels"]["dota2uid"]["filename"] = "../outside.whl"
    elif change == "hash":
        manifest["wheels"]["dota2uid"]["sha256"] = "invalid"
    elif change == "version":
        release["versions"]["dota2uid"] = "../outside"
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")
    (root / "release.json").write_text(json.dumps(release), "utf-8")
    if change != "deployment":
        deployment(root)
    else:
        (root / "deployment.json").write_text(
            json.dumps({"schema_version": 1, "mode": "bundled", "manifest_sha256": "0" * 64}),
            "utf-8",
        )
    manager = runtime.BundledRuntime(root, data)
    assert asyncio.run(manager.prepare(allow_download=True)) is None
    assert manager.error == "invalid_manifest"
    assert not data.exists()


@pytest.mark.parametrize(
    "bad_path",
    [
        "../escaped.py",
        "/escaped.py",
        "Dota2UID\\escape.py",
        "Dota2UID/../escape.py",
        "Dota2UID//escape.py",
        "Dota2UID/CON.txt",
        "Dota2UID/file.py.",
        "gsuid_core/__init__.py",
        "PIL/__init__.py",
        "Dota2UID/image.PNG",
        "Dota2UID/config.toml",
        "Dota2UID/cache.sqlite3",
        "Dota2UID/native.pyd",
    ],
)
def test_wheel_paths_native_sdk_art_and_config_are_rejected(tmp_path, bad_path):
    files = wheel_files("dota2uid")
    files[bad_path] = b"hostile"
    wheel = tmp_path / "dota2uid-0.1.0a6-py3-none-any.whl"
    digest = write_wheel(wheel, files)
    with pytest.raises(runtime.BootstrapError, match="校验失败"):
        runtime.validate_wheel(wheel, "dota2uid", "0.1.0a6", digest)
    assert not (tmp_path / "escaped.py").exists()


@pytest.mark.parametrize(
    "field,value", [("Name", "foreign"), ("Version", "0.0.1"), ("Requires-Python", ">=3.11")]
)
def test_wheel_metadata_must_match_exact_release(tmp_path, field, value):
    files = wheel_files("dota2uid")
    key = "dota2uid-0.1.0a6.dist-info/METADATA"
    text = files[key].decode()
    old = {"Name": "dota2uid", "Version": "0.1.0a6", "Requires-Python": ">=3.12"}[field]
    files[key] = text.replace(f"{field}: {old}", f"{field}: {value}").encode()
    path = tmp_path / "dota2uid-0.1.0a6-py3-none-any.whl"
    digest = write_wheel(path, files)
    with pytest.raises(runtime.BootstrapError):
        runtime.validate_wheel(path, "dota2uid", "0.1.0a6", digest)


@pytest.mark.parametrize(
    "case", ["duplicate", "case", "symlink", "collision", "limit", "tag", "license", "bad_hash"]
)
def test_wheel_structure_collisions_tags_hashes_and_limits(tmp_path, monkeypatch, case):
    files = wheel_files("dota2uid")
    if case == "case":
        files["Dota2UID/__INIT__.py"] = b"case collision"
    elif case == "collision":
        files["Dota2UID/sub"] = b"file"
        files["Dota2UID/sub/child.py"] = b"collision"
    elif case == "limit":
        monkeypatch.setattr(runtime, "MAX_EXPANDED_BYTES", 10)
    elif case == "tag":
        files["dota2uid-0.1.0a6.dist-info/WHEEL"] = files[
            "dota2uid-0.1.0a6.dist-info/WHEEL"
        ].replace(b"py3-none-any", b"cp313-cp313-win_amd64")
    elif case == "license":
        del files["dota2uid-0.1.0a6.dist-info/licenses/LICENSE"]
    path = tmp_path / "dota2uid-0.1.0a6-py3-none-any.whl"
    digest = write_wheel(path, files)
    if case in {"duplicate", "symlink"}:
        with ZipFile(path, "a") as output:
            info = ZipInfo("Dota2UID/__init__.py" if case == "duplicate" else "Dota2UID/link")
            info.create_system = 3
            info.external_attr = (0o120777 if case == "symlink" else 0o100644) << 16
            with pytest.warns(UserWarning) if case == "duplicate" else nullcontext():
                output.writestr(info, b"target")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if case == "bad_hash":
        digest = "0" * 64
    with pytest.raises(runtime.BootstrapError):
        runtime.validate_wheel(path, "dota2uid", "0.1.0a6", digest)


def test_host_dependency_conflict_remains_distinct_from_missing_runtime(plugin, monkeypatch):
    root, data, _ = plugin
    original = runtime.metadata.distribution
    monkeypatch.setattr(
        runtime.metadata,
        "distribution",
        lambda name: (
            SimpleNamespace(version="0.1", metadata={}, requires=[])
            if name == "httpx"
            else original(name)
        ),
    )
    manager = runtime.BundledRuntime(root, data)
    assert asyncio.run(manager.prepare()) is None
    assert manager.state == "dependency_incompatible"
    assert "宿主" in manager.status_text() and not (data / "runtime/current.json").exists()


def test_transitive_requirement_and_host_constraints_are_checked(monkeypatch):
    installed_site = runtime.metadata.distribution("httpx").locate_file("")
    installed_pillow = runtime.metadata.version("Pillow")

    class Distribution:
        def __init__(self, name, version, requires):
            self.version = version
            self.requires = requires
            self.metadata = {"Name": name, "Requires-Python": ">=3.12"}

        def locate_file(self, name):
            return installed_site / name

    host = {
        "httpx": Distribution("httpx", "0.28.1", ["httpcore==1.*", "optional; extra == 'brotli'"]),
        "httpcore": Distribution("httpcore", "1.0.9", ["h11>=0.16"]),
        "h11": Distribution("h11", "0.16.0", []),
        "pillow": Distribution("pillow", installed_pillow, []),
    }
    monkeypatch.setattr(runtime.metadata, "distribution", lambda name: host[name])
    monkeypatch.setattr(runtime.metadata, "version", lambda name: host[name].version)
    monkeypatch.setattr(runtime.metadata, "distributions", lambda: host.values())
    runtime._dependencies({}, [])
    host["h11"].version = "0.15.0"
    with pytest.raises(runtime.BootstrapError) as error:
        runtime._dependencies({}, [])
    assert error.value.code == "dependency_incompatible"
    host["h11"].version = "0.16.0"
    host["consumer"] = Distribution("consumer", "1", ["Pillow<11"])
    with pytest.raises(runtime.BootstrapError):
        runtime._dependencies({}, [])


@pytest.mark.parametrize(
    "version,spec,expected",
    [
        ("0.28.1", ">=0.28.1,<1", True),
        ("11.3.0", ">=11.3,<13", True),
        ("13.0.0", "<13", False),
        ("1.0.9", "==1.*", True),
        ("1.0.9", "!=1.*", False),
        ("1.4.6", "~=1.4.5", True),
        ("1.5.0", "~=1.4.5", False),
        ("0.1.0a6", ">=0.1.0a4,<0.2", True),
        ("1.1", "===1.1", True),
    ],
)
def test_supported_pep440_ranges(version, spec, expected):
    assert runtime._satisfies(version, spec) is expected


def test_markers_do_not_execute_code_and_respect_extras():
    assert runtime._marker("python_version >= '3.12' and extra == 'stratz'", "stratz")
    assert not runtime._marker("extra == 'brotli'")
    assert runtime._marker("sys_platform in 'win32 linux darwin'")
    with pytest.raises(runtime.BootstrapError):
        runtime._marker("__import__('os').system('bad')")
    with pytest.raises(runtime.BootstrapError):
        runtime._requirement("pillow @ https://evil.invalid/a.whl")


def test_busy_command_is_idempotent_and_close_waits_for_owned_thread(plugin, monkeypatch):
    root, data, _ = plugin
    entered, exited = threading.Event(), threading.Event()

    def blocked_probe(generation, versions, stop):
        entered.set()
        stop.wait(5)
        exited.set()
        runtime._check_stop(stop)

    monkeypatch.setattr(runtime, "_probe", blocked_probe)
    manager = runtime.BundledRuntime(root, data)

    async def check():
        work = asyncio.create_task(manager.prepare())
        assert await asyncio.to_thread(entered.wait, 3)
        assert manager.status()["busy"] is True
        assert await manager.prepare(allow_download=True) is None
        await manager.close()
        assert exited.is_set() and work.done()
        assert await work is None

    asyncio.run(check())
    assert manager.state == "stopped" and not (data / "runtime/current.json").exists()
    assert not list((data / "runtime").glob("*/.staging-*"))


def test_cancellation_waits_for_worker_and_does_not_publish(plugin, monkeypatch):
    root, data, _ = plugin
    entered, exited = threading.Event(), threading.Event()

    def blocked_probe(generation, versions, stop):
        entered.set()
        stop.wait(5)
        exited.set()
        runtime._check_stop(stop)

    monkeypatch.setattr(runtime, "_probe", blocked_probe)
    manager = runtime.BundledRuntime(root, data)

    async def check():
        work = asyncio.create_task(manager.prepare())
        assert await asyncio.to_thread(entered.wait, 3)
        work.cancel()
        with pytest.raises(asyncio.CancelledError):
            await work
        assert exited.is_set() and manager._task.done()

    asyncio.run(check())
    assert manager.error == "cancelled" and not (data / "runtime/current.json").exists()


def test_two_runtime_instances_share_one_os_lease_and_snapshot(plugin):
    root, data, _ = plugin
    first, second = runtime.BundledRuntime(root, data), runtime.BundledRuntime(root, data)

    async def check():
        one, two = await asyncio.gather(first.prepare(), second.prepare())
        assert one is not None and one == two

    asyncio.run(check())
    assert len(list((data / "runtime").glob("*/*/.complete.json"))) == 1


def test_activation_refuses_unknown_or_old_project_modules_without_deleting_them(
    plugin, monkeypatch
):
    root, data, _ = plugin
    manager = runtime.BundledRuntime(root, data)
    assert asyncio.run(manager.prepare()) is not None
    module = ModuleType("dota2forge_core")
    module.__file__ = str(data / "old/core.py")
    monkeypatch.setitem(sys.modules, "dota2forge_core", module)
    previous = list(sys.path)
    with pytest.raises(runtime.BootstrapError) as error:
        manager.activate()
    assert error.value.code == "module_conflict"
    assert sys.modules["dota2forge_core"] is module and sys.path == previous


def test_activation_prepend_is_idempotent_and_requires_prepared_complete_snapshot(
    plugin, monkeypatch
):
    root, data, _ = plugin
    manager = runtime.BundledRuntime(root, data)
    with pytest.raises(runtime.BootstrapError):
        manager.activate()
    generation = asyncio.run(manager.prepare())
    assert generation is not None
    for name in list(sys.modules):
        if any(
            name == package or name.startswith(package + ".")
            for package in runtime.PACKAGES.values()
        ):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "path_hooks", list(sys.path_hooks))
    monkeypatch.setattr(sys, "path_importer_cache", dict(sys.path_importer_cache))
    manager.activate()
    manager.activate()
    assert manager.state == "runtime_available" and sys.path[0] == str(generation)
    assert sys.path.count(str(generation)) == 1
    asyncio.run(manager.close())
    with pytest.raises(runtime.BootstrapError) as error:
        manager.activate()
    assert error.value.code == "stopped"


def real_snapshot(root):
    source_roots = {
        "dota2forge-core": "packages/dota2forge-core/src",
        "dota2forge-renderer": "packages/dota2forge-renderer/src",
        "dota2forge-assets": "packages/dota2forge-assets/src",
        "dota2uid": "adapters/Dota2UID/src",
    }
    for name, module in runtime.PACKAGES.items():
        shutil.copytree(
            ROOT / source_roots[name] / module,
            root / module,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for filename, data in wheel_files(name).items():
            if ".dist-info/" in filename:
                target = root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)


def test_real_isolated_probe_imports_four_components_and_renders_font_resources(tmp_path):
    generation = tmp_path / "generation"
    generation.mkdir()
    real_snapshot(generation)
    runtime._probe(generation, VERSIONS, threading.Event())
    font = generation / "dota2forge_renderer/assets/v1/NotoSansCJKsc-Regular.otf"
    font.write_bytes(b"damaged font")
    with pytest.raises(runtime.BootstrapError) as error:
        runtime._probe(generation, VERSIONS, threading.Event())
    assert error.value.code == "runtime_probe_failed"
    assert not list(generation.rglob("*.pyc"))


def test_probe_blocks_socket_access_without_reading_configuration(tmp_path):
    generation = tmp_path / "generation"
    generation.mkdir()
    real_snapshot(generation)
    (generation / "dota2forge_core/__init__.py").write_text(
        "import socket\nsocket.socket()\n", "utf-8"
    )
    with pytest.raises(runtime.BootstrapError) as error:
        runtime._probe(generation, VERSIONS, threading.Event())
    assert error.value.code == "runtime_probe_failed"


def test_probe_timeout_and_cancel_reap_child_process(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "PROBE", "import time; time.sleep(60)")
    monkeypatch.setattr(runtime, "PROBE_TIMEOUT", 0.05)
    with pytest.raises(runtime.BootstrapError) as error:
        runtime._probe(tmp_path, VERSIONS, threading.Event())
    assert error.value.code == "runtime_probe_failed"
    stopped = threading.Event()
    stopped.set()
    with pytest.raises(runtime.BootstrapError) as error:
        runtime._probe(tmp_path, VERSIONS, stopped)
    assert error.value.code == "cancelled"


def test_redirect_rejects_untrusted_hosts_credentials_and_downgrade():
    from http.client import HTTPMessage
    from io import BytesIO
    from urllib.request import Request

    handler = runtime._SecureRedirect()
    request = Request("https://github.com/HBLADEH/Dota2UID/releases/download/v1/a.whl")
    for url in (
        "http://github.com/a",
        "https://evil.invalid/a",
        "https://user:secret@github.com/a",
        "https://github.com:444/a",
    ):
        with pytest.raises(runtime.BootstrapError):
            handler.redirect_request(request, BytesIO(), 302, "redirect", HTTPMessage(), url)


def test_child_process_lock_cannot_take_parent_lease_and_releases_on_exit(tmp_path):
    lock = tmp_path / "runtime.lock"
    command = [
        sys.executable,
        "-I",
        "-c",
        "import importlib.util, pathlib, sys, threading\n"
        "spec=importlib.util.spec_from_file_location('bootstrap',sys.argv[1])\n"
        "m=importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "stop=threading.Event()\n"
        "threading.Timer(.15,stop.set).start()\n"
        "lease=m._process_lock(pathlib.Path(sys.argv[2]),stop)\n"
        "lease.__enter__()\n",
        str(ROOT / "scripts/gscore_bundled_runtime.py"),
        str(lock),
    ]
    with runtime._process_lock(lock, threading.Event()):
        result = subprocess.run(command, capture_output=True, timeout=5)
        assert result.returncode != 0 and b"BootstrapError" in result.stderr
    with runtime._process_lock(lock, threading.Event()):
        pass


@pytest.mark.skipif(os.name != "nt", reason="Windows junction test")
def test_private_runtime_rejects_junction_data_root(plugin):
    root, data, _ = plugin
    target = data.parent / "target"
    target.mkdir()
    os.symlink(target, data, target_is_directory=True)
    try:
        manager = runtime.BundledRuntime(root, data)
        assert asyncio.run(manager.prepare()) is None
        assert manager.error == "permission_denied"
        assert not (target / "runtime").exists()
    finally:
        data.unlink()


def test_validated_wheel_is_parsed_from_authenticated_bytes_not_reopened_path(
    tmp_path, monkeypatch
):
    path = tmp_path / "dota2uid-0.1.0a6-py3-none-any.whl"
    original = wheel_files("dota2uid")
    digest = write_wheel(path, original)
    read_bytes = Path.read_bytes
    replaced = False

    def replace_after_read(current):
        nonlocal replaced
        content = read_bytes(current)
        if current == path and not replaced:
            replaced = True
            path.write_bytes(b"substituted after the digest read")
        return content

    monkeypatch.setattr(Path, "read_bytes", replace_after_read)
    assert runtime.validate_wheel(path, "dota2uid", "0.1.0a6", digest) == original
    assert replaced and path.read_bytes() == b"substituted after the digest read"


def test_interrupted_process_staging_is_cleaned_under_new_lease_without_touching_pointer(plugin):
    root, data, _ = plugin
    manager = runtime.BundledRuntime(root, data)
    generation = asyncio.run(manager.prepare())
    assert generation is not None
    pointer = (data / "runtime/current.json").read_bytes()
    abandoned = generation.parent / (".staging-" + "a" * 32)
    child = """import importlib.util, os, pathlib, sys, threading
spec = importlib.util.spec_from_file_location('bootstrap', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
lock = module._process_lock(pathlib.Path(sys.argv[2]), threading.Event())
lock.__enter__()
stage = pathlib.Path(sys.argv[3])
stage.mkdir()
(stage / 'partial.py').write_bytes(b'incomplete')
os._exit(7)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            child,
            str(ROOT / "scripts/gscore_bundled_runtime.py"),
            str(data / "runtime/.prepare.lock"),
            str(abandoned),
        ],
        timeout=5,
    )
    assert result.returncode == 7 and abandoned.exists()
    assert asyncio.run(manager.prepare()) == generation
    assert not abandoned.exists() and (data / "runtime/current.json").read_bytes() == pointer


def test_repeated_close_cancellation_still_waits_for_thread_and_marks_stopped(plugin, monkeypatch):
    root, data, _ = plugin
    entered, stopping, release, exited = (threading.Event() for _ in range(4))

    def slow_stopping(generation, versions, stop):
        entered.set()
        stop.wait(5)
        stopping.set()
        release.wait(5)
        exited.set()
        runtime._check_stop(stop)

    monkeypatch.setattr(runtime, "_probe", slow_stopping)
    manager = runtime.BundledRuntime(root, data)

    async def check():
        work = asyncio.create_task(manager.prepare())
        assert await asyncio.to_thread(entered.wait, 3)
        closed = asyncio.create_task(manager.close())
        assert await asyncio.to_thread(stopping.wait, 3)
        closed.cancel()
        await asyncio.sleep(0.01)
        assert not closed.done() and not exited.is_set()
        closed.cancel()
        await asyncio.sleep(0.01)
        assert not closed.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await closed
        assert exited.is_set() and manager._task.done()
        assert await work is None

    asyncio.run(check())
    assert manager.state == "stopped" and not (data / "runtime/current.json").exists()


@pytest.mark.parametrize("case", ["ok", "limit", "cancel", "timeout", "url_error", "deadline"])
def test_standard_library_downloader_is_bounded_cancellable_and_injectable(
    tmp_path, monkeypatch, case
):
    from urllib.error import URLError

    destination = tmp_path / "runtime.whl"
    stop = threading.Event()
    calls = []

    class Response(io.BytesIO):
        def read(self, count):
            if case == "timeout":
                raise TimeoutError
            return super().read(count)

    class Opener:
        def open(self, url, *, timeout):
            calls.append((url, timeout))
            if case == "url_error":
                raise URLError("synthetic unreachable release")
            return Response(b"authenticated bytes")

    monkeypatch.setattr(runtime, "build_opener", lambda redirect: Opener())
    if case == "cancel":
        stop.set()
    elif case == "limit":
        monkeypatch.setattr(runtime, "MAX_WHEEL_BYTES", 2)
    elif case == "deadline":
        monkeypatch.setattr(runtime, "DOWNLOAD_DEADLINE", -1)
    url = "https://github.com/HBLADEH/Dota2UID/releases/download/v0.1.0a6/runtime.whl"
    if case == "ok":
        runtime._download(url, destination, stop)
        assert destination.read_bytes() == b"authenticated bytes"
    else:
        expected = {
            "limit": "invalid_wheel",
            "cancel": "cancelled",
            "timeout": "download_timeout",
            "url_error": "download_failed",
            "deadline": "download_timeout",
        }[case]
        with pytest.raises(runtime.BootstrapError) as error:
            runtime._download(url, destination, stop)
        assert error.value.code == expected
    assert calls == [(url, runtime.DOWNLOAD_TIMEOUT)]


def test_loaded_third_party_version_and_source_must_agree_with_host_metadata(monkeypatch):
    loaded = ModuleType("httpx")
    loaded.__file__ = str(ROOT / "unmanaged/httpx/__init__.py")
    loaded.__version__ = runtime.metadata.version("httpx")
    monkeypatch.setitem(sys.modules, "httpx", loaded)
    with pytest.raises(runtime.BootstrapError) as error:
        runtime._dependencies({}, [])
    assert error.value.code == "dependency_incompatible"
    loaded.__file__ = str(runtime.metadata.distribution("httpx").locate_file("httpx/__init__.py"))
    loaded.__version__ = "0.1"
    with pytest.raises(runtime.BootstrapError):
        runtime._dependencies({}, [])


@pytest.mark.parametrize("loaded_version, compatible", [("2026.01.04", True), ("2026.1.5", False)])
def test_loaded_certifi_calendar_version_is_compared_with_pep440_normalization(
    monkeypatch, loaded_version, compatible
):
    distribution = runtime.metadata.distribution
    original = distribution("certifi")
    certificate = SimpleNamespace(
        version="2026.1.4",
        metadata=original.metadata,
        requires=original.requires,
        locate_file=original.locate_file,
    )
    monkeypatch.setattr(
        runtime.metadata,
        "distribution",
        lambda name: certificate if name == "certifi" else distribution(name),
    )
    loaded = ModuleType("certifi")
    loaded.__file__ = str(original.locate_file("certifi/__init__.py"))
    loaded.__version__ = loaded_version
    monkeypatch.setitem(sys.modules, "certifi", loaded)
    if compatible:
        runtime._dependencies({}, ["certifi"])
    else:
        with pytest.raises(runtime.BootstrapError) as error:
            runtime._dependencies({}, ["certifi"])
        assert error.value.code == "dependency_incompatible"


@pytest.mark.parametrize(
    "failure,expected", [(PermissionError, "permission_denied"), (OSError, "disk_error")]
)
def test_storage_errors_are_distinct_and_never_publish(plugin, monkeypatch, failure, expected):
    root, data, _ = plugin

    def publish(*args):
        raise failure("synthetic storage failure")

    monkeypatch.setattr(runtime, "_atomic_json", publish)
    manager = runtime.BundledRuntime(root, data)
    assert asyncio.run(manager.prepare()) is None
    assert manager.error == expected and not (data / "runtime/current.json").exists()


@pytest.mark.parametrize("case", ["unknown_compression", "corrupt_deflate"])
def test_malformed_compression_is_reported_as_invalid_wheel(tmp_path, case):
    path = tmp_path / "dota2uid-0.1.0a6-py3-none-any.whl"
    write_wheel(path, wheel_files("dota2uid"))
    payload = bytearray(path.read_bytes())
    if case == "unknown_compression":
        struct.pack_into("<H", payload, 8, 999)
        central = payload.index(b"PK\x01\x02")
        struct.pack_into("<H", payload, central + 10, 999)
    else:
        filename_length, extra_length = struct.unpack_from("<HH", payload, 26)
        body = 30 + filename_length + extra_length
        payload[body : body + 2] = b"\x07\xff"  # Reserved deflate block type.
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    with pytest.raises(runtime.BootstrapError) as error:
        runtime.validate_wheel(path, "dota2uid", "0.1.0a6", digest)
    assert error.value.code == "invalid_wheel"


def test_private_source_loader_ignores_unverified_bytecode_and_never_writes_caches(tmp_path):
    import importlib.machinery
    import py_compile

    source = tmp_path / "isolated_module.py"
    source.write_text("value = 17\n", "utf-8")
    malicious = tmp_path / "malicious.py"
    malicious.write_text("value = 99\n", "utf-8")
    os.utime(source, (1_000_000, 1_000_000))
    os.utime(malicious, (1_000_000, 1_000_000))
    cache = Path(importlib.util.cache_from_source(str(source)))
    py_compile.compile(str(malicious), cfile=str(cache), dfile=str(source), doraise=True)
    cached = {}
    exec(
        importlib.machinery.SourceFileLoader("isolated_module", str(source)).get_code(
            "isolated_module"
        ),
        cached,
    )
    assert cached["value"] == 99
    loader = runtime._ImmutableSourceLoader("isolated_module", str(source))
    validated = {}
    exec(loader.get_code("isolated_module"), validated)
    assert validated["value"] == 17
    cache.unlink()
    loader.get_code("isolated_module")
    loader.set_data(str(cache), b"unverified")
    assert not cache.exists()


def test_private_path_hook_clears_only_its_cache_and_preserves_host_loader(tmp_path, monkeypatch):
    generation = tmp_path / "private"
    generation.mkdir()
    child = generation / "package"
    child.mkdir()
    outside = tmp_path / "host"
    outside.mkdir()
    outside_finder = object()
    monkeypatch.setattr(sys, "path_hooks", list(sys.path_hooks))
    monkeypatch.setattr(
        sys,
        "path_importer_cache",
        {
            str(generation): object(),
            str(child): object(),
            str(outside): outside_finder,
        },
    )
    previous_hooks = len(sys.path_hooks)
    runtime._install_source_hook(generation)
    runtime._install_source_hook(generation)
    assert len(sys.path_hooks) == previous_hooks + 1
    assert sys.path_importer_cache == {str(outside): outside_finder}
    assert isinstance(sys.path_hooks[0](str(child)), runtime.machinery.FileFinder)
    with pytest.raises(ImportError):
        sys.path_hooks[0](str(outside))


def test_non_bytecode_disabled_parent_imports_and_stop_reload_reuse_one_generation(plugin):
    root, data, manifest = plugin
    temporary_sources = data.parent / "actual_source"
    temporary_sources.mkdir()
    real_snapshot(temporary_sources)
    for name, module in runtime.PACKAGES.items():
        files = {
            path.relative_to(temporary_sources).as_posix(): path.read_bytes()
            for path in (temporary_sources / module).rglob("*")
            if path.is_file()
        }
        files.update(
            {
                filename: payload
                for filename, payload in wheel_files(name).items()
                if ".dist-info/" in filename
            }
        )
        entry = manifest["wheels"][name]
        entry["sha256"] = write_wheel(root / "runtime-wheels" / entry["filename"], files)
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")
    deployment(root)
    host_source = data.parent / "host_source"
    host_source.mkdir()
    (host_source / "host_cache_probe.py").write_text("value = 1\n", "utf-8")
    child = """import asyncio, importlib.util, pathlib, sys, threading
spec = importlib.util.spec_from_file_location('bootstrap', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root, data = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
manager = module.BundledRuntime(root, data)
generation = asyncio.run(manager.prepare())
assert generation is not None, manager.error
assert sys.dont_write_bytecode is False
manager.activate()
import dota2forge_core, dota2forge_assets, dota2forge_renderer, Dota2UID.runtime
from importlib.resources import files
assert files('dota2forge_renderer').joinpath('assets','v1','OFL.txt').read_bytes()
assert not list(generation.rglob('__pycache__'))
assert module._complete(generation, manager._digest, threading.Event())
assert sys.dont_write_bytecode is False
sys.path.insert(0, sys.argv[4])
import host_cache_probe
assert list(pathlib.Path(sys.argv[4]).rglob('*.pyc'))
asyncio.run(manager.close())
replacement = module.BundledRuntime(root, data)
assert asyncio.run(replacement.prepare()) == generation, replacement.error
replacement.activate()
assert replacement.state == 'runtime_available'
assert module._complete(generation, replacement._digest, threading.Event())
assert not list(generation.rglob('__pycache__'))
hooks = [h for h in sys.path_hooks
         if getattr(h,'_dota2forge_generation',None)==str(generation)]
assert len(hooks) == 1
asyncio.run(replacement.close())
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            child,
            str(ROOT / "scripts/gscore_bundled_runtime.py"),
            str(root),
            str(data),
            str(host_source),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert len(list((data / "runtime").glob("*/*/.complete.json"))) == 1


def test_frozen_bridge_manifest_and_prepared_pointer_do_not_change_active_version(plugin):
    root, data, manifest = plugin
    source = b'"""Synthetic frozen bridge."""\n'
    (root / "_dota2forge_business.py").write_bytes(source)
    config = json.loads((root / "deployment.json").read_bytes())
    config["hot_reload"] = {
        "protocol": 1,
        "contract": runtime.HOT_RELOAD_CONTRACT,
        "business_sha256": hashlib.sha256(source).hexdigest(),
    }
    (root / "deployment.json").write_text(json.dumps(config), "utf-8")
    initial = runtime.BundledRuntime(root, data)
    initial.freeze()
    assert initial.versions == VERSIONS and initial.bridge == source
    assert asyncio.run(initial.prepare()) is not None
    initial.record_active()
    active = (data / "runtime/active.json").read_bytes()
    # A later Git update changes the manifest; the first owner retains its copy.
    manifest["repository"] = "https://github.com/another/Dota2UID"
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")
    deployment(root)
    assert asyncio.run(initial.prepare()) == initial.generation
    assert initial.bridge == source
    later = runtime.BundledRuntime(root, data)
    assert asyncio.run(later.prepare()) is not None
    assert later.digest != initial.digest
    assert (data / "runtime/active.json").read_bytes() == active
    later.record_active()
    assert (data / "runtime/active.json").read_bytes() != active


@pytest.mark.parametrize("case", ["protocol", "bridge", "contract", "missing"])
def test_freeze_rejects_invalid_handoff_manifest(plugin, case):
    root, data, _ = plugin
    source = b"value = 1\n"
    (root / "_dota2forge_business.py").write_bytes(source)
    config = json.loads((root / "deployment.json").read_bytes())
    hot = {
        "protocol": 1,
        "contract": runtime.HOT_RELOAD_CONTRACT,
        "business_sha256": hashlib.sha256(source).hexdigest(),
    }
    if case == "protocol":
        hot["protocol"] = True
    elif case == "bridge":
        hot["business_sha256"] = "0" * 64
    elif case == "contract":
        hot["contract"] = None
    else:
        (root / "_dota2forge_business.py").unlink()
    config["hot_reload"] = hot
    (root / "deployment.json").write_text(json.dumps(config), "utf-8")
    with pytest.raises((runtime.BootstrapError, OSError)):
        runtime.BundledRuntime(root, data).freeze()


def test_storage_fingerprint_checks_schema_and_detects_failed_start_writes(tmp_path):
    import sqlite3
    from contextlib import closing

    assert set(runtime.storage_fingerprint(tmp_path).values()) == {"missing"}
    for name, app, version in (
        ("bindings.sqlite3", 0x44324647, 1),
        ("subscriptions.sqlite3", 0x44325355, 3),
    ):
        with closing(sqlite3.connect(tmp_path / name)) as connection:
            connection.execute(f"PRAGMA application_id = {app}")
            connection.execute(f"PRAGMA user_version = {version}")
            connection.execute("CREATE TABLE synthetic(value INTEGER)")
    before = runtime.storage_fingerprint(tmp_path)
    with closing(sqlite3.connect(tmp_path / "bindings.sqlite3")) as connection:
        connection.execute("INSERT INTO synthetic VALUES (42)")
        connection.commit()
    assert runtime.storage_fingerprint(tmp_path) != before
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection:
        connection.execute("PRAGMA user_version = 99")
    with pytest.raises(runtime.BootstrapError) as error:
        runtime.storage_fingerprint(tmp_path)
    assert error.value.code == "reload_incompatible"


@pytest.fixture
def module_switch(tmp_path, monkeypatch):
    old = runtime.BundledRuntime(tmp_path / "old-plugin", tmp_path / "data")
    new = runtime.BundledRuntime(tmp_path / "new-plugin", tmp_path / "data")
    old.generation, new.generation = tmp_path / "old", tmp_path / "new"
    old.contract = new.contract = runtime.HOT_RELOAD_CONTRACT
    old.generation.mkdir()
    new.generation.mkdir()
    module = ModuleType("dota2forge_core")
    module.__file__ = str(old.generation / "dota2forge_core/__init__.py")
    # Only the module-table bookkeeping is exercised here; real imports are
    # covered separately in an isolated interpreter so test collection is intact.
    monkeypatch.setattr(
        runtime,
        "sys",
        SimpleNamespace(
            modules={"dota2forge_core": module},
            path=[str(old.generation), "synthetic-host"],
            path_hooks=list(sys.path_hooks),
            path_importer_cache={"synthetic-host": object()},
        ),
    )
    runtime.claim_runtime(old, "synthetic-owner")
    return old, new, module


def test_switch_detaches_all_late_imports_and_restores_only_project_state(module_switch):
    old, new, module = module_switch
    switch = runtime.RuntimeSwitch(old, new, "synthetic-owner", "plugins.Dota2UID")
    late = ModuleType("dota2forge_core.late")
    late.__file__ = str(old.generation / "dota2forge_core/late.py")
    runtime.sys.modules[late.__name__] = late
    host_finder = runtime.sys.path_importer_cache["synthetic-host"]
    switch.detach()
    assert "dota2forge_core" not in runtime.sys.modules and late.__name__ not in runtime.sys.modules
    candidate = ModuleType("dota2forge_core")
    candidate.__file__ = str(new.generation / "dota2forge_core/__init__.py")
    runtime.sys.modules[candidate.__name__] = candidate
    unrelated = ModuleType("another_plugin")
    runtime.sys.modules[unrelated.__name__] = unrelated
    runtime.sys.path.insert(0, str(new.generation))
    runtime.sys.path.append("later-host")
    switch.restore()
    assert runtime.sys.modules["dota2forge_core"] is module
    assert runtime.sys.modules[late.__name__] is late
    assert runtime.sys.modules[unrelated.__name__] is unrelated
    assert "later-host" in runtime.sys.path and str(new.generation) not in runtime.sys.path
    assert runtime.sys.path_importer_cache["synthetic-host"] is host_finder


@pytest.mark.parametrize("case", ["source", "lease", "contract", "consumer", "replaced"])
def test_switch_rejects_unknown_sources_shared_consumers_and_changed_modules(module_switch, case):
    old, new, module = module_switch
    expected = "reload_incompatible"
    if case == "source":
        module.__file__ = str(new.generation / "unexpected.py")
        expected = "module_conflict"
    elif case == "lease":
        runtime._leases()["another-owner"] = str(old.generation)
    elif case == "contract":
        new.contract = "incompatible-storage"
    elif case == "consumer":
        consumer = ModuleType("another_plugin")
        consumer.Core = module
        runtime.sys.modules[consumer.__name__] = consumer
        expected = "runtime_shared"
    else:
        switch = runtime.RuntimeSwitch(old, new, "synthetic-owner", "plugins.Dota2UID")
        runtime.sys.modules["dota2forge_core"] = ModuleType("dota2forge_core")
        with pytest.raises(runtime.BootstrapError) as error:
            switch.detach()
        assert error.value.code == "module_conflict"
        assert not switch.detached
        return
    with pytest.raises(runtime.BootstrapError) as error:
        runtime.RuntimeSwitch(old, new, "synthetic-owner", "plugins.Dota2UID")
    assert error.value.code == expected
    assert runtime.sys.modules["dota2forge_core"] is module

"""Check generated dependency lists in fresh environments using only staged local wheels."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gscore_public_runtime import public_requirements

SMOKE = r"""
import asyncio
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
import httpx
import io
from PIL import Image

entry = Path(sys.argv[1])
if (entry.parent / 'deployment.json').is_file():
    for package in ('Dota2UID', 'dota2forge_core', 'dota2forge_renderer', 'dota2forge_assets'):
        assert importlib.util.find_spec(package) is None
    bundled_spec = importlib.util.spec_from_file_location(
        'bundled_runtime', entry.parent / '_dota2forge_runtime.py'
    )
    bundled = importlib.util.module_from_spec(bundled_spec)
    sys.modules[bundled_spec.name] = bundled
    bundled_spec.loader.exec_module(bundled)
    manager = bundled.BundledRuntime(entry.parent, Path.cwd() / 'bundled-data')
    assert asyncio.run(manager.prepare()) is not None, manager.status()
    manager.activate()
    assert manager.state == 'runtime_available'
    assert importlib.metadata.version('dota2uid')
from dota2forge_assets import AssetManager

if not (entry.parent / 'deployment.json').is_file():
    spec = importlib.util.spec_from_file_location(
        "release_guard", entry.parent / "_dota2forge_bootstrap.py"
    )
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.verify_dependencies(str(entry))
assert importlib.util.find_spec("astrbot") is None
assert importlib.util.find_spec("gsuid_core") is None
clients = []
asset_clients = []
asset_requests = []

def asset_factory(root, activate):
    def artwork(request):
        asset_requests.append(request)
        assert 'authorization' not in request.headers
        if 'datafeed' in str(request.url):
            hero = 'herolist' in str(request.url)
            key = 'heroes' if hero else 'itemabilities'
            return httpx.Response(200, json={'result': {'data': {key: [
                {'id': 2 if hero else 1,
                 'name': 'npc_dota_hero_axe' if hero else 'item_blink', 'name_loc': 'fixture'}
            ]}}})
        with io.BytesIO() as stream, Image.new('RGB', (16, 16), 'red') as image:
            image.save(stream, 'PNG')
            return httpx.Response(200, content=stream.getvalue())
    def client():
        result = httpx.AsyncClient(transport=httpx.MockTransport(artwork), trust_env=False)
        asset_clients.append(result)
        return result
    return AssetManager(root, activate=activate, client_factory=client)
def factory():
    def blocked(request):
        raise AssertionError("No network during distribution smoke")
    client = httpx.AsyncClient(transport=httpx.MockTransport(blocked))
    clients.append(client)
    return client

async def check():
    replies = []
    async def send(reply):
        replies.append(reply)
    if entry.name == "main.py":
        from astrbot_plugin_dota2forge.runtime import Runtime, State
        from astrbot_plugin_dota2forge.identity import Caller
        caller = Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")
        data = Path.cwd() / "astrbot-data"
        pending = Runtime({}, data, client_factory=factory, asset_manager_factory=asset_factory)
        def configured():
            return Runtime(
                {"stratz_token": "synthetic-token", "reply_mode": "text"},
                data, client_factory=factory, asset_manager_factory=asset_factory,
            )
    else:
        from Dota2UID.runtime import Runtime, State
        from Dota2UID.commands import Caller
        caller = Caller("onebot", "bot", "user", "connection")
        data = Path.cwd() / "gscore-data/config.toml"
        pending = Runtime(data, client_factory=factory, asset_manager_factory=asset_factory)
        configured = lambda: Runtime(
            data, client_factory=factory, asset_manager_factory=asset_factory,
        )
    await pending.start()
    assert pending.state == State.AWAITING_CONFIG and pending.client_closed and not clients
    await pending._assets.manager.wait()
    assert pending.asset_status.state == 'ready' and len(asset_requests) == 19
    await pending.close()
    if entry.name != "main.py":
        updated = data.read_text("utf-8").replace(
            'stratz_token = ""', 'stratz_token = "synthetic-token"'
        ).replace('reply_mode = "image"', 'reply_mode = "text"')
        data.write_text(updated, encoding="utf-8")
    ready = configured()
    await ready.start()
    assert ready.state == State.READY and len(clients) == 1
    if entry.name == "main.py":
        await ready.dispatch(caller, "do绑定", "123", send)
        assert "绑定已保存" in replies[-1].text
    else:
        assert "绑定已保存" in (await ready.handle(caller, "do绑定", "123"))[0]
    await ready.close()
    assert clients[-1].is_closed
    restored = configured()
    await restored.start()
    if entry.name == "main.py":
        await restored.dispatch(caller, "do账号", "", send)
        assert "123" in replies[-1].text
    else:
        assert "已绑定" in (await restored.handle(caller, "do账号", ""))[0]
        from Dota2UID.config import load_config
        from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository
        binding = await SQLiteBindingRepository(data.with_name("bindings.sqlite3")).get(
            caller.identity(load_config(data))
        )
        assert binding is not None and binding.account_id.value == 123
    await restored.close()
    assert all(client.is_closed for client in clients)
    assert all(client.is_closed for client in asset_clients) and len(asset_requests) == 19
asyncio.run(check())
if (entry.parent / 'deployment.json').is_file():
    asyncio.run(manager.close())
print("Pinned dependencies, automatic assets, configuration, shutdown and persistence passed.")
"""


def offline_astrbot_requirements(plugin: Path, wheels: Path) -> list[str]:
    """Map public URLs to identical local wheels, retaining SHA256 verification."""
    lines = (plugin / "requirements.txt").read_text("utf-8").splitlines()
    references = [line for line in lines if " @ " in line]
    if references and references != public_requirements(plugin):
        raise ValueError("Requirements do not match the public runtime manifest")
    result = []
    for line in lines:
        if " @ " not in line:
            result.append(line)
            continue
        requirement, url = line.split(" @ ", 1)
        parsed = urlsplit(url)
        filename = Path(parsed.path).name
        wheel = wheels.resolve() / filename
        if not wheel.is_file():
            raise ValueError(f"Missing staged wheel {filename}")
        if parsed.fragment != "sha256=" + hashlib.sha256(wheel.read_bytes()).hexdigest():
            raise ValueError(f"Staged wheel checksum mismatch: {filename}")
        result.append(f"{requirement} @ {wheel.as_uri()}#{parsed.fragment}")
    return result


def smoke_distributions(candidate: Path, wheels: Path) -> None:
    candidate, wheels = candidate.resolve(), wheels.resolve()
    manifest = json.loads((candidate / "manifest.json").read_text("utf-8"))
    for name, digest in manifest["files_sha256"].items():
        path = (candidate / name).resolve()
        if (
            not path.is_relative_to(candidate)
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Candidate checksum mismatch")
    astrbot_requirements = offline_astrbot_requirements(
        candidate / "astrbot_plugin_dota2forge", wheels
    )
    for plugin, entry in (("astrbot_plugin_dota2forge", "main.py"), ("Dota2UID", "__init__.py")):
        with tempfile.TemporaryDirectory(prefix="dota2forge-distribution-") as temp:
            directory = Path(temp)
            environment = directory / "venv"
            subprocess.run(
                ["uv", "venv", "--offline", "--python", sys.executable, str(environment)],
                check=True,
            )
            python = environment / (
                "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
            )
            install = [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-cache",
                "--python",
                str(python),
                "--no-index",
                "--find-links",
                str(wheels),
            ]
            if plugin.startswith("astrbot"):
                requirements_path = directory / "astrbot-requirements.txt"
                requirements_path.write_text(
                    "\n".join(astrbot_requirements) + "\n", encoding="utf-8"
                )
                install.extend(["-r", str(requirements_path)])
            else:
                project = tomllib.loads((candidate / plugin / "pyproject.toml").read_text("utf-8"))
                install.extend(project["project"]["dependencies"])
            subprocess.run(install, check=True)
            subprocess.run(
                [str(python), "-I", "-B", "-c", SMOKE, str(candidate / plugin / entry)],
                cwd=directory,
                check=True,
            )
            print(f"SDK-free local distribution smoke passed: {plugin}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--wheels", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        smoke_distributions(args.candidate, args.wheels)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        print("Distribution smoke failed. Stage matching wheels and recheck candidate checksums.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

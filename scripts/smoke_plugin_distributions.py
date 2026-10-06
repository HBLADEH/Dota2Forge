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

SMOKE = r"""
import asyncio
import importlib.util
import sys
from pathlib import Path
import httpx

entry = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    "release_guard", entry.parent / "_dota2forge_bootstrap.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.verify_dependencies(str(entry))
assert importlib.util.find_spec("astrbot") is None
assert importlib.util.find_spec("gsuid_core") is None
clients = []
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
        pending = Runtime({}, data, client_factory=factory)
        def configured():
            return Runtime(
                {"stratz_token": "synthetic-token", "reply_mode": "text"},
                data, client_factory=factory,
            )
    else:
        from Dota2UID.runtime import Runtime, State
        from Dota2UID.commands import Caller
        caller = Caller("onebot", "bot", "user", "connection")
        data = Path.cwd() / "gscore-data/config.toml"
        pending = Runtime(data, client_factory=factory)
        configured = lambda: Runtime(data, client_factory=factory)
    await pending.start()
    assert pending.state == State.AWAITING_CONFIG and pending.client_closed and not clients
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
asyncio.run(check())
print("Pinned dependencies, first configuration, shutdown and binding persistence passed.")
"""


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
                install.extend(["-r", str(candidate / plugin / "requirements.txt")])
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

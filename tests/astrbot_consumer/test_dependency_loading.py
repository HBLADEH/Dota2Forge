"""AstrBot's dependency preference invalidates each declared top-level package.

Exercise that host behavior in an isolated SDK-free process so a dependent
consumer cannot retain cards/errors from a previous shared-package import.
"""

import subprocess
import sys
from importlib.resources import files


def test_declared_dependency_reload_keeps_consumer_and_renderer_types_consistent():
    requirements = files("astrbot_plugin_dota2forge").joinpath("host/requirements.txt")
    code = r"""
import asyncio
import importlib
import importlib.metadata
import sys
from pathlib import Path
from packaging.requirements import Requirement
import pytest_socket

roots = {
    "astrbot-plugin-dota2forge": "astrbot_plugin_dota2forge",
    "dota2forge-core": "dota2forge_core",
    "dota2forge-renderer": "dota2forge_renderer",
}
requested = set(Requirement(line).name for line in Path(sys.argv[1]).read_text().splitlines())
pending = list(requested)
while pending:
    name = pending.pop()
    # The host target contains the three project wheels; built-in dependencies
    # are not candidates for preference or dependency expansion in that target.
    if name not in roots:
        continue
    for dependency in importlib.metadata.requires(name) or ():
        dependency_name = Requirement(dependency).name
        if dependency_name not in requested:
            requested.add(dependency_name)
            pending.append(dependency_name)
loop = asyncio.new_event_loop()
pytest_socket.disable_socket()
try:
    for cycle in range(2):
        for name in sorted(requested):
            root = roots.get(name)
            if root is None:
                continue
            for module in tuple(sys.modules):
                if module == root or module.startswith(root + "."):
                    del sys.modules[module]
            importlib.import_module(root)
        from astrbot_plugin_dota2forge.application import AstrApplication, AstrImageReply
        from dota2forge_core import PlatformIdentity
        from dota2forge_renderer import AsyncRenderer
        async def check():
            renderer = AsyncRenderer()
            application = AstrApplication(object(), object(), renderer)
            try:
                replies = await application.handle(
                    PlatformIdentity("test", "qq", "bot", "user"), "dota菜单", ""
                )
                assert len(replies) == 1 and isinstance(replies[0], AstrImageReply)
                assert replies[0].artifact.data.startswith(bytes([137, 80, 78, 71]))
            finally:
                await application.close()
        loop.run_until_complete(check())
finally:
    loop.run_until_complete(loop.shutdown_default_executor())
    loop.close()
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(requirements)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

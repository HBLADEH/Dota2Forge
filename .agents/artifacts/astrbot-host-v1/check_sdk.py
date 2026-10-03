"""Explicit installed AstrBot SDK check; synthetic config and temporary data only.

Run with the host interpreter and explicit --sdk-root/--packages arguments.
This does not contact a platform, query STRATZ, or verify a running StarManager.
"""

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.packages), str(args.sdk_root)]
    with tempfile.TemporaryDirectory(prefix="dota2forge-astrbot-sdk-") as directory:
        os.environ["ASTRBOT_ROOT"] = directory
        from astrbot import __version__
        from astrbot.core.star.filter.command import CommandFilter
        from astrbot.core.star.star_handler import star_handlers_registry
        from astrbot.core.utils.pip_installer import _ensure_plugin_dependencies_preferred
        from astrbot.core.utils.requirements_utils import extract_requirement_names

        requested = extract_requirement_names(str(args.requirements))
        _ensure_plugin_dependencies_preferred(str(args.packages), requested)

        spec = importlib.util.spec_from_file_location(
            "sdk_dota2forge",
            args.bridge,
            loader=SourceFileLoader("sdk_dota2forge", str(args.bridge)),
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        handlers = star_handlers_registry.get_handlers_by_module_name(spec.name)
        commands = [
            event_filter
            for handler in handlers
            for event_filter in handler.event_filters
            if isinstance(event_filter, CommandFilter)
        ]
        assert len(commands) == 11

        class SyntheticEvent:
            is_at_or_wake_command = True

            def __init__(self, message):
                self.message = message
                self.extras = {}

            def get_message_str(self):
                return self.message

            def set_extra(self, key, value):
                self.extras[key] = value

        for name, text in (("dota绑定", "01 extra"), ("dota菜单", "")):
            event = SyntheticEvent((name + " " + text).strip())
            selected = next(command for command in commands if command.command_name == name)
            assert selected.filter(event, {})
            assert event.extras["parsed_params"] == {"text": text}

        async def lifecycle():
            from astrbot_plugin_dota2forge.identity import Caller

            plugin = module.Dota2ForgePlugin(object(), {"stratz_token": "synthetic-token"})
            await plugin.initialize()
            await plugin.initialize()
            assert plugin.runtime.state.value == "ready"
            replies = []

            async def capture(reply):
                replies.append(reply)

            await plugin.runtime.dispatch(
                Caller("qq", "connection", "bot", "user"), "dota菜单", "", capture
            )
            assert len(replies) == 1 and replies[0].artifact.data.startswith(b"\x89PNG")
            await plugin.terminate()
            await plugin.terminate()
            assert plugin.runtime.state.value == "stopped" and plugin.runtime.client_closed

        asyncio.run(lifecycle())
        print(
            json.dumps(
                {
                    "sdk_version": __version__,
                    "commands": len(commands),
                    "greedy_parameters": True,
                    "initialize_terminate": True,
                    "client_closed": True,
                    "menu_render_after_dependency_preference": True,
                    "real_platform_messages": False,
                }
            )
        )


if __name__ == "__main__":
    main()

"""Explicit real APScheduler/SDK check with synthetic configuration and no sends."""

import argparse
import ast
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.packages), str(args.sdk_root)]
    config = ModuleType("gsuid_core.config")
    config.core_config = SimpleNamespace(get_config=lambda _: 90)
    logger = ModuleType("gsuid_core.logger")
    logger.logger = SimpleNamespace(info=lambda *args, **kwargs: None)
    i18n = ModuleType("gsuid_core.i18n")
    i18n.t = lambda key, **kwargs: key
    sys.modules.update(
        {"gsuid_core.config": config, "gsuid_core.logger": logger, "gsuid_core.i18n": i18n}
    )
    from Dota2UID.runtime import Runtime
    from Dota2UID.subscriptions import SUBSCRIPTION_COMMANDS
    from gsuid_core import __version__
    from gsuid_core.aps import scheduler
    from gsuid_core.models import Event

    target_send = next(
        node
        for node in ast.walk(
            ast.parse((args.sdk_root / "gsuid_core" / "bot.py").read_text("utf-8"))
        )
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "target_send"
    )
    assert {"bot_id", "bot_self_id", "wait_recall"} <= {
        argument.arg for argument in target_send.args.args
    }
    Event(
        bot_id="onebot",
        bot_self_id="synthetic-bot",
        user_id="synthetic-user",
        WS_BOT_ID="synthetic-connection",
        user_type="direct",
    )
    assert len(SUBSCRIPTION_COMMANDS) == 6

    async def check(directory):
        path = Path(directory) / "config.toml"
        path.write_text(
            'namespace="sdk-test"\nstratz_token="synthetic-token"\n'
            'timeout_seconds=2\nreply_mode="text"\nsubscriptions_enabled=true\n'
            '[platforms]\nonebot="qq"\n',
            encoding="utf-8",
        )

        async def send(_event, _text):
            raise AssertionError("No messages in SDK check")

        scheduler.start()
        for _iteration in range(2):
            runtime = Runtime(path)
            await runtime.start()
            assert runtime.state.value == "ready" and runtime.subscriptions_enabled
            await runtime.poll_subscriptions(send)
            job = scheduler.add_job(
                runtime.poll_subscriptions,
                "interval",
                seconds=60,
                args=[send],
                id="Dota2UID-subscriptions",
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
            assert job.max_instances == 1 and job.coalesce
            assert len(scheduler.get_jobs()) == 1
            scheduler.remove_job(job.id)
            await runtime.close()
            await runtime.close()
            assert runtime.client_closed and not scheduler.get_jobs()
        scheduler.shutdown(wait=False)
        await asyncio.sleep(0)

    with tempfile.TemporaryDirectory(prefix="dota2forge-gscore-sdk-") as directory:
        asyncio.run(check(directory))
    print(
        json.dumps(
            {
                "sdk_version": __version__,
                "real_scheduler_register_remove": True,
                "runtime_reload_twice": True,
                "client_closed": True,
                "subscription_commands": 6,
                "real_platform_messages": False,
            }
        )
    )


if __name__ == "__main__":
    main()

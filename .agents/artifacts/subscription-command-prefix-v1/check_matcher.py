"""Read-only isolated GsCore Event/Trigger/trie check with synthetic messages."""

import ast
import asyncio
import hashlib
import json
import socket
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

sdk, root, output = (Path(value).resolve() for value in sys.argv[1:4])
loop = asyncio.new_event_loop()


def deny(*args, **kwargs):
    raise AssertionError("External network disabled")


socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.socket.sendto = deny
socket.getaddrinfo = deny
sys.modules["gsuid_core"] = ModuleType("gsuid_core")
bot = sys.modules["gsuid_core.bot"] = ModuleType("gsuid_core.bot")
bot.Bot = object
sv = sys.modules["gsuid_core.sv"] = ModuleType("gsuid_core.sv")
sv.SV = object
sv.SL = SimpleNamespace(lst={})
hashes = {}


def load(name):
    path = sdk / "gsuid_core" / (name + ".py")
    data = path.read_bytes()
    hashes[name] = hashlib.sha256(data).hexdigest()
    fullname = "gsuid_core." + name
    module = ModuleType(fullname)
    sys.modules[fullname] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


models, trigger, index = (load(name) for name in ("models", "trigger", "trigger_index"))
source = root / "adapters/Dota2UID/src/Dota2UID/subscriptions.py"
values = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in ast.parse(source.read_text("utf-8")).body
    if isinstance(node, ast.Assign)
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id in {"SUBSCRIPTION_COMMANDS", "SUBSCRIPTION_PATTERN"}
}
commands, pattern = values["SUBSCRIPTION_COMMANDS"], values["SUBSCRIPTION_PATTERN"]


async def handler(*args):
    pass


async def match(keywords, raw_text, *, fixed=False):
    triggers = {key: trigger.Trigger("command", key, handler, block=True) for key in keywords}
    regex = {pattern: trigger.Trigger("regex", pattern, handler, block=True)} if fixed else {}
    sv.SL.lst = {"synthetic-service": SimpleNamespace(TL={"command": triggers, "regex": regex})}
    candidates = index.TriggerIndex().candidates(models.Event(raw_text=raw_text))
    event = models.Event(raw_text=raw_text)
    valid = {item: 6 for item in candidates if item.check_command(event)}
    selected = sorted(valid, key=lambda item: (not item.prefix, valid[item]))[0]
    parsed = await selected.get_command(event)
    if "subscription_args" in parsed.regex_dict:
        return "do订阅", parsed.regex_dict["subscription_args"].strip()
    return parsed.command, parsed.text


async def check():
    player_message = "do订阅玩家 123456789"
    old = await match(commands, player_message)
    reordered = await match(tuple(reversed(commands)), player_message)
    assert old == reordered == ("do订阅", "玩家 123456789")
    fixed_commands = tuple(key for key in commands if key != "do订阅")
    rows = []
    for raw, expected in (
        (player_message, ("do订阅玩家", "123456789")),
        ("do订阅比赛 9001", ("do订阅比赛", "9001")),
        ("do订阅列表", ("do订阅列表", "")),
        ("do订阅 比赛 123456789", ("do订阅", "比赛 123456789")),
        ("do订阅", ("do订阅", "")),
        ("do订阅\t段位\t123456789", ("do订阅", "段位\t123456789")),
        ("do订阅　日报　123456789", ("do订阅", "日报　123456789")),
        ("do订阅 未知 123", ("do订阅", "未知 123")),
        ("do订阅玩家 123 extra", ("do订阅玩家", "123 extra")),
    ):
        actual = await match(fixed_commands, raw, fixed=True)
        assert actual == expected, (raw, actual)
        rows.append({"raw_text": raw, "keyword": actual[0], "text": actual[1]})
    assert all(
        hashlib.sha256((sdk / "gsuid_core" / (name + ".py")).read_bytes()).hexdigest() == digest
        for name, digest in hashes.items()
    )
    output.write_text(
        json.dumps(
            {"sdk_source_sha256": hashes, "before": old, "reordered": reordered, "fixed": rows},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "utf-8",
    )


try:
    loop.run_until_complete(check())
finally:
    loop.close()
print("Actual Event/Trigger/trie: before reproduced, reordering ineffective, 9 fixed routes pass.")

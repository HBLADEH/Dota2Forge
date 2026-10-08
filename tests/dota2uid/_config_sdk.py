"""Small SDK-free native config fixture, matching tagged JSON and exact-type writes."""

import inspect
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType


@dataclass
class GsStrConfig:
    title: str
    desc: str
    data: str
    options: list[str] = field(default_factory=list)
    regex: str | None = None
    details: dict | None = None
    secret: bool = False


@dataclass
class GsBoolConfig:
    title: str
    desc: str
    data: bool
    secret: bool = False


@dataclass
class GsIntConfig:
    title: str
    desc: str
    data: int
    max_value: int | None = None
    options: list[int] = field(default_factory=list)
    secret: bool = False


@dataclass
class GsFloatConfig:
    title: str
    desc: str
    data: float
    min_value: float | None = None
    max_value: float | None = None
    secret: bool = False


def install_config_sdk(monkeypatch):
    registry = {}
    models = ModuleType("gsuid_core.utils.plugins_config.models")
    classes = (GsStrConfig, GsBoolConfig, GsIntConfig, GsFloatConfig)
    types = {kind.__name__: kind for kind in classes}
    for name, kind in types.items():
        setattr(models, name, kind)

    class StringConfig:
        def __new__(cls, name, path, fields):
            if name in registry:
                return registry[name]
            instance = super().__new__(cls)
            registry[name] = instance
            return instance

        def __init__(self, name, path, fields):
            self.config_name = name
            self.CONFIG_PATH = path
            self.config_list = self.config_default = fields
            caller_file = Path(inspect.currentframe().f_back.f_code.co_filename)
            parts = caller_file.parts
            self.plugin_name = next(
                (
                    parts[index + 1]
                    for index in range(1, len(parts) - 1)
                    if parts[index - 1] == "gsuid_core" and parts[index] == "plugins"
                ),
                None,
            )
            self.config = fields
            if path.exists():
                stored = json.loads(path.read_text("utf-8"))
                self.config = {}
                for key, raw in stored.items():
                    body = dict(raw)
                    kind = types[body.pop("type")]
                    item = kind(**body)
                    default = fields[key]
                    item.title, item.desc, item.secret = default.title, default.desc, default.secret
                    self.config[key] = item
            self.write_config()

        def write_config(self):
            payload = {
                key: {"type": type(value).__name__, **asdict(value)}
                for key, value in self.config.items()
            }
            self.CONFIG_PATH.write_text(json.dumps(payload, indent=2), "utf-8")

        def get_config(self, key):
            return self.config[key]

        def set_config(self, key, value):
            current = self.config[key].data
            if type(value) is type(current):
                self.config[key].data = value
            elif isinstance(self.config[key], GsFloatConfig) and type(value) is int:
                self.config[key].data = float(value)
            else:
                return False
            self.write_config()
            return True

    manager = ModuleType("gsuid_core.utils.plugins_config.gs_config")
    manager.StringConfig = StringConfig
    manager.all_config_list = registry
    for name in ("gsuid_core", "gsuid_core.utils", "gsuid_core.utils.plugins_config"):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, ModuleType(name))
    monkeypatch.setitem(sys.modules, models.__name__, models)
    monkeypatch.setitem(sys.modules, manager.__name__, manager)
    return registry

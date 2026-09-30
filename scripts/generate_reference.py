"""Generate package reference from TOML without importing application code."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("docs/generated/packages.md")


def read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def package_configs(root: Path) -> list[Path]:
    members = read_toml(root / "pyproject.toml")["tool"]["uv"]["workspace"]["members"]
    paths: list[Path] = []
    for member in members:
        if Path(member).is_absolute() or ".." in Path(member).parts or "*" in member:
            raise ValueError(f"Workspace member must be an explicit relative path: {member}")
        path = root / member / "pyproject.toml"
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or invalid workspace member: {member}")
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate workspace members")
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def render(root: Path) -> str:
    lines = [
        "# Dota2Forge 包参考",
        "",
        "由 `scripts/generate_reference.py` 从 workspace 与各包 pyproject.toml 生成。",
        "",
        "| 分发包 | 版本 | 导入包 | 运行依赖 |",
        "| --- | --- | --- | --- |",
    ]
    for path in package_configs(root):
        config = read_toml(path)
        project = config["project"]
        imports = ", ".join(
            Path(p).name for p in config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        )
        dependencies = ", ".join(project.get("dependencies", [])) or "无"
        lines.append(f"| {project['name']} | {project['version']} | {imports} | {dependencies} |")
    lines.extend(
        [
            "",
            "本表仅描述包元数据；实现边界见 [当前架构](../architecture.md)。"
            "配置、命令与 AI Tool 注册表尚未实现。",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = render(ROOT)
    path = ROOT / OUTPUT
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            print(f"Generated reference drift: {OUTPUT}", file=sys.stderr)
            return 1
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate deterministic thin host repositories and reviewable store submission drafts."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tempfile
import tomllib
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "dota2forge-core": "packages/dota2forge-core",
    "dota2forge-renderer": "packages/dota2forge-renderer",
    "dota2uid": "adapters/Dota2UID",
    "astrbot-plugin-dota2forge": "adapters/astrbot_plugin_dota2forge",
}
MAX_ASTRBOT_ZIP_BYTES = 16_000_000
PROJECT_SOURCE_URL = "https://github.com/HBLADEH/Dota2Forge/blob/main"
ICON_SOURCE = "docs/assets/branding/juggernaut-icon-v1.png"
GS_RUNTIME_SOURCE = "scripts/gscore_public_runtime.py"
GS_INSTALL_GUIDE = "docs/cookbook/gscore-public-install.md"
ASTR_INSTALL_GUIDE = "docs/cookbook/astrbot-public-install.md"
# Only explicitly reviewed, identity-free images belong in the standalone plugin ZIPs.
SHOWCASE_IMAGES = {
    "Dota2UID": {
        "hero-items.png": "docs/assets/screenshots/astrbot/hero-items.png",
    },
    "astrbot_plugin_dota2forge": {
        "hero-items.png": "docs/assets/screenshots/astrbot/hero-items.png",
    },
}
PRELUDE = (
    "from ._dota2forge_bootstrap import verify_dependencies as _verify_dependencies\n"
    "\n_verify_dependencies(__file__)\n\n"
)


def text_bytes(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").encode("utf-8")


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def repository(value: str, name: str) -> tuple[str, str]:
    match = re.fullmatch(r"https://github\.com/([A-Za-z0-9_-]+)/" + re.escape(name), value)
    if match is None:
        raise ValueError(f"Expected an HTTPS GitHub repository named {name}")
    return value, match[1]


def versions(root: Path) -> dict[str, str]:
    result = {}
    for name, folder in PACKAGES.items():
        project = tomllib.loads((root / folder / "pyproject.toml").read_text("utf-8"))["project"]
        version = project.get("version")
        if (
            project.get("name") != name
            or not isinstance(version, str)
            or not re.fullmatch(r"[0-9][0-9A-Za-z.!+-]{0,63}", version)
        ):
            raise ValueError("Invalid package name or version")
        if project.get("requires-python") != ">=3.12":
            raise ValueError("Recheck host compatibility before changing the Python baseline")
        result[name] = version
    return result


def third_party_requirements(root: Path) -> list[str]:
    """Use the package metadata, rejecting drift between implemented consumers."""
    constraints: dict[str, set[str]] = {"httpx": set(), "pillow": set()}
    for folder in PACKAGES.values():
        project = tomllib.loads((root / folder / "pyproject.toml").read_text("utf-8"))["project"]
        declared = list(project.get("dependencies", []))
        declared.extend(project.get("optional-dependencies", {}).get("stratz", []))
        for dependency in declared:
            if not isinstance(dependency, str):
                raise ValueError("Dependency declarations must be strings")
            for name in constraints:
                if re.fullmatch(rf"{name}(?:[<>=!~].*)?", dependency, re.IGNORECASE):
                    constraints[name].add(dependency.lower())
    if any(len(values) != 1 for values in constraints.values()):
        raise ValueError("Recheck HTTPX/Pillow constraints across implemented consumers")
    return [next(iter(values)) for _, values in sorted(constraints.items())]


def archive(contents: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as output:
        for name, data in sorted(contents.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            output.writestr(info, data, compresslevel=9)
    return buffer.getvalue()


def readme(root: Path, plugin: str, repo: str, version: str, public_runtime: bool = False) -> bytes:
    adapter = "astrbot-plugin-dota2forge" if plugin.startswith("astrbot") else "dota2uid"
    content = (root / PACKAGES[adapter] / "README.md").read_text(encoding="utf-8")
    marker = "<!-- distribution-release -->"
    if content.count(marker) != 1:
        raise ValueError("Plugin README must contain one distribution release marker")
    icon_name = "logo.png" if plugin.startswith("astrbot") else "ICON.png"
    content = content.replace(f"../../{ICON_SOURCE}", icon_name)
    for name, source in SHOWCASE_IMAGES.get(plugin, {}).items():
        content = content.replace(f"../../{source}", f"screenshots/{name}")
    if public_runtime:
        content = re.sub(r"]\(\.\./\.\./(?:docs/|\.agents/)[^)]+\)", "](INSTALL.md)", content)
    elif plugin.startswith("astrbot"):
        pinned = versions(root)
        packages = " ".join(
            f"{name}{'[stratz]' if name != 'dota2forge-renderer' else ''}=={pinned[name]}"
            for name in ("dota2forge-core", "dota2forge-renderer", "astrbot-plugin-dota2forge")
        )
        content = content.replace(
            ".venv/Scripts/python.exe data/plugins/astrbot_plugin_dota2forge/install_runtime.py "
            "--host-python .venv/Scripts/python.exe",
            f".venv/Scripts/python.exe -m pip install {packages}",
        )
        content = content.replace(
            "三个组件从本插件 GitHub Releases 下载，安装器核对版本与摘要，并检查依赖冲突。",
            "本候选按包名安装，需自行准备匹配运行包，尚未附带公开下载清单。",
        )
    elif plugin == "Dota2UID":
        command = (
            ".venv/Scripts/python.exe gsuid_core/plugins/Dota2UID/install_runtime.py "
            "--host-python .venv/Scripts/python.exe"
        )
        pinned = versions(root)
        packages = " ".join(
            f'"{name}{"[stratz]" if name != "dota2forge-renderer" else ""}=={pinned[name]}"'
            for name in ("dota2forge-core", "dota2forge-renderer", "dota2uid")
        )
        content = content.replace(command, f".venv/Scripts/python.exe -m pip install {packages}")
        content = content.replace(
            "三个运行包来自GitHub Releases，安装器校验固定版本与SHA256；共享库更新后必须冷启动。",
            "本目录按PyPI包名解析锁定版本，生成器未发布包；需先保证依赖可取得。共享库更新后必须冷启动。",
        )
    content = content.replace("](../../LICENSE)", "](LICENSE)")
    content = content.replace("](../../", f"]({PROJECT_SOURCE_URL}/")
    content = content.replace(
        marker, f"> 发行版本：`{version}` · [目标分发仓库]({repo})。由主仓同一源码生成。"
    )
    if plugin.startswith("astrbot"):
        # Cloud renders repository-relative URLs against its own page origin.
        raw = repo.replace("https://github.com/", "https://raw.githubusercontent.com/")
        content = content.replace(f'src="{icon_name}"', f'src="{raw}/main/{icon_name}"')
        for name in SHOWCASE_IMAGES.get(plugin, {}):
            content = content.replace(f"](screenshots/{name})", f"]({raw}/main/screenshots/{name})")
        for name in ("INSTALL.md", "LICENSE"):
            content = content.replace(f"]({name})", f"]({repo}/blob/main/{name})")
    return content.encode("utf-8")


def runtime_wheels(wheels: Path, pinned: dict[str, str], repo: str) -> bytes:
    result = {}
    for name, version in sorted(pinned.items()):
        filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        path = wheels / filename
        with ZipFile(path) as wheel:
            metadata_name = f"{name.replace('-', '_')}-{version}.dist-info/METADATA"
            metadata = BytesParser().parsebytes(wheel.read(metadata_name))
            if (
                metadata["Name"] != name
                or metadata["Version"] != version
                or metadata["Requires-Python"] != ">=3.12"
            ):
                raise ValueError("Runtime wheel metadata does not match the release")
        result[name] = {
            "filename": filename,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    adapter = "dota2uid" if "dota2uid" in pinned else "astrbot-plugin-dota2forge"
    return json_bytes(
        {
            "schema_version": 1,
            "repository": repo,
            "release_tag": f"v{pinned[adapter]}",
            "wheels": result,
        }
    )


def distribution_files(
    root: Path,
    astrbot_repo: str,
    gscore_repo: str,
    gscore_wheels: Path | None = None,
    astrbot_wheels: Path | None = None,
) -> dict[str, bytes]:
    astrbot_repo, author = repository(astrbot_repo, "astrbot_plugin_dota2forge")
    gscore_repo, gs_author = repository(gscore_repo, "Dota2UID")
    if gscore_wheels is not None:
        gscore_wheels = gscore_wheels.resolve()
        if not gscore_wheels.is_relative_to(root.resolve()):
            raise ValueError(
                "Keep runtime wheel inputs inside the source repository for provenance"
            )
    if astrbot_wheels is not None:
        astrbot_wheels = astrbot_wheels.resolve()
        if not astrbot_wheels.is_relative_to(root.resolve()):
            raise ValueError("Keep AstrBot runtime wheels inside the source repository")
    release_versions = versions(root)
    third_party = third_party_requirements(root)
    bootstrap = text_bytes(root / "scripts/plugin_bootstrap.py")
    license_text = text_bytes(root / "LICENSE")
    icon = (root / ICON_SOURCE).read_bytes()
    astr_host = root / "adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host"
    artifacts: dict[str, bytes] = {}
    for plugin, adapter in (
        ("astrbot_plugin_dota2forge", "astrbot-plugin-dota2forge"),
        ("Dota2UID", "dota2uid"),
    ):
        pinned = {
            name: release_versions[name]
            for name in ("dota2forge-core", "dota2forge-renderer", adapter)
        }
        requirements = [
            f"{name}{'[stratz]' if name != 'dota2forge-renderer' else ''}=={version}"
            for name, version in sorted(pinned.items())
        ]
        dependencies = requirements + third_party
        repo = astrbot_repo if plugin.startswith("astrbot") else gscore_repo
        public_wheels = astrbot_wheels if plugin.startswith("astrbot") else gscore_wheels
        content = {
            "LICENSE": license_text,
            "README.md": readme(
                root,
                plugin,
                repo,
                release_versions[adapter],
                public_runtime=public_wheels is not None,
            ),
            "logo.png" if plugin.startswith("astrbot") else "ICON.png": icon,
            "_dota2forge_bootstrap.py": bootstrap,
            "release.json": json_bytes({"schema_version": 1, "plugin": plugin, "versions": pinned}),
        }
        content.update(
            {
                f"screenshots/{name}": (root / source).read_bytes()
                for name, source in SHOWCASE_IMAGES.get(plugin, {}).items()
            }
        )
        if plugin.startswith("astrbot"):
            metadata = (astr_host / "metadata.yaml").read_text("utf-8")
            # Keep template compatibility fields and set the distribution identity.
            for key, value in {
                "repo": repo,
                "author": author,
                "version": release_versions[adapter],
            }.items():
                metadata, count = re.subn(rf"(?m)^{key}: .+$", f"{key}: {value}", metadata)
                if count != 1:
                    raise ValueError("Host metadata must declare repo, author and version once")
            content.update(
                {
                    "main.py": PRELUDE.encode() + text_bytes(astr_host / "main.py.template"),
                    "metadata.yaml": metadata.encode("utf-8"),
                    "_conf_schema.json": text_bytes(astr_host / "_conf_schema.json"),
                    "requirements.txt": ("\n".join(dependencies) + "\n").encode(),
                }
            )
        else:
            content.update(
                {
                    "__init__.py": PRELUDE.encode()
                    + text_bytes(root / "adapters/Dota2UID/src/Dota2UID/host_entry.py.template"),
                    "config.example.toml": text_bytes(
                        root / "adapters/Dota2UID/config.example.toml"
                    ),
                    "pyproject.toml": (
                        '[project]\nname = "dota2uid-host-entry"\n'
                        f'version = "{release_versions[adapter]}"\nrequires-python = ">=3.12"\n'
                        f"dependencies = {json.dumps(dependencies)}\n"
                        f"gscore_auto_update_dep = {json.dumps(requirements)}\n"
                    ).encode(),
                }
            )
        if public_wheels is not None:
            content["install_runtime.py"] = text_bytes(root / GS_RUNTIME_SOURCE)
            content["runtime-wheels.json"] = runtime_wheels(public_wheels, pinned, repo)
            guide = ASTR_INSTALL_GUIDE if plugin.startswith("astrbot") else GS_INSTALL_GUIDE
            content["INSTALL.md"] = text_bytes(root / guide)
        packed = archive(content)
        if plugin.startswith("astrbot") and len(packed) > MAX_ASTRBOT_ZIP_BYTES:
            raise ValueError("AstrBot ZIP exceeds the 16 MB distribution limit")
        artifacts.update({f"{plugin}/{name}": data for name, data in content.items()})
        artifacts[f"{plugin}.zip"] = packed
    artifacts["gscore-index-entry.json"] = json_bytes(
        {
            "plugins": {
                "Dota2UID": {
                    "link": gscore_repo,
                    "branch": "main",
                    "avatar": f"https://raw.githubusercontent.com/{gs_author}/Dota2UID/main/ICON.png",
                    "cover": f"https://raw.githubusercontent.com/{gs_author}/Dota2UID/main/ICON.png",
                    "type": "tip",
                    "content": "普通",
                    "info": (
                        "Dota2Forge：查刀塔战绩、比赛详情和英雄热门出装，还能看段位和预估分数。"
                    ),
                    "installMsg": (
                        "第一次安装请先看插件里的 INSTALL.md：关闭 GsCore，用它的 Python "
                        "运行 install_runtime.py 安装所需组件，然后重新启动。"
                        "再按说明填写 STRATZ 密钥和插件标识（namespace）。"
                        "只在商店点击安装还不能直接使用。"
                        if gscore_wheels is not None
                        else "请按说明填写 STRATZ 密钥和插件标识（namespace），然后重新加载插件。"
                    ),
                    "alias": ["dota2", "dota2forge", "刀塔"],
                }
            },
            "tool_plugins": ["Dota2UID"],
        }
    )
    sources = [
        root / "LICENSE",
        root / "scripts/plugin_bootstrap.py",
        root / "scripts/build_plugin_distributions.py",
        root / ICON_SOURCE,
    ]
    sources.extend(
        root / source for images in SHOWCASE_IMAGES.values() for source in images.values()
    )
    for folder in PACKAGES.values():
        sources.append(root / folder / "pyproject.toml")
        if folder.startswith("adapters/"):
            sources.append(root / folder / "README.md")
        sources.extend(
            p
            for p in (root / folder / "src").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    sources.append(root / "adapters/Dota2UID/config.example.toml")
    if gscore_wheels is not None:
        sources.append(root / GS_RUNTIME_SOURCE)
        sources.append(root / GS_INSTALL_GUIDE)
        for name in ("dota2forge-core", "dota2forge-renderer", "dota2uid"):
            path = (
                gscore_wheels
                / f"{name.replace('-', '_')}-{release_versions[name]}-py3-none-any.whl"
            )
            sources.append(path)
    if astrbot_wheels is not None:
        sources.extend((root / GS_RUNTIME_SOURCE, root / ASTR_INSTALL_GUIDE))
        for name in ("dota2forge-core", "dota2forge-renderer", "astrbot-plugin-dota2forge"):
            sources.append(
                astrbot_wheels
                / f"{name.replace('-', '_')}-{release_versions[name]}-py3-none-any.whl"
            )
    artifacts["manifest.json"] = json_bytes(
        {
            "schema_version": 1,
            "status": "local_candidate",
            "versions": release_versions,
            "source_sha256": {
                p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(sources)
            },
            "files_sha256": {
                name: hashlib.sha256(data).hexdigest() for name, data in sorted(artifacts.items())
            },
        }
    )
    return artifacts


def build_distributions(
    root: Path,
    output: Path,
    astrbot_repo: str,
    gscore_repo: str,
    gscore_wheels: Path | None = None,
    astrbot_wheels: Path | None = None,
) -> Path:
    root, output = root.resolve(), output.absolute()
    if root.is_relative_to(output.resolve()):
        raise ValueError("Output must not replace or contain the source repository")
    artifacts = distribution_files(root, astrbot_repo, gscore_repo, gscore_wheels, astrbot_wheels)
    if output.exists():
        present = {p.relative_to(output).as_posix(): p for p in output.rglob("*") if p.is_file()}
        if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
            raise ValueError("Existing distribution contains symlinks")
        if set(present) != set(artifacts) or any(
            present[name].read_bytes() != data for name, data in artifacts.items()
        ):
            raise ValueError("Existing distribution differs; choose a new output directory")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".dota2forge-release-") as temp:
        staging = Path(temp) / "candidate"
        staging.mkdir()
        for name, data in artifacts.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        staging.rename(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--astrbot-repo", required=True)
    parser.add_argument("--gscore-repo", required=True)
    parser.add_argument(
        "--gscore-wheels", type=Path, help="Include a pinned GitHub Releases runtime installer"
    )
    parser.add_argument(
        "--astrbot-wheels", type=Path, help="Include AstrBot pinned runtime installer"
    )
    args = parser.parse_args(argv)
    try:
        destination = build_distributions(
            ROOT,
            args.output,
            args.astrbot_repo,
            args.gscore_repo,
            args.gscore_wheels,
            args.astrbot_wheels,
        )
    except (OSError, ValueError, KeyError):
        print("Distribution generation failed. Check source metadata, repository URLs and output.")
        return 1
    print(
        f"Local plugin candidates generated: {destination}. No packages or stores were published."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

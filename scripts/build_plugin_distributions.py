"""Generate deterministic host repositories and reviewable store submission drafts."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import tempfile
import tomllib
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
STRATZ_PACKAGES = {"dota2forge-core", "dota2uid", "astrbot-plugin-dota2forge"}
PACKAGES = {
    "dota2forge-core": "packages/dota2forge-core",
    "dota2forge-renderer": "packages/dota2forge-renderer",
    "dota2forge-assets": "packages/dota2forge-assets",
    "dota2uid": "adapters/Dota2UID",
    "astrbot-plugin-dota2forge": "adapters/astrbot_plugin_dota2forge",
}
MAX_ASTRBOT_ZIP_BYTES = 16_000_000
PROJECT_SOURCE_URL = "https://github.com/HBLADEH/Dota2Forge/blob/main"
ICON_SOURCE = "docs/assets/branding/juggernaut-icon-v1.png"
GS_RUNTIME_SOURCE = "scripts/gscore_public_runtime.py"
GS_BUNDLED_RUNTIME_SOURCE = "scripts/gscore_bundled_runtime.py"
GS_ADAPTER_SOURCE = "adapters/Dota2UID/src/Dota2UID"
GS_INSTALL_GUIDE = "docs/cookbook/gscore-public-install.md"
GS_BUNDLED_INSTALL_GUIDE = "docs/cookbook/gscore-bundled-install.md"
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


def source_repository_url(source_ref: str = "main") -> str:
    """Use reviewed source commits without accepting arbitrary branches or URL fragments."""
    if source_ref != "main" and re.fullmatch(r"[0-9a-f]{40}", source_ref) is None:
        raise ValueError("Source reference must be main or a full lowercase commit SHA")
    return PROJECT_SOURCE_URL.rsplit("/", 1)[0] + "/" + source_ref


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


def astrbot_version(version: str) -> str:
    """Translate supported Python package versions to Cloud's SemVer notation."""
    match = re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:(a|b|rc)(0|[1-9][0-9]*))?", version
    )
    if match is None:
        raise ValueError("AstrBot version requires a release or supported prerelease")
    base = ".".join(match.group(1, 2, 3))
    stage = match.group(4)
    return (
        base
        if stage is None
        else base + "-" + {"a": "alpha", "b": "beta", "rc": "rc"}[stage] + "." + match.group(5)
    )


def readme(
    root: Path,
    plugin: str,
    repo: str,
    version: str,
    public_runtime: bool = False,
    gscore_bundled: bool = False,
    source_ref: str = "main",
) -> bytes:
    source_url = source_repository_url(source_ref)
    adapter = "astrbot-plugin-dota2forge" if plugin.startswith("astrbot") else "dota2uid"
    content = (root / PACKAGES[adapter] / "README.md").read_text(encoding="utf-8")
    marker = "<!-- distribution-release -->"
    if content.count(marker) != 1:
        raise ValueError("Plugin README must contain one distribution release marker")
    icon_name = "logo.png" if plugin.startswith("astrbot") else "ICON.png"
    content = content.replace(f"../../{ICON_SOURCE}", icon_name)
    for name, source in SHOWCASE_IMAGES.get(plugin, {}).items():
        content = content.replace(f"../../{source}", f"screenshots/{name}")
    if gscore_bundled and plugin == "Dota2UID":
        content = bundled_readme(content)
    if gscore_bundled and plugin == "Dota2UID":
        content = re.sub(
            r"]\(\.\./\.\./docs/cookbook/(?:dota2uid|gscore-bundled-install)\.md\)",
            "](INSTALL.md)",
            content,
        )
    elif public_runtime or gscore_bundled:
        content = re.sub(r"]\(\.\./\.\./(?:docs/|\.agents/)[^)]+\)", "](INSTALL.md)", content)
    elif plugin.startswith("astrbot"):
        pinned = versions(root)
        packages = " ".join(
            f"{name}{'[stratz]' if name in STRATZ_PACKAGES else ''}=={pinned[name]}"
            for name in (
                "dota2forge-core",
                "dota2forge-renderer",
                "dota2forge-assets",
                "astrbot-plugin-dota2forge",
            )
        )
        content = content.replace(
            ".venv/Scripts/python.exe data/plugins/astrbot_plugin_dota2forge/install_runtime.py "
            "--host-python .venv/Scripts/python.exe",
            f".venv/Scripts/python.exe -m pip install {packages}",
        )
        content = content.replace(
            "四个组件从本插件 GitHub Releases 下载，安装器核对版本与摘要，并检查依赖冲突。",
            "本候选按包名安装，需自行准备匹配运行包，尚未附带公开下载清单。",
        )
    elif plugin == "Dota2UID":
        command = (
            ".venv/Scripts/python.exe gsuid_core/plugins/Dota2UID/install_runtime.py "
            "--host-python .venv/Scripts/python.exe"
        )
        pinned = versions(root)
        packages = " ".join(
            f'"{name}{"[stratz]" if name in STRATZ_PACKAGES else ""}=={pinned[name]}"'
            for name in ("dota2forge-core", "dota2forge-renderer", "dota2forge-assets", "dota2uid")
        )
        content = content.replace(command, f".venv/Scripts/python.exe -m pip install {packages}")
        content = content.replace(
            "四个运行包来自GitHub Releases，安装器校验固定版本与SHA256；共享库更新后必须冷启动。",
            "本目录按PyPI包名解析锁定版本，生成器未发布包；需先保证依赖可取得。共享库更新后必须冷启动。",
        )
    content = content.replace("](../../LICENSE)", "](LICENSE)")
    content = content.replace("](../../", f"]({source_url}/")
    display_version = astrbot_version(version) if plugin.startswith("astrbot") else version
    content = content.replace(
        marker,
        f"> 发行版本：`{display_version}` · [目标分发仓库]({repo})。由主仓同一源码生成。",
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


def bundled_readme(content: str) -> str:
    """Describe the generated bundled entry without changing legacy thin instructions."""
    content = content.replace(
        "公开运行包安装采用下述停机与冷启动流程。",
        "本分发采用随包运行库，安装与恢复采用下述流程。",
    )
    content = content.replace(
        "下述公开安装流程仍适用于现有 a4 和薄分发。",
        "下述步骤仅适用于本 bundled 分发；旧 a4 请使用旧版公开安装指南。",
    )
    content = re.sub(r"当前源码 (a\d+) 包含", r"本预发行版 \1 包含", content)
    content = re.sub(r"当前源码 (a\d+) 候选在", r"本预发行版 \1 在", content)
    content = content.replace("，尚未公开；Token、素材与订阅", "；Token、素材与订阅")
    content = content.replace(
        "的后台素材服务及可选 bundled 分发", "的后台素材服务及 bundled 随包运行库"
    )
    content = content.replace(
        "，仍未发布；原公开版本不含这些新增安装行为。",
        "；既有 a4 分发不含这些新增安装行为。",
    )
    content = content.replace("bundled 候选随仓库提供", "本随包预发行版随仓库提供")
    content = content.replace(
        "公开a9按冷启动流程更新，本地a10兼容切换边界见上文，真实聊天效果待用户复测。",
        "a9公开运行库更新须冷启动；a10兼容bundled更新可按本地候选步骤重载，真实聊天效果待用户复测。",
    )
    content = content.replace(
        "公开a9的共享库更新须冷启动；本地a10兼容代际更新可受控重载，旧版首次升级仍须冷启动。",
        "公开a9的共享库更新须冷启动；a10兼容代际更新可受控重载，旧版首次升级仍须冷启动。",
    )
    start = "## 丨安装与首次配置"
    end = "## 丨快速开始"
    replacement = (
        f"{start}\n\n"
        "1. 通过 GsCore 的 URL 安装功能添加本分发仓库，然后完整重启宿主。"
        "仓库携带匹配的四个项目运行包，启动时校验并准备插件专用运行目录，"
        "不需要先安装本项目 PyPI 包。\n"
        "2. 用主人身份发送 `do核心状态` 查看准备和加载结果。"
        "缺包或校验失败时发送 `do安装核心`，按提示完成恢复后重载插件。"
        "恢复只使用清单固定版本与 SHA256，不接受聊天 URL、版本或 pip 参数。\n"
        "3. 在后台 **插件配置 → Dota2UID → 插件参数配置** 填写 "
        "STRATZ Token 和独立 `namespace`，点击确认修改。"
        "重载当前插件后读取保存的配置；旧 a6–a9 首次升级本版须完整冷启动。"
        "Token 不发送到聊天。\n\n"
        "`do帮助` / `do菜单` 在运行库未就绪时返回文字提示；配置未完成单独显示。"
        "HTTPX、Pillow 继续使用宿主兼容版本，第三方冲突须按 "
        "[安装指南](../../docs/cookbook/gscore-bundled-install.md)维护。"
        "运行中的安装或修复只准备新运行库，兼容更新通过受控重载启用；"
        "状态分别显示期望、准备、运行版本与摘要。未知消费者、schema/第三方变化或"
        "关闭超时仍需冷启动；已有绑定和配置保留。详细安装、更新与回退见同一指南。\n\n"
        "独立分发目录与 ZIP 由[发行生成器](../../docs/cookbook/plugin-release.md)生成。"
        "这是随包预发行分发；生成器只准备分发文件，生成动作本身不代表公开发布。\n\n"
    )
    pattern = rf"{re.escape(start)}\n.*?(?={re.escape(end)})"
    content, count = re.subn(pattern, lambda _: replacement, content, flags=re.DOTALL)
    if count != 1:
        raise ValueError("Dota2UID README must contain one installation section")
    row = "| `do菜单` / `do帮助` | 查看帮助图片 |"
    content = content.replace(
        row,
        "| `do核心状态` / `do安装核心` | 查看运行库状态 / 主人准备或恢复运行库 |\n" + row,
    )
    return content


def bundled_install_guide(root: Path, source_ref: str = "main") -> bytes:
    """Resolve source-relative guide links before moving the guide to a plugin root."""
    source_url = source_repository_url(source_ref)
    source = root / GS_BUNDLED_INSTALL_GUIDE
    content = source.read_text("utf-8")

    def resolve_link(match: re.Match[str]) -> str:
        target = match[1]
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match[0]
        path = (source.parent / unquote(parsed.path)).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(
                "Bundled installation guide links must stay inside the source repository"
            )
        relative = quote(path.relative_to(root.resolve()).as_posix(), safe="/")
        url = f"{source_url}/{relative}"
        if parsed.query:
            url += "?" + parsed.query
        if parsed.fragment:
            url += "#" + parsed.fragment
        return f"]({url})"

    return re.sub(r"]\(([^)\s]+)\)", resolve_link, content).encode("utf-8")


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


def public_wheel_requirements(wheels: Path, pinned: dict[str, str], repo: str) -> list[str]:
    """Return hash-pinned GitHub Release references for a public AstrBot bridge."""
    manifest = json.loads(runtime_wheels(wheels, pinned, repo).decode("utf-8"))
    tag = manifest["release_tag"]
    requirements: list[str] = []
    for name in sorted(pinned):
        wheel = manifest["wheels"][name]
        extra = "[stratz]" if name not in {"dota2forge-renderer", "dota2forge-assets"} else ""
        url = f"{repo}/releases/download/{tag}/{wheel['filename']}#sha256={wheel['sha256']}"
        requirements.append(f"{name}{extra} @ {url}")
    return requirements


def bundled_runtime_files(wheels: Path, pinned: dict[str, str], repo: str) -> dict[str, bytes]:
    """Carry only validated project wheels; never bundle host or game dependencies."""
    from scripts.gscore_bundled_runtime import MAX_WHEEL_BYTES, validate_wheel

    content: dict[str, bytes] = {}
    wheel_entries: dict[str, dict[str, str]] = {}
    present: set[str] = set()
    for name, version in sorted(pinned.items()):
        filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        path = wheels / filename
        if path.is_symlink() or path.stat().st_size > MAX_WHEEL_BYTES:
            raise ValueError("Bundled runtime wheel input is unsafe or too large")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files = validate_wheel(path, name, version, digest)
        if present.intersection(files):
            raise ValueError("Bundled runtime wheels contain colliding files")
        present.update(files)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Bundled runtime wheel changed during validation")
        wheel_entries[name] = {"filename": filename, "sha256": digest}
        content[f"runtime-wheels/{filename}"] = data
    manifest = json_bytes(
        {
            "schema_version": 1,
            "repository": repo,
            "release_tag": f"v{pinned['dota2uid']}",
            "wheels": wheel_entries,
        }
    )
    content["runtime-wheels.json"] = manifest
    content["deployment.json"] = json_bytes(
        {
            "schema_version": 1,
            "mode": "bundled",
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        }
    )
    return content


def distribution_files(
    root: Path,
    astrbot_repo: str,
    gscore_repo: str,
    gscore_wheels: Path | None = None,
    astrbot_wheels: Path | None = None,
    gscore_bundled: bool = False,
    source_ref: str = "main",
) -> dict[str, bytes]:
    source_repository_url(source_ref)
    astrbot_repo, author = repository(astrbot_repo, "astrbot_plugin_dota2forge")
    gscore_repo, gs_author = repository(gscore_repo, "Dota2UID")
    if gscore_bundled and gscore_wheels is None:
        raise ValueError("Bundled GsCore distributions require --gscore-wheels")
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
            for name in ("dota2forge-core", "dota2forge-renderer", "dota2forge-assets", adapter)
        }
        requirements = [
            f"{name}{'[stratz]' if name in STRATZ_PACKAGES else ''}=={version}"
            for name, version in sorted(pinned.items())
        ]
        repo = astrbot_repo if plugin.startswith("astrbot") else gscore_repo
        public_wheels = astrbot_wheels if plugin.startswith("astrbot") else gscore_wheels
        bundled = plugin == "Dota2UID" and gscore_bundled
        dependencies = requirements + third_party
        if public_wheels is not None and plugin.startswith("astrbot"):
            dependencies = public_wheel_requirements(public_wheels, pinned, repo) + third_party
        content = {
            "LICENSE": license_text,
            "README.md": readme(
                root,
                plugin,
                repo,
                release_versions[adapter],
                public_runtime=public_wheels is not None,
                gscore_bundled=bundled,
                source_ref=source_ref,
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
                "version": astrbot_version(release_versions[adapter]),
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
            host_source = "bundled_host_entry.py.template" if bundled else "host_entry.py.template"
            entry = text_bytes(root / GS_ADAPTER_SOURCE / host_source)
            if not bundled:
                entry = PRELUDE.encode() + entry
            gs_dependencies = third_party if bundled else dependencies
            auto_update = (
                "" if bundled else f"gscore_auto_update_dep = {json.dumps(requirements)}\n"
            )
            content.update(
                {
                    "__init__.py": entry,
                    "_dota2forge_config.py": text_bytes(
                        root / GS_ADAPTER_SOURCE / "host_config.py.template"
                    ),
                    "config.example.toml": text_bytes(
                        root / "adapters/Dota2UID/config.example.toml"
                    ),
                    "pyproject.toml": (
                        '[project]\nname = "dota2uid-host-entry"\n'
                        f'version = "{release_versions[adapter]}"\nrequires-python = ">=3.12"\n'
                        f"dependencies = {json.dumps(gs_dependencies)}\n"
                        f"{auto_update}"
                    ).encode(),
                }
            )
            if bundled:
                content.update(
                    {
                        "_dota2forge_business.py": text_bytes(
                            root / GS_ADAPTER_SOURCE / "bundled_business_entry.py.template"
                        ),
                        "_dota2forge_runtime.py": text_bytes(root / GS_BUNDLED_RUNTIME_SOURCE),
                    }
                )
                # The early guard is specific to the thin entry; bundled bootstrap owns validation.
                del content["_dota2forge_bootstrap.py"]
        if public_wheels is not None:
            if bundled:
                content.update(bundled_runtime_files(public_wheels, pinned, repo))
                deployment = json.loads(content["deployment.json"])
                deployment["hot_reload"] = {
                    "protocol": 1,
                    "contract": "dota2forge-storage-1-3-report-2",
                    "business_sha256": hashlib.sha256(
                        content["_dota2forge_business.py"]
                    ).hexdigest(),
                }
                content["deployment.json"] = json_bytes(deployment)
            else:
                content["install_runtime.py"] = text_bytes(root / GS_RUNTIME_SOURCE)
                content["runtime-wheels.json"] = runtime_wheels(public_wheels, pinned, repo)
            guide = (
                ASTR_INSTALL_GUIDE
                if plugin.startswith("astrbot")
                else GS_BUNDLED_INSTALL_GUIDE
                if bundled
                else GS_INSTALL_GUIDE
            )
            content["INSTALL.md"] = (
                bundled_install_guide(root, source_ref) if bundled else text_bytes(root / guide)
            )
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
                        "URL 安装后请完整重启 GsCore，运行库随插件提供。主人可发送 "
                        "do核心状态 检查；需要恢复时发送 do安装核心，完成后按提示冷启动。"
                        "再在后台插件配置 → Dota2UID 填 STRATZ Token 和 namespace，确认修改后"
                        " do停用，再重载当前插件；第三方依赖冲突见 INSTALL.md。"
                        if gscore_bundled
                        else "第一次安装请先看插件里的 INSTALL.md：关闭 GsCore，用它的 Python "
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
        if gscore_bundled:
            sources.append(root / GS_BUNDLED_RUNTIME_SOURCE)
        else:
            sources.append(root / GS_RUNTIME_SOURCE)
        sources.append(root / (GS_BUNDLED_INSTALL_GUIDE if gscore_bundled else GS_INSTALL_GUIDE))
        for name in ("dota2forge-core", "dota2forge-renderer", "dota2forge-assets", "dota2uid"):
            path = (
                gscore_wheels
                / f"{name.replace('-', '_')}-{release_versions[name]}-py3-none-any.whl"
            )
            sources.append(path)
    if astrbot_wheels is not None:
        sources.extend((root / GS_RUNTIME_SOURCE, root / ASTR_INSTALL_GUIDE))
        for name in (
            "dota2forge-core",
            "dota2forge-renderer",
            "dota2forge-assets",
            "astrbot-plugin-dota2forge",
        ):
            sources.append(
                astrbot_wheels
                / f"{name.replace('-', '_')}-{release_versions[name]}-py3-none-any.whl"
            )
    artifacts["manifest.json"] = json_bytes(
        {
            "schema_version": 1,
            "status": "local_candidate",
            **({"source_ref": source_ref} if source_ref != "main" else {}),
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
    gscore_bundled: bool = False,
    source_ref: str = "main",
) -> Path:
    root, output = root.resolve(), output.absolute()
    if root.is_relative_to(output.resolve()):
        raise ValueError("Output must not replace or contain the source repository")
    artifacts = distribution_files(
        root, astrbot_repo, gscore_repo, gscore_wheels, astrbot_wheels, gscore_bundled, source_ref
    )
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
    parser.add_argument(
        "--gscore-bundled",
        action="store_true",
        help="Bundle validated GsCore project wheels and a dependency-free management entry",
    )
    parser.add_argument(
        "--source-ref",
        default="main",
        help="Pin source links to main or a full lowercase commit SHA",
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
            args.gscore_bundled,
            args.source_ref,
        )
    except (OSError, ValueError, KeyError, BadZipFile):
        print("Distribution generation failed. Check source metadata, repository URLs and output.")
        return 1
    print(
        f"Local plugin candidates generated: {destination}. No packages or stores were published."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

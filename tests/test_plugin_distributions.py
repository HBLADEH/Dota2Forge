"""Offline distribution contracts; these do not certify real store installation."""

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile

import pytest

from scripts import build_plugin_distributions as distribution
from scripts import plugin_bootstrap
from scripts import smoke_plugin_distributions as smoke

ROOT = Path(__file__).resolve().parents[1]
ASTR_REPO = "https://github.com/HBLADEH/astrbot_plugin_dota2forge"
GS_REPO = "https://github.com/HBLADEH/Dota2UID"


@pytest.fixture
def candidate(tmp_path):
    return distribution.build_distributions(ROOT, tmp_path / "candidate", ASTR_REPO, GS_REPO)


def test_both_roots_have_pinned_dependencies_license_and_reproducible_archives(candidate, tmp_path):
    second = distribution.build_distributions(ROOT, tmp_path / "second", ASTR_REPO, GS_REPO)
    assert distribution.build_distributions(ROOT, candidate, ASTR_REPO, GS_REPO) == candidate
    for plugin, entry in (("Dota2UID", "__init__.py"), ("astrbot_plugin_dota2forge", "main.py")):
        release = json.loads((candidate / plugin / "release.json").read_text("utf-8"))
        assert release["plugin"] == plugin and len(release["versions"]) == 4
        assert release["versions"] == {
            "dota2forge-core": "0.1.0a6",
            "dota2forge-renderer": "0.1.0a5",
            "dota2forge-assets": "0.1.0a1",
            (
                "astrbot-plugin-dota2forge" if plugin.startswith("astrbot") else "dota2uid"
            ): "0.1.0a9",
        }
        compile((candidate / plugin / entry).read_text("utf-8"), entry, "exec")
        assert (candidate / plugin / "LICENSE").read_text("utf-8") == (ROOT / "LICENSE").read_text(
            "utf-8"
        )
        packed = candidate / f"{plugin}.zip"
        assert packed.read_bytes() == (second / packed.name).read_bytes()
        assert packed.stat().st_size < distribution.MAX_ASTRBOT_ZIP_BYTES
        with ZipFile(packed) as archive:
            assert "release.json" in archive.namelist() and entry in archive.namelist()
            assert not any(
                ".env" in name or ".git" in name or "assets/" in name for name in archive.namelist()
            )
            assert archive.read(entry) == (candidate / plugin / entry).read_bytes()
    gs = tomllib.loads((candidate / "Dota2UID/pyproject.toml").read_text("utf-8"))
    assert gs["project"]["gscore_auto_update_dep"] == [
        "dota2forge-assets==0.1.0a1",
        "dota2forge-core[stratz]==0.1.0a6",
        "dota2forge-renderer==0.1.0a5",
        "dota2uid[stratz]==0.1.0a9",
    ]
    assert "workspace" not in (candidate / "Dota2UID/pyproject.toml").read_text("utf-8")
    helper = candidate / "Dota2UID/_dota2forge_config.py"
    compile(helper.read_text("utf-8"), str(helper), "exec")
    assert (
        helper.read_bytes()
        == (ROOT / "adapters/Dota2UID/src/Dota2UID/host_config.py.template")
        .read_text("utf-8")
        .replace("\r\n", "\n")
        .encode()
    )
    astr = (candidate / "astrbot_plugin_dota2forge/metadata.yaml").read_text("utf-8")
    assert f"repo: {ASTR_REPO}" in astr and 'astrbot_version: ">=4.5.0"' in astr
    requirements = (candidate / "astrbot_plugin_dota2forge/requirements.txt").read_text("utf-8")
    assert "astrbot-plugin-dota2forge[stratz]==0.1.0a9" in requirements
    assert "dota2forge-core[stratz]==0.1.0a6" in requirements
    manifest = json.loads((candidate / "manifest.json").read_text("utf-8"))
    assert manifest["status"] == "local_candidate"
    for name, digest in manifest["files_sha256"].items():
        assert hashlib.sha256((candidate / name).read_bytes()).hexdigest() == digest
    index = json.loads((candidate / "gscore-index-entry.json").read_text("utf-8"))
    assert index["plugins"]["Dota2UID"]["link"] == GS_REPO
    assert index["tool_plugins"] == ["Dota2UID"]


@pytest.mark.parametrize("change", ["edit", "extra", "missing"])
def test_rebuild_refuses_to_overwrite_changed_or_partial_artifacts(candidate, change):
    target = candidate / "Dota2UID/README.md"
    if change == "edit":
        target.write_text("user edit", encoding="utf-8")
    elif change == "extra":
        (candidate / "keep.txt").write_text("user file", encoding="utf-8")
    else:
        target.unlink()
    before = {p.relative_to(candidate): p.read_bytes() for p in candidate.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="Existing distribution differs"):
        distribution.build_distributions(ROOT, candidate, ASTR_REPO, GS_REPO)
    assert before == {
        p.relative_to(candidate): p.read_bytes() for p in candidate.rglob("*") if p.is_file()
    }


def test_output_cannot_be_repository_or_parent():
    for target in (ROOT, ROOT.parent):
        with pytest.raises(ValueError, match="source repository"):
            distribution.build_distributions(ROOT, target, ASTR_REPO, GS_REPO)


@pytest.mark.parametrize(
    "repo",
    [
        "http://github.com/HBLADEH/Dota2UID",
        "https://gitlab.com/HBLADEH/Dota2UID",
        "https://github.com/HBLADEH/Dota2Forge/tree/main/adapters/Dota2UID",
        "https://github.com/HBLADEH/Dota2UID.git",
    ],
)
def test_repository_must_match_the_host_distribution_name(repo):
    with pytest.raises(ValueError, match="HTTPS GitHub"):
        distribution.repository(repo, "Dota2UID")


@pytest.mark.parametrize(
    "field,value",
    [("name", "wrong"), ("version", ""), ("version", 1), ("requires-python", ">=3.10")],
)
def test_invalid_package_metadata_is_rejected_before_output(tmp_path, field, value):
    for name, folder in distribution.PACKAGES.items():
        target = tmp_path / folder / "pyproject.toml"
        target.parent.mkdir(parents=True)
        project = {"name": name, "version": "0.1.0a4", "requires-python": ">=3.12"}
        project[field] = value
        target.write_text(
            "[project]\n" + "\n".join(f"{k} = {json.dumps(v)}" for k, v in project.items()),
            encoding="utf-8",
        )
    with pytest.raises(ValueError):
        distribution.versions(tmp_path)


def test_oversize_archive_fails_before_output(tmp_path, monkeypatch):
    monkeypatch.setattr(distribution, "MAX_ASTRBOT_ZIP_BYTES", 1)
    target = tmp_path / "candidate"
    with pytest.raises(ValueError, match="16 MB"):
        distribution.build_distributions(ROOT, target, ASTR_REPO, GS_REPO)
    assert not target.exists()


def test_cli_has_success_and_non_destructive_failure(tmp_path, capsys):
    target = tmp_path / "candidate"
    args = ["--output", str(target), "--astrbot-repo", ASTR_REPO, "--gscore-repo", GS_REPO]
    assert distribution.main(args) == 0
    assert "No packages or stores were published" in capsys.readouterr().out
    (target / "keep.txt").write_text("keep", encoding="utf-8")
    assert distribution.main(args) == 1
    assert (target / "keep.txt").read_text("utf-8") == "keep"


def test_bootstrap_matches_versions_and_rejects_missing_or_older_libraries(candidate, monkeypatch):
    entry = str(candidate / "Dota2UID/__init__.py")
    monkeypatch.setattr(
        plugin_bootstrap.metadata, "version", lambda name: distribution.versions(ROOT)[name]
    )
    plugin_bootstrap.verify_dependencies(entry)
    monkeypatch.setattr(plugin_bootstrap.metadata, "version", lambda name: "0.1.0a1")
    with pytest.raises(RuntimeError, match="missing or incompatible"):
        plugin_bootstrap.verify_dependencies(entry)

    def missing(name):
        raise plugin_bootstrap.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(plugin_bootstrap.metadata, "version", missing)
    with pytest.raises(RuntimeError, match="dota2uid"):
        plugin_bootstrap.verify_dependencies(entry)


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {},
        {"schema_version": True},
        {"schema_version": 2},
        {"schema_version": 1, "plugin": "wrong"},
        {"schema_version": 1, "plugin": "Dota2UID", "versions": []},
        {
            "schema_version": 1,
            "plugin": "Dota2UID",
            "versions": {"dota2forge-core": "", "dota2forge-renderer": "1", "dota2uid": "1"},
        },
    ],
)
def test_manifest_missing_or_invalid_fails_closed(tmp_path, data):
    if data is not None:
        (tmp_path / "release.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest is missing or invalid"):
        plugin_bootstrap.verify_dependencies(str(tmp_path / "__init__.py"))


def test_old_python_is_rejected_before_manifest_io(tmp_path, monkeypatch):
    monkeypatch.setattr(plugin_bootstrap.sys, "version_info", (3, 11, 0))
    with pytest.raises(RuntimeError, match="Python 3.12"):
        plugin_bootstrap.verify_dependencies(str(tmp_path / "__init__.py"))
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "plugin,entry", [("Dota2UID", "__init__.py"), ("astrbot_plugin_dota2forge", "main.py")]
)
def test_generated_entry_checks_versions_before_sdk_imports(candidate, plugin, entry, monkeypatch):
    monkeypatch.setattr(plugin_bootstrap.metadata, "version", lambda name: "0.1.0a1")
    name = f"synthetic_release_{plugin}"
    spec = importlib.util.spec_from_file_location(
        name, candidate / plugin / entry, submodule_search_locations=[str(candidate / plugin)]
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    with pytest.raises(RuntimeError, match="missing or incompatible"):
        spec.loader.exec_module(module)
    monkeypatch.delitem(sys.modules, name + "._dota2forge_bootstrap", raising=False)


def test_distribution_smoke_always_uses_fresh_offline_environments(candidate, monkeypatch):
    calls = []
    monkeypatch.setattr(
        smoke.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs))
    )
    smoke.smoke_distributions(candidate, ROOT / "dist")
    installs = [args for args, _ in calls if args[:3] == ["uv", "pip", "install"]]
    assert len(installs) == 2
    assert all(
        "--offline" in args and "--no-index" in args and "--no-cache" in args for args in installs
    )
    checks = [args for args, _ in calls if "-I" in args]
    assert len(checks) == 2 and checks[0][0] != checks[1][0]
    assert all("-B" in args for args in checks)
    assert all(kwargs["check"] for _, kwargs in calls)


def test_smoke_rejects_tampered_artifacts_before_any_execution(candidate, monkeypatch):
    monkeypatch.setattr(
        smoke.subprocess, "run", lambda *args, **kwargs: pytest.fail("no execution")
    )
    (candidate / "Dota2UID/__init__.py").write_text("user change", encoding="utf-8")
    assert smoke.main(["--candidate", str(candidate), "--wheels", str(ROOT / "dist")]) == 1


def test_smoke_command_failure_is_propagated(candidate, monkeypatch):
    def fail(args, **kwargs):
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(smoke.subprocess, "run", fail)
    assert smoke.main(["--candidate", str(candidate), "--wheels", str(ROOT / "dist")]) == 1


def test_third_party_dependency_constraints_come_from_metadata():
    assert distribution.third_party_requirements(ROOT) == ["httpx>=0.28.1,<1", "pillow>=11.3,<13"]


def test_plugin_readmes_and_icons_remain_usable_outside_the_workspace(candidate):
    """The standalone ZIP must resolve its icon/license without the monorepo layout."""
    icon = (ROOT / distribution.ICON_SOURCE).read_bytes()
    assert icon.startswith(b"\x89PNG\r\n\x1a\n")
    for plugin, icon_name, repo in (
        ("Dota2UID", "ICON.png", GS_REPO),
        ("astrbot_plugin_dota2forge", "logo.png", ASTR_REPO),
    ):
        folder = candidate / plugin
        content = (folder / "README.md").read_text("utf-8")
        icon_url = (
            repo.replace("https://github.com/", "https://raw.githubusercontent.com/")
            + f"/main/{icon_name}"
            if plugin.startswith("astrbot")
            else icon_name
        )
        assert f'src="{icon_url}"' in content
        assert "0.1.0a5" in content and repo in content
        assert "待实机截图" in content
        assert ("0.1.0-alpha.9" if plugin.startswith("astrbot") else "尚未上架商店") in content
        assert "<!-- distribution-release -->" not in content
        targets = re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)\)|src="([^"]+)"', content)
        for link, source in targets:
            target = link or source
            if not urlsplit(target).scheme:
                assert (folder / target).is_file(), target
        with ZipFile(candidate / f"{plugin}.zip") as packed:
            assert packed.read(icon_name) == icon == (folder / icon_name).read_bytes()
            assert packed.read("README.md").decode("utf-8") == content
    manifest = json.loads((candidate / "manifest.json").read_text("utf-8"))
    for source in (
        distribution.ICON_SOURCE,
        "adapters/Dota2UID/README.md",
        "adapters/astrbot_plugin_dota2forge/README.md",
    ):
        assert (
            manifest["source_sha256"][source]
            == hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        )
    index = json.loads((candidate / "gscore-index-entry.json").read_text("utf-8"))
    entry = index["plugins"]["Dota2UID"]
    assert (
        entry["avatar"]
        == entry["cover"]
        == ("https://raw.githubusercontent.com/HBLADEH/Dota2UID/main/ICON.png")
    )


def test_readme_uses_requested_release_identity_and_requires_one_marker(tmp_path):
    repo = "https://github.com/example/Dota2UID"
    content = distribution.readme(ROOT, "Dota2UID", repo, "0.2.0").decode("utf-8")
    assert f"[目标分发仓库]({repo})" in content and "`0.2.0`" in content
    target = tmp_path / "adapters/Dota2UID/README.md"
    target.parent.mkdir(parents=True)
    for value in ("no marker", "<!-- distribution-release -->" * 2):
        target.write_text(value, encoding="utf-8")
        with pytest.raises(ValueError, match="one distribution release marker"):
            distribution.readme(tmp_path, "Dota2UID", repo, "0.2.0")


@pytest.mark.parametrize(
    "plugin,caption",
    [
        ("astrbot_plugin_dota2forge", "AstrBot 主宰热门出装实机卡片"),
        ("Dota2UID", "主宰热门出装共享卡片（来自 AstrBot）"),
    ],
)
def test_reviewed_screenshot_is_local_in_zip_and_covered_by_both_digests(
    candidate, plugin, caption
):
    """A standalone README must retain its image without remote monorepo assets."""
    source = "docs/assets/screenshots/astrbot/hero-items.png"
    target = f"{plugin}/screenshots/hero-items.png"
    original = (ROOT / source).read_bytes()
    content = (candidate / plugin / "README.md").read_text("utf-8")
    image_url = (
        ASTR_REPO.replace("https://github.com/", "https://raw.githubusercontent.com/")
        + "/main/screenshots/hero-items.png"
        if plugin.startswith("astrbot")
        else "screenshots/hero-items.png"
    )
    assert f"![{caption}]({image_url})" in content
    if plugin == "Dota2UID":
        assert "复用此前 AstrBot 实机原图" in content and "不构成 GsCore 聊天收发" in content
    assert (candidate / target).read_bytes() == original
    with ZipFile(candidate / f"{plugin}.zip") as packed:
        assert packed.read("screenshots/hero-items.png") == original
    manifest = json.loads((candidate / "manifest.json").read_text("utf-8"))
    digest = hashlib.sha256(original).hexdigest()
    assert manifest["source_sha256"][source] == digest
    assert manifest["files_sha256"][target] == digest


def test_missing_reviewed_screenshot_fails_before_creating_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(
        distribution,
        "SHOWCASE_IMAGES",
        {"astrbot_plugin_dota2forge": {"missing.png": "missing-reviewed-image.png"}},
    )
    target = tmp_path / "candidate"
    with pytest.raises(FileNotFoundError):
        distribution.build_distributions(ROOT, target, ASTR_REPO, GS_REPO)
    assert not target.exists()


@pytest.mark.parametrize(
    "package,market",
    [
        ("0.1.0a7", "0.1.0-alpha.7"),
        ("1.2.3b2", "1.2.3-beta.2"),
        ("1.2.3rc1", "1.2.3-rc.1"),
        ("1.2.3", "1.2.3"),
    ],
)
def test_market_version_is_semver(package, market):
    assert distribution.astrbot_version(package) == market


def test_market_rejects_unmapped_version():
    with pytest.raises(ValueError):
        distribution.astrbot_version("1.2.3.dev4")

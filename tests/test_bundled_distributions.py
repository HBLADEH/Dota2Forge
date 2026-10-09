"""Offline bundled generation preserves thin and AstrBot distribution contracts."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import shutil
import tomllib
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile

import pytest

from scripts import build_plugin_distributions as distribution
from scripts import gscore_bundled_runtime as bundled_runtime

ROOT = Path(__file__).resolve().parents[1]
ASTR_REPO = "https://github.com/HBLADEH/astrbot_plugin_dota2forge"
GS_REPO = "https://github.com/HBLADEH/Dota2UID"
NAMES = ("dota2forge-assets", "dota2forge-core", "dota2forge-renderer", "dota2uid")


def synthetic_wheel(name, version, extra=None, tag="py3-none-any"):
    package = "Dota2UID" if name == "dota2uid" else name.replace("-", "_")
    dist_info = f"{name.replace('-', '_')}-{version}.dist-info"
    files = {
        f"{package}/__init__.py": b'"""Synthetic offline project package."""\n',
        f"{package}/py.typed": b"",
        f"{dist_info}/METADATA": (
            f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\nRequires-Python: >=3.12\n"
        ).encode(),
        f"{dist_info}/WHEEL": (f"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: {tag}\n").encode(),
        f"{dist_info}/licenses/LICENSE": b"MIT synthetic fixture\n",
    }
    files.update(extra or {})
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for path, data in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow((path, "sha256=" + digest, len(data)))
    writer.writerow((f"{dist_info}/RECORD", "", ""))
    files[f"{dist_info}/RECORD"] = record.getvalue().encode()
    return distribution.archive(files)


@pytest.fixture
def bundled_source(tmp_path):
    root = tmp_path / "source"
    relative_files = [
        "LICENSE",
        "scripts/build_plugin_distributions.py",
        "scripts/plugin_bootstrap.py",
        distribution.GS_RUNTIME_SOURCE,
        distribution.GS_BUNDLED_RUNTIME_SOURCE,
        distribution.GS_INSTALL_GUIDE,
        distribution.GS_BUNDLED_INSTALL_GUIDE,
        distribution.ASTR_INSTALL_GUIDE,
        distribution.ICON_SOURCE,
        "docs/assets/screenshots/astrbot/hero-items.png",
        "adapters/Dota2UID/config.example.toml",
    ]
    for folder in distribution.PACKAGES.values():
        relative_files.append(folder + "/pyproject.toml")
        if folder.startswith("adapters/"):
            relative_files.append(folder + "/README.md")
    relative_files.extend(
        distribution.GS_ADAPTER_SOURCE + "/" + name
        for name in (
            "host_entry.py.template",
            "host_config.py.template",
            "bundled_host_entry.py.template",
            "bundled_business_entry.py.template",
        )
    )
    host = "adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host/"
    relative_files.extend(
        host + name for name in ("main.py.template", "metadata.yaml", "_conf_schema.json")
    )
    for relative in relative_files:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    wheels = root / "wheels"
    wheels.mkdir()
    pinned = distribution.versions(root)
    for name in (*NAMES, "astrbot-plugin-dota2forge"):
        filename = f"{name.replace('-', '_')}-{pinned[name]}-py3-none-any.whl"
        (wheels / filename).write_bytes(synthetic_wheel(name, pinned[name]))
    # Extra staged host dependencies must never enter the bundled ZIP.
    (wheels / "pillow-12.0-cp312-cp312-win_amd64.whl").write_bytes(b"native host fixture")
    return root, wheels


def build_bundle(root, wheels, destination):
    return distribution.build_distributions(
        root, destination, ASTR_REPO, GS_REPO, wheels, wheels, gscore_bundled=True
    )


def test_bundle_carries_only_validated_project_wheels_and_stdlib_bootstrap(
    bundled_source, tmp_path
):
    root, wheels = bundled_source
    output = build_bundle(root, wheels, tmp_path / "candidate")
    plugin = output / "Dota2UID"
    project = tomllib.loads((plugin / "pyproject.toml").read_text("utf-8"))["project"]
    assert project["dependencies"] == distribution.third_party_requirements(root)
    assert "gscore_auto_update_dep" not in project
    assert not (plugin / "_dota2forge_bootstrap.py").exists()
    assert not (plugin / "install_runtime.py").exists()
    assert "下述公开安装流程仍适用于现有 a4" not in (plugin / "README.md").read_text("utf-8")
    assert (plugin / "__init__.py").read_bytes() == distribution.text_bytes(
        root / distribution.GS_ADAPTER_SOURCE / "bundled_host_entry.py.template"
    )
    for name in (
        "__init__.py",
        "_dota2forge_business.py",
        "_dota2forge_runtime.py",
        "_dota2forge_config.py",
    ):
        compile((plugin / name).read_text("utf-8"), name, "exec")
    assert (plugin / "_dota2forge_runtime.py").read_bytes() == distribution.text_bytes(
        root / distribution.GS_BUNDLED_RUNTIME_SOURCE
    )
    manifest_data = (plugin / "runtime-wheels.json").read_bytes()
    manifest = json.loads(manifest_data)
    release = json.loads((plugin / "release.json").read_text("utf-8"))
    assert set(manifest["wheels"]) == set(release["versions"]) == set(NAMES)
    assert manifest["repository"] == GS_REPO
    assert manifest["release_tag"] == "v" + distribution.versions(root)["dota2uid"]
    assert json.loads((plugin / "deployment.json").read_text("utf-8")) == {
        "schema_version": 1,
        "mode": "bundled",
        "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
    }
    filenames = {wheel["filename"] for wheel in manifest["wheels"].values()}
    assert {p.name for p in (plugin / "runtime-wheels").iterdir()} == filenames
    with ZipFile(output / "Dota2UID.zip") as packed:
        packed_names = {name for name in packed.namelist() if name.startswith("runtime-wheels/")}
        assert packed_names == {"runtime-wheels/" + name for name in filenames}
        for name in filenames:
            data = (wheels / name).read_bytes()
            assert packed.read("runtime-wheels/" + name) == data
            assert (plugin / "runtime-wheels" / name).read_bytes() == data
    ledger = json.loads((output / "manifest.json").read_text("utf-8"))
    for source in (distribution.GS_BUNDLED_RUNTIME_SOURCE, distribution.GS_BUNDLED_INSTALL_GUIDE):
        assert (
            ledger["source_sha256"][source]
            == hashlib.sha256((root / source).read_bytes()).hexdigest()
        )
    for name in filenames:
        digest = hashlib.sha256((wheels / name).read_bytes()).hexdigest()
        assert ledger["source_sha256"]["wheels/" + name] == digest
        assert ledger["files_sha256"]["Dota2UID/runtime-wheels/" + name] == digest


def test_bundle_is_deterministic_keeps_astrbot_unchanged_and_uses_its_install_guide(
    bundled_source, tmp_path
):
    root, wheels = bundled_source
    bundle = build_bundle(root, wheels, tmp_path / "bundled")
    second = build_bundle(root, wheels, tmp_path / "second")
    assert build_bundle(root, wheels, bundle) == bundle
    assert (bundle / "Dota2UID.zip").read_bytes() == (second / "Dota2UID.zip").read_bytes()
    thin = distribution.build_distributions(
        root, tmp_path / "thin", ASTR_REPO, GS_REPO, wheels, wheels
    )
    assert (bundle / "astrbot_plugin_dota2forge.zip").read_bytes() == (
        thin / "astrbot_plugin_dota2forge.zip"
    ).read_bytes()
    assert (bundle / "Dota2UID/INSTALL.md").read_bytes() == distribution.bundled_install_guide(root)
    assert (thin / "Dota2UID/INSTALL.md").read_bytes() == distribution.text_bytes(
        root / distribution.GS_INSTALL_GUIDE
    )
    readme = (bundle / "Dota2UID/README.md").read_text("utf-8")
    assert "`do核心状态`" in readme and "`do安装核心`" in readme
    assert "install_runtime.py" not in readme
    assert "](INSTALL.md)" in readme
    assert "gscore_auto_update_dep" in (thin / "Dota2UID/pyproject.toml").read_text("utf-8")
    assert not (thin / "Dota2UID/deployment.json").exists()
    entry = json.loads((bundle / "gscore-index-entry.json").read_text("utf-8"))["plugins"][
        "Dota2UID"
    ]
    assert "do安装核心" in entry["installMsg"]
    assert "install_runtime.py" not in entry["installMsg"]


def test_bundled_install_guide_links_use_the_source_repository(bundled_source, tmp_path):
    root, wheels = bundled_source
    output = build_bundle(root, wheels, tmp_path / "candidate")
    guide = (output / "Dota2UID/INSTALL.md").read_text("utf-8")
    targets = re.findall(r"]\(([^)\s]+)\)", guide)
    assert targets
    assert all(urlsplit(target).scheme == "https" for target in targets)
    assert f"]({distribution.PROJECT_SOURCE_URL}/docs/cookbook/gscore-public-install.md)" in guide
    assert f"]({distribution.PROJECT_SOURCE_URL}/adapters/Dota2UID/README.md)" in guide
    release_url = "https://github.com/HBLADEH/Dota2UID/releases"
    assert f"[Dota2UID Releases]({release_url})" in guide
    assert {
        target for target in targets if not target.startswith(distribution.PROJECT_SOURCE_URL + "/")
    } == {release_url}
    source = (root / distribution.GS_BUNDLED_INSTALL_GUIDE).read_text("utf-8")
    assert "[旧安装流程](gscore-public-install.md)" in source
    with ZipFile(output / "Dota2UID.zip") as packed:
        assert packed.read("INSTALL.md").decode() == guide


def test_bundled_install_guide_keeps_remote_and_anchor_links_and_rejects_escape(tmp_path):
    guide = tmp_path / distribution.GS_BUNDLED_INSTALL_GUIDE
    guide.parent.mkdir(parents=True)
    guide.write_text(
        "[Remote](https://example.org/guide) [Anchor](#setup) "
        "[Local](../../adapters/Dota2UID/README.md#setup)\n",
        "utf-8",
    )
    converted = distribution.bundled_install_guide(tmp_path).decode()
    assert "[Remote](https://example.org/guide) [Anchor](#setup)" in converted
    assert (
        f"[Local]({distribution.PROJECT_SOURCE_URL}/adapters/Dota2UID/README.md#setup)" in converted
    )
    for target in ("../../../outside.md", "%2e%2e/%2e%2e/%2e%2e/outside.md"):
        guide.write_text(f"[Outside]({target})", "utf-8")
        with pytest.raises(ValueError, match="inside the source repository"):
            distribution.bundled_install_guide(tmp_path)


@pytest.mark.parametrize("source_ref", ["main", "0123456789abcdef0123456789abcdef01234567"])
def test_bundled_readme_preserves_source_references_and_local_installation_links(
    bundled_source, source_ref
):
    root, _ = bundled_source
    readme = distribution.readme(
        root,
        "Dota2UID",
        GS_REPO,
        distribution.versions(root)["dota2uid"],
        public_runtime=True,
        gscore_bundled=True,
        source_ref=source_ref,
    ).decode()
    source_url = f"https://github.com/HBLADEH/Dota2Forge/blob/{source_ref}"
    for label, path in (
        ("截图清单", "docs/cookbook/plugin-showcase.md"),
        ("部署证据", ".agents/artifacts/gscore-current-deployment-v1/README.md"),
        ("发行生成器", "docs/cookbook/plugin-release.md"),
        ("来源与范围", "docs/assets/screenshots/README.md"),
        ("素材说明", "docs/cookbook/illustrations.md"),
    ):
        assert f"[{label}]({source_url}/{path})" in readme
        assert f"[{label}](INSTALL.md)" not in readme
    for label in ("安装文档", "随包安装指南", "安装指南", "生命周期步骤"):
        assert f"[{label}](INSTALL.md)" in readme
    assert "[MIT](LICENSE)" in readme
    assert "](../../" not in readme


def test_source_commit_pins_readmes_and_bundled_guide_without_changing_runtime(
    bundled_source, tmp_path, monkeypatch
):
    root, wheels = bundled_source
    source_ref = "0123456789abcdef0123456789abcdef01234567"
    monkeypatch.setattr(distribution, "ROOT", root)
    pinned = tmp_path / "pinned"
    assert (
        distribution.main(
            [
                "--output",
                str(pinned),
                "--astrbot-repo",
                ASTR_REPO,
                "--gscore-repo",
                GS_REPO,
                "--gscore-wheels",
                str(wheels),
                "--astrbot-wheels",
                str(wheels),
                "--gscore-bundled",
                "--source-ref",
                source_ref,
            ]
        )
        == 0
    )
    source_url = f"https://github.com/HBLADEH/Dota2Forge/blob/{source_ref}"
    for plugin in ("Dota2UID", "astrbot_plugin_dota2forge"):
        readme = (pinned / plugin / "README.md").read_text("utf-8")
        assert f"]({source_url}/README.md)" in readme
        assert distribution.PROJECT_SOURCE_URL not in readme
    guide = (pinned / "Dota2UID/INSTALL.md").read_text("utf-8")
    assert f"]({source_url}/adapters/Dota2UID/README.md)" in guide
    assert f"]({source_url}/docs/cookbook/gscore-public-install.md)" in guide
    assert distribution.PROJECT_SOURCE_URL not in guide
    pinned_manifest = json.loads((pinned / "manifest.json").read_text("utf-8"))
    assert pinned_manifest["source_ref"] == source_ref
    default = distribution.distribution_files(root, ASTR_REPO, GS_REPO, wheels, wheels, True)
    explicit_main = distribution.distribution_files(
        root, ASTR_REPO, GS_REPO, wheels, wheels, True, source_ref="main"
    )
    assert default == explicit_main
    assert "source_ref" not in json.loads(default["manifest.json"])
    for plugin in ("Dota2UID", "astrbot_plugin_dota2forge"):
        for name in ("release.json", "runtime-wheels.json"):
            assert (pinned / plugin / name).read_bytes() == default[f"{plugin}/{name}"]
    for path in (pinned / "Dota2UID/runtime-wheels").iterdir():
        assert path.read_bytes() == default[f"Dota2UID/runtime-wheels/{path.name}"]
    assert (pinned / "Dota2UID/pyproject.toml").read_bytes() == default["Dota2UID/pyproject.toml"]
    assert (pinned / "astrbot_plugin_dota2forge/requirements.txt").read_bytes() == default[
        "astrbot_plugin_dota2forge/requirements.txt"
    ]


@pytest.mark.parametrize("source_ref", ["latest", "main/path", "a" * 39, "a" * 41, "A" * 40])
def test_source_reference_rejects_arbitrary_branches_and_unsafe_refs_before_output(
    bundled_source, tmp_path, monkeypatch, source_ref
):
    root, wheels = bundled_source
    monkeypatch.setattr(distribution, "ROOT", root)
    output = tmp_path / "candidate"
    with pytest.raises(ValueError, match="main or a full lowercase commit SHA"):
        distribution.build_distributions(
            root, output, ASTR_REPO, GS_REPO, wheels, wheels, True, source_ref=source_ref
        )
    assert not output.exists()
    with pytest.raises(ValueError):
        distribution.bundled_install_guide(root, source_ref)
    with pytest.raises(ValueError):
        distribution.readme(root, "Dota2UID", GS_REPO, "0.1.0a6", source_ref=source_ref)
    assert (
        distribution.main(
            [
                "--output",
                str(output),
                "--astrbot-repo",
                ASTR_REPO,
                "--gscore-repo",
                GS_REPO,
                "--source-ref",
                source_ref,
            ]
        )
        == 1
    )
    assert not output.exists()


def test_bundle_requires_local_wheel_inputs_before_creating_output(tmp_path):
    output = tmp_path / "candidate"
    with pytest.raises(ValueError, match="require --gscore-wheels"):
        distribution.build_distributions(ROOT, output, ASTR_REPO, GS_REPO, gscore_bundled=True)
    assert not output.exists()
    with pytest.raises(ValueError, match="inside the source repository"):
        distribution.build_distributions(
            ROOT, output, ASTR_REPO, GS_REPO, tmp_path / "wheels", gscore_bundled=True
        )
    assert not output.exists()


@pytest.mark.parametrize(
    "extra,tag",
    [
        ({"gsuid_core/__init__.py": b"host SDK"}, "py3-none-any"),
        ({"dota2forge_core/extension.pyd": b"native"}, "py3-none-any"),
        ({"dota2forge_core/hero.png": b"game PNG"}, "py3-none-any"),
        ({}, "cp312-cp312-win_amd64"),
    ],
)
def test_bundle_rejects_sdk_native_assets_and_mislabelled_wheels(
    bundled_source, tmp_path, extra, tag
):
    root, wheels = bundled_source
    version = distribution.versions(root)["dota2forge-core"]
    path = wheels / f"dota2forge_core-{version}-py3-none-any.whl"
    path.write_bytes(synthetic_wheel("dota2forge-core", version, extra, tag))
    output = tmp_path / "candidate"
    with pytest.raises(ValueError):
        build_bundle(root, wheels, output)
    assert not output.exists()


@pytest.mark.parametrize("change", ["missing", "metadata", "corrupt"])
def test_invalid_bundle_does_not_overwrite_existing_candidate(
    bundled_source, tmp_path, change, monkeypatch
):
    root, wheels = bundled_source
    monkeypatch.setattr(distribution, "ROOT", root)
    output = build_bundle(root, wheels, tmp_path / "candidate")
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    version = distribution.versions(root)["dota2uid"]
    path = wheels / f"dota2uid-{version}-py3-none-any.whl"
    if change == "missing":
        path.unlink()
    elif change == "metadata":
        path.write_bytes(synthetic_wheel("dota2uid", "0.0.1"))
    else:
        path.write_bytes(b"corrupt ZIP")
    assert (
        distribution.main(
            [
                "--output",
                str(output),
                "--astrbot-repo",
                ASTR_REPO,
                "--gscore-repo",
                GS_REPO,
                "--gscore-wheels",
                str(wheels),
                "--gscore-bundled",
            ]
        )
        == 1
    )
    assert before == {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    }


def test_bundle_cli_reports_success_and_never_publishes(
    bundled_source, tmp_path, monkeypatch, capsys
):
    root, wheels = bundled_source
    monkeypatch.setattr(distribution, "ROOT", root)
    assert (
        distribution.main(
            [
                "--output",
                str(tmp_path / "candidate"),
                "--astrbot-repo",
                ASTR_REPO,
                "--gscore-repo",
                GS_REPO,
                "--gscore-wheels",
                str(wheels),
                "--gscore-bundled",
            ]
        )
        == 0
    )
    assert "No packages or stores were published" in capsys.readouterr().out


@pytest.mark.parametrize("change", ["oversize", "collision", "changed"])
def test_bundle_validation_fails_before_output_if_inputs_change_or_collide(
    bundled_source, tmp_path, monkeypatch, change
):
    root, wheels = bundled_source
    original = bundled_runtime.validate_wheel
    if change == "oversize":
        monkeypatch.setattr(bundled_runtime, "MAX_WHEEL_BYTES", 1)

        def validate(*args):
            pytest.fail("Oversize wheel must fail before opening ZIP metadata")
    else:

        def validate(path, name, version, digest):
            files = original(path, name, version, digest)
            if change == "collision":
                files["common-marker"] = b"collision"
            else:
                path.write_bytes(path.read_bytes() + b"modified during validation")
            return files

    monkeypatch.setattr(bundled_runtime, "validate_wheel", validate)
    output = tmp_path / "candidate"
    with pytest.raises(ValueError):
        build_bundle(root, wheels, output)
    assert not output.exists()


def test_bundle_readme_requires_an_explicit_installation_section():
    with pytest.raises(ValueError, match="one installation section"):
        distribution.bundled_readme("README with no installation instructions")

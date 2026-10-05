from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import build_plugin_distributions as distribution
from scripts import gscore_public_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("dota2forge-core", "dota2forge-renderer", "dota2uid")
REPO = "https://github.com/HBLADEH/Dota2UID"


@pytest.fixture
def manifests(tmp_path):
    versions = {name: "0.1.0a4" for name in NAMES}
    release = {"schema_version": 1, "plugin": "Dota2UID", "versions": versions}
    wheels = {
        name: {"filename": f"{name.replace('-', '_')}-0.1.0a4-py3-none-any.whl", "sha256": "a" * 64}
        for name in NAMES
    }
    manifest = {
        "schema_version": 1,
        "repository": REPO,
        "release_tag": "v0.1.0a4",
        "wheels": wheels,
    }
    (tmp_path / "release.json").write_text(json.dumps(release), encoding="utf-8")
    (tmp_path / "runtime-wheels.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, release, manifest


def test_requirements_use_exact_public_wheels_hashes_and_extras(manifests):
    root, _, _ = manifests
    requirements = runtime.public_requirements(root)
    assert len(requirements) == 3
    assert all(
        "/releases/download/v0.1.0a4/" in value and value.endswith("#sha256=" + "a" * 64)
        for value in requirements
    )
    assert requirements[0].startswith("dota2forge-core[stratz] @ ")
    assert requirements[1].startswith("dota2forge-renderer @ ")
    assert requirements[2].startswith("dota2uid[stratz] @ ")


@pytest.mark.parametrize(
    "change",
    [
        "boolean_schema",
        "foreign_repository",
        "credentials",
        "wrong_tag",
        "path_traversal",
        "wrong_hash",
        "missing_package",
        "invalid_version",
    ],
)
def test_untrusted_manifests_fail_before_installation(manifests, change):
    root, release, manifest = manifests
    if change == "boolean_schema":
        manifest["schema_version"] = True
    elif change == "foreign_repository":
        manifest["repository"] = "https://example.org/HBLADEH/Dota2UID"
    elif change == "credentials":
        manifest["repository"] = "https://user:secret@github.com/HBLADEH/Dota2UID"
    elif change == "wrong_tag":
        manifest["release_tag"] = "v0.1.0a1"
    elif change == "path_traversal":
        manifest["wheels"]["dota2uid"]["filename"] = "../../other.whl"
    elif change == "wrong_hash":
        manifest["wheels"]["dota2uid"]["sha256"] = "not-a-sha256"
    elif change == "missing_package":
        del manifest["wheels"]["dota2uid"]
    else:
        release["versions"]["dota2uid"] = "../other"
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
    with pytest.raises(ValueError):
        runtime.public_requirements(root)


@pytest.mark.parametrize("pip_present,install_result", [(True, 0), (False, 0), (True, 7)])
def test_target_interpreter_bootstrap_and_pip_failure_propagation(
    monkeypatch, pip_present, install_result
):
    calls = []
    target = Path("host with spaces/python.exe")

    def run(command, **kwargs):
        calls.append(command)
        if "-c" in command:
            output = "[]" if "metadata.distributions()" in command[-1] else "[3, 13]"
            return subprocess.CompletedProcess(command, 0, stdout=output)
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0 if pip_present else 1)
        if "ensurepip" in command:
            return subprocess.CompletedProcess(command, 0)
        return subprocess.CompletedProcess(command, install_result)

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert runtime.install(target, ["verified requirement"]) == install_result
    assert all(command[0] == str(target) for command in calls)
    assert any("ensurepip" in command for command in calls) is not pip_present
    installation = next(command for command in calls if "install" in command)
    assert installation[-1] == "verified requirement" and "--no-cache-dir" in installation
    assert any(command[-1] == "check" for command in calls) is (install_result == 0)


def test_host_pillow_constraint_is_passed_and_dependency_conflict_fails(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "-c" in command:
            output = (
                '["pillow<12.0,>=11.0.0"]'
                if "metadata.distributions()" in command[-1]
                else "[3, 13]"
            )
            return subprocess.CompletedProcess(command, 0, stdout=output)
        if "install" in command:
            constraint_file = Path(command[command.index("--constraint") + 1])
            assert constraint_file.read_text("utf-8") == "pillow<12.0,>=11.0.0\n"
        return subprocess.CompletedProcess(command, 1 if command[-1] == "check" else 0)

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert runtime.install(Path("python"), ["requirement"]) == 1
    assert calls[-1][-1] == "check"


@pytest.mark.parametrize("output", ["{}", '["pillow @ https://private.invalid/x"]', "[3]"])
def test_invalid_host_constraints_fail_before_pip_install(monkeypatch, output):
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout=output),
    )
    with pytest.raises(ValueError, match="host Pillow"):
        runtime.pillow_constraints(Path("python"))


def test_python_baseline_failure_never_installs(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="[3, 11]")

    monkeypatch.setattr(runtime.subprocess, "run", run)
    with pytest.raises(ValueError, match="Python 3.12"):
        runtime.install(Path("python"), ["requirement"])
    assert len(calls) == 1


def test_bootstrap_failure_does_not_attempt_runtime_install(monkeypatch):
    def run(command, **kwargs):
        if "-c" in command:
            return subprocess.CompletedProcess(command, 0, stdout="[3, 12]")
        return subprocess.CompletedProcess(command, 9)

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert runtime.install(Path("python"), ["requirement"]) == 9


def test_cli_only_reports_success_after_installation(manifests, monkeypatch, capsys):
    root, _, _ = manifests
    monkeypatch.setattr(runtime, "__file__", str(root / "install_runtime.py"))
    monkeypatch.setattr(runtime, "install", lambda target, requirements: 0)
    assert runtime.main(["--host-python", "python"]) == 0
    assert "Cold-start" in capsys.readouterr().out
    monkeypatch.setattr(runtime, "install", lambda target, requirements: 7)
    assert runtime.main(["--host-python", "python"]) == 7
    assert "installed" not in capsys.readouterr().out
    (root / "runtime-wheels.json").write_text("{}", encoding="utf-8")
    assert runtime.main(["--host-python", "python"]) == 1


def write_wheels(directory: Path, *, wrong_version: bool = False):
    directory.mkdir()
    for name in (*NAMES, "astrbot-plugin-dota2forge"):
        filename = f"{name.replace('-', '_')}-0.1.0a4-py3-none-any.whl"
        version = "0.1.0a1" if wrong_version else "0.1.0a4"
        with ZipFile(directory / filename, "w") as wheel:
            wheel.writestr(
                f"{name.replace('-', '_')}-0.1.0a4.dist-info/METADATA",
                f"Name: {name}\nVersion: {version}\nRequires-Python: >=3.12\n",
            )


def test_wheel_metadata_mismatch_is_rejected(tmp_path):
    wheels = tmp_path / "wheels"
    write_wheels(wheels, wrong_version=True)
    with pytest.raises(ValueError, match="metadata"):
        distribution.runtime_wheels(wheels, {name: "0.1.0a4" for name in NAMES}, REPO)


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_public_generation_keeps_operator_links_local_and_hashes_wheels(tmp_path, line_ending):
    root = tmp_path / "source"
    relative_files = [
        "LICENSE",
        "scripts/build_plugin_distributions.py",
        "scripts/plugin_bootstrap.py",
        distribution.GS_RUNTIME_SOURCE,
        distribution.GS_INSTALL_GUIDE,
        distribution.ASTR_INSTALL_GUIDE,
        distribution.ICON_SOURCE,
        "docs/assets/screenshots/astrbot/hero-items.png",
        "adapters/Dota2UID/config.example.toml",
        "adapters/Dota2UID/src/Dota2UID/host_entry.py.template",
    ]
    for folder in distribution.PACKAGES.values():
        relative_files.append(folder + "/pyproject.toml")
        if folder.startswith("adapters/"):
            relative_files.append(folder + "/README.md")
    host = "adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host/"
    relative_files.extend(
        host + name for name in ("main.py.template", "metadata.yaml", "_conf_schema.json")
    )
    for relative in relative_files:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    guide = root / distribution.GS_INSTALL_GUIDE
    guide_text = guide.read_text("utf-8")
    guide.write_bytes(guide_text.replace("\n", line_ending).encode("utf-8"))
    wheels = root / "wheels"
    write_wheels(wheels)
    candidate = distribution.build_distributions(
        root,
        tmp_path / "candidate",
        "https://github.com/HBLADEH/astrbot_plugin_dota2forge",
        REPO,
        wheels,
        wheels,
    )
    plugin = candidate / "Dota2UID"
    # Distribution text is deterministically UTF-8/LF on Windows and Unix checkouts.
    assert (plugin / "INSTALL.md").read_bytes() == guide_text.encode("utf-8")
    readme = (plugin / "README.md").read_text("utf-8")
    assert "](INSTALL.md)" in readme and "/blob/main/docs/" not in readme
    assert "install_runtime.py" in readme
    assert len(runtime.public_requirements(plugin)) == 3
    manifest = json.loads((plugin / "runtime-wheels.json").read_text("utf-8"))
    for wheel in manifest["wheels"].values():
        assert (
            wheel["sha256"] == hashlib.sha256((wheels / wheel["filename"]).read_bytes()).hexdigest()
        )
    astr = candidate / "astrbot_plugin_dota2forge"
    assert len(runtime.public_requirements(astr)) == 3
    assert (astr / "INSTALL.md").read_text("utf-8") == (
        root / distribution.ASTR_INSTALL_GUIDE
    ).read_text("utf-8")
    assert "](INSTALL.md)" in (astr / "README.md").read_text("utf-8")
    assert "dota2uid" not in (astr / "runtime-wheels.json").read_text("utf-8")
    manifest_sources = json.loads((candidate / "manifest.json").read_text("utf-8"))["source_sha256"]
    assert "wheels/astrbot_plugin_dota2forge-0.1.0a4-py3-none-any.whl" in manifest_sources
    plain = distribution.build_distributions(
        root, tmp_path / "plain", "https://github.com/HBLADEH/astrbot_plugin_dota2forge", REPO
    )
    assert "install_runtime.py" not in (plain / "Dota2UID/README.md").read_text("utf-8")


def test_astrbot_manifest_selects_only_its_adapter_and_repo(manifests):
    root, release, manifest = manifests
    release["plugin"] = "astrbot_plugin_dota2forge"
    release["versions"]["astrbot-plugin-dota2forge"] = release["versions"].pop("dota2uid")
    wheel = manifest["wheels"].pop("dota2uid")
    wheel["filename"] = wheel["filename"].replace("dota2uid", "astrbot_plugin_dota2forge")
    manifest["wheels"]["astrbot-plugin-dota2forge"] = wheel
    manifest["repository"] = "https://github.com/HBLADEH/astrbot_plugin_dota2forge"
    (root / "release.json").write_text(json.dumps(release), "utf-8")
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")
    requirements = runtime.public_requirements(root)
    assert len(requirements) == 3
    assert requirements[0].startswith("astrbot-plugin-dota2forge[stratz] @ ")
    assert all("/astrbot_plugin_dota2forge/releases/download/v0.1.0a4/" in r for r in requirements)
    manifest["repository"] = REPO
    (root / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")
    with pytest.raises(ValueError):
        runtime.public_requirements(root)

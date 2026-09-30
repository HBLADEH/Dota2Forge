from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_governance as checks
from scripts import generate_reference as reference
from scripts import smoke_wheels

ROOT = Path(__file__).resolve().parents[1]
NOTE = ".agents/notes/implemented/2026-09-30-workspace-foundation.md"
CORE = "packages/dota2forge-core"


@pytest.fixture
def repository(tmp_path):
    for name in [
        ".agents",
        "packages",
        "adapters",
        "docs",
        "scripts",
        "tests",
        ".github",
        "deploy",
    ]:
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    for pattern in ["*.md", "*.toml", "LICENSE"]:
        for path in ROOT.glob(pattern):
            shutil.copy(path, tmp_path / path.name)
    return tmp_path


def change_policy(root, operation):
    path = root / ".agents/policy.json"
    policy = json.loads(path.read_text())
    operation(policy)
    path.write_text(json.dumps(policy))


def test_valid_repository_passes(repository):
    assert checks.check_repository(repository) == []


@pytest.mark.parametrize("value", ["unknown", 2])
def test_policy_rejects_unknown_fields_and_versions(repository, value):
    change_policy(
        repository,
        lambda p: p.update({"extra": True} if value == "unknown" else {"schema_version": value}),
    )
    assert "Invalid policy" in "\n".join(checks.check_repository(repository))


@pytest.mark.parametrize("value", ["../outside", "/tmp", "missing", "adapters/Dota2UID"])
def test_policy_rejects_bad_paths(repository, value):
    change_policy(repository, lambda p: p["architecture"].update(core_path=value))
    assert checks.check_repository(repository)


def test_policy_requires_complete_workspace(repository):
    path = repository / "pyproject.toml"
    path.write_text(path.read_text().replace(', "adapters/Dota2UID"', ""))
    assert "cover exactly" in "\n".join(checks.check_repository(repository))


@pytest.mark.parametrize(
    ("file", "content", "message"),
    [
        ("AGENTS.md", "字" * 3001, "character budget"),
        ("AGENTS.md", "a\n" * 81, "line budget"),
        ("docs/cookbook/too-long.md", "字" * 4001, "character budget"),
        ("docs/links.md", "[bad](missing.md)", "broken local link"),
        ("docs/links.md", "[bad](architecture.md#missing)", "missing anchor"),
        ("docs/links.md", "[ref]: missing.md", "broken local link"),
        ("docs/links.md", "[bad](../../outside.md)", "broken local link"),
    ],
)
def test_documents_reject_bad_inputs(repository, file, content, message):
    (repository / file).write_text(content)
    assert message in "\n".join(checks.check_repository(repository))


def test_code_examples_and_external_links_are_not_local_files(repository):
    (repository / "docs/links.md").write_text(
        "```markdown\n[example](does-not-exist.md)\n```\n"
        "`[code](absent.md)`\n[web](https://example.invalid/no-network)\n"
        "[heading](#有效标题)\n# 有效标题\n"
    )
    assert checks.check_repository(repository) == []
    assert checks.anchors("# Title\n# Title\n") == {"title", "title-1"}


@pytest.mark.parametrize(
    "source",
    [
        "import astrbot",
        "from gsuid_core import bot",
        "import nonebot",
        "__import__('astrbot')",
        "import importlib as il\nil.import_module('gsuid_core')",
        "from importlib import import_module as load\nload('astrbot')",
        "import Dota2UID",
        "import astrbot_plugin_dota2forge",
    ],
)
def test_core_rejects_platform_imports(repository, source):
    (repository / CORE / "src/dota2forge_core/bad.py").write_text(source)
    assert "forbidden import" in "\n".join(checks.check_repository(repository))


@pytest.mark.parametrize(
    ("original", "declaration"),
    [
        ("dependencies = []", 'dependencies = ["astrbot>=1"]'),
        (
            "[project.optional-dependencies]",
            '[project.optional-dependencies]\nhost = ["gsuid_core"]',
        ),
    ],
)
def test_dependency_declarations_checked(repository, original, declaration):
    path = repository / CORE / "pyproject.toml"
    path.write_text(path.read_text().replace(original, declaration))
    assert "forbidden dependency" in "\n".join(checks.check_repository(repository))


def test_development_and_build_dependencies_checked(repository):
    path = repository / CORE / "pyproject.toml"
    path.write_text(
        path.read_text().replace('"hatchling>=1.27,<2"', '"astrbot"')
        + '\n[dependency-groups]\ndev = ["nonebot2"]\n'
    )
    errors = "\n".join(checks.check_repository(repository))
    assert "forbidden dependency astrbot" in errors
    assert "forbidden dependency nonebot2" in errors


def test_adapter_cross_import_and_host_sdk_checked(repository):
    path = repository / "adapters/Dota2UID/src/Dota2UID/bad.py"
    path.write_text("import astrbot_plugin_dota2forge\nimport astrbot")
    assert "forbidden import" in "\n".join(checks.check_repository(repository))
    path.write_text("import gsuid_core\nimport dota2forge_core")
    assert checks.check_repository(repository) == []


def test_missing_package_init_fails(repository):
    (repository / CORE / "src/dota2forge_core/__init__.py").unlink()
    assert "missing package" in "\n".join(checks.check_repository(repository))


def test_invalid_python_fails(repository):
    (repository / CORE / "src/dota2forge_core/bad.py").write_text("import ???")
    assert "Governance input error" in "\n".join(checks.check_repository(repository))


def test_missing_decision_record_fails(repository):
    for note in (repository / ".agents/notes/implemented").glob("*.md"):
        note.unlink()
    assert "Missing implemented decision" in "\n".join(checks.check_repository(repository))


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("Category: architecture", "Category: typo", "invalid note category"),
        ("## Decision", "## Wrong", "missing note section Decision"),
        ("Related code:", "Code:", "missing linked field Related code"),
    ],
)
def test_note_structure(repository, old, new, message):
    path = repository / NOTE
    path.write_text(path.read_text().replace(old, new))
    assert message in "\n".join(checks.check_repository(repository))


def test_note_lifecycle_and_filename(repository):
    (repository / NOTE).rename(repository / ".agents/notes/invalid.md")
    errors = "\n".join(checks.check_repository(repository))
    assert "invalid note lifecycle" in errors
    assert "invalid note filename" in errors


def test_sensitive_diff_requires_changed_note(repository):
    changed = {CORE + "/src/dota2forge_core/__init__.py"}
    assert "requires a changed" in "\n".join(checks.check_repository(repository, changed))
    assert checks.check_repository(repository, changed | {NOTE}) == []
    assert checks.check_repository(repository, {"README.md"}) == []


def test_generated_drift_fails(repository):
    (repository / reference.OUTPUT).write_text("wrong")
    assert "Generated reference drift" in "\n".join(checks.check_repository(repository))


def test_reference_cli(repository, monkeypatch):
    monkeypatch.setattr(reference, "ROOT", repository)
    (repository / reference.OUTPUT).unlink()
    assert reference.main(["--check"]) == 1
    assert reference.main([]) == 0
    assert reference.main(["--check"]) == 0


@pytest.mark.parametrize(
    "members",
    ['["../escape"]', '["missing"]', '["packages/dota2forge-core", "packages/dota2forge-core"]'],
)
def test_workspace_members_rejected(tmp_path, members):
    (tmp_path / "pyproject.toml").write_text(f"[tool.uv.workspace]\nmembers={members}")
    path = tmp_path / CORE / "pyproject.toml"
    path.parent.mkdir(parents=True)
    path.touch()
    with pytest.raises(ValueError):
        reference.package_configs(tmp_path)


def test_nonconstant_dynamic_imports_not_claimed_supported():
    assert checks.imported_modules(ast.parse("__import__(variable)")) == []


def test_required_commands_fail_closed(tmp_path, monkeypatch):
    assert checks.run_checks(tmp_path, [["/no-such-dota2forge-command"]]) == 1
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 3))
    assert checks.run_checks(tmp_path, [["ruff"]]) == 1
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0))
    assert checks.run_checks(tmp_path, [["ruff"]]) == 0


def test_python_checks_use_current_environment_interpreter(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    original = ["python", "-m", "coverage", "report"]
    assert checks.run_checks(tmp_path, [original]) == 0
    assert calls == [[sys.executable, "-m", "coverage", "report"]]
    assert original == ["python", "-m", "coverage", "report"]


def test_reference_package_order_is_platform_independent(repository):
    paths = [
        path.relative_to(repository).as_posix() for path in reference.package_configs(repository)
    ]
    assert paths == sorted(paths)
    assert paths[0] == "adapters/Dota2UID/pyproject.toml"


def test_cli_runs_checks_after_governance(repository, monkeypatch):
    monkeypatch.setattr(checks, "ROOT", repository)
    calls = []
    monkeypatch.setattr(checks, "run_checks", lambda root, commands: calls.append(commands) or 0)
    assert checks.main(["--all"]) == 0
    assert calls[0][-3:] == [
        ["pytest"],
        ["python", "-m", "coverage", "report", "--include=scripts/*", "--fail-under=80"],
        [
            "python",
            "-m",
            "coverage",
            "report",
            "--include=packages/dota2forge-core/*",
            "--fail-under=80",
        ],
    ]
    (repository / NOTE).unlink()
    assert checks.main(["--all"]) == 1


def test_cli_invalid_git_base_fails(repository, monkeypatch):
    monkeypatch.setattr(checks, "ROOT", repository)
    assert checks.main(["--base", "does-not-exist"]) == 1


def test_git_scope_covers_committed_staged_working_deleted_and_untracked(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-b", "main")
    git("config", "user.name", "Dota2Forge test")
    git("config", "user.email", "test@example.invalid")
    for name in ["committed", "staged", "working", "deleted", "renamed"]:
        (tmp_path / name).write_text("initial")
    git("add", ".")
    git("commit", "-m", "fixture base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "committed").write_text("committed change")
    git("add", "committed")
    git("commit", "-m", "fixture change")
    (tmp_path / "staged").write_text("staged change")
    git("add", "staged")
    (tmp_path / "working").write_text("working change")
    (tmp_path / "deleted").unlink()
    git("mv", "renamed", "new name")
    (tmp_path / "untracked").touch()
    assert checks.changed_paths(tmp_path, base) == {
        "committed",
        "staged",
        "working",
        "deleted",
        "renamed",
        "new name",
        "untracked",
    }


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_wheel_smoke_uses_offline_install_and_isolated_import(monkeypatch, platform):
    commands = []
    monkeypatch.setattr(smoke_wheels.sys, "platform", platform)
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: commands.append(args))
    assert smoke_wheels.main() == 0
    assert len(commands) == 9
    for install in commands[1::3]:
        assert "--no-index" in install
        assert "--no-cache" in install
    assert "from Dota2UID.commands import parse_command" in commands[-1][-1]
    assert "host_entry.py.template" in commands[-1][-1]
    for command in commands[2::3]:
        assert "-I" in command
        suffix = "Scripts/python.exe" if platform == "win32" else "bin/python"
        assert Path(command[0]).as_posix().endswith(suffix)


@pytest.mark.parametrize("low_group", [None, "scripts", "packages/dota2forge-core"])
def test_coverage_gates_keep_core_and_governance_independent(tmp_path, low_group):
    from coverage import CoverageData

    data = CoverageData(basename=str(tmp_path / ".coverage"))
    for group in ("scripts", "packages/dota2forge-core"):
        source = tmp_path / group / "sample.py"
        source.parent.mkdir(parents=True)
        source.write_text("\n".join(f"value_{index} = {index}" for index in range(1, 11)))
        data.add_lines({str(source): {1} if group == low_group else set(range(1, 11))})
    data.write()
    gates = checks.load_policy(ROOT)["verification"]["commands"][-2:]
    for group, command in zip(("scripts", "packages/dota2forge-core"), gates, strict=True):
        result = subprocess.run(
            [sys.executable, *command[1:]], cwd=tmp_path, capture_output=True, text=True
        )
        assert result.returncode == (2 if group == low_group else 0), result.stdout + result.stderr


def test_coverage_gate_fails_without_data(tmp_path):
    command = checks.load_policy(ROOT)["verification"]["commands"][-1]
    result = subprocess.run(
        [sys.executable, *command[1:]], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode != 0

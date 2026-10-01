"""Validate repository contracts and run every registered offline check."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_reference import OUTPUT, package_configs, read_toml, render

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"}


def files(root: Path, pattern: str) -> list[Path]:
    return sorted(
        p for p in root.rglob(pattern) if not IGNORED.intersection(p.relative_to(root).parts)
    )


def inside(root: Path, value: str) -> Path:
    path = root / value
    if Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError(f"Invalid repository path: {value}")
    if not path.resolve().is_relative_to(root.resolve()) or not path.exists():
        raise ValueError(f"Missing or escaped repository path: {value}")
    return path


def load_policy(root: Path) -> dict[str, Any]:
    policy: dict[str, Any] = json.loads((root / ".agents/policy.json").read_text())
    schema = json.loads((root / ".agents/policy.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(policy), key=lambda e: str(e.path))
    if errors:
        raise ValueError("Invalid policy: " + "; ".join(e.message for e in errors))
    architecture = policy["architecture"]
    for value in [
        architecture["core_path"],
        *architecture["adapter_paths"],
        *architecture["shared_paths"],
        *policy["documents"]["generated_paths"],
    ]:
        inside(root, value)
    paths = [
        architecture["core_path"],
        *architecture["adapter_paths"],
        *architecture["shared_paths"],
    ]
    if len(set(paths)) != len(paths):
        raise ValueError("Architecture paths must be distinct")
    actual = {p.parent.relative_to(root).as_posix() for p in package_configs(root)}
    if actual != set(paths):
        raise ValueError("Architecture paths must cover exactly the workspace packages")
    return policy


def prose(text: str) -> str:
    """Ignore fenced examples and inline code when inspecting prose links."""
    text = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def anchors(text: str) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    for title in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", text):
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def check_documents(root: Path, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    budgets = policy["documents"]
    for path in files(root, "*.md"):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        budget: int | None = None
        if relative == "AGENTS.md":
            budget = budgets["root_agents"]["max_chars"]
            if len(text.splitlines()) > budgets["root_agents"]["max_lines"]:
                errors.append(f"{relative}: line budget exceeded")
        elif path.name == "AGENTS.md":
            budget = budgets["scoped_agents_max_chars"]
        else:
            for prefix, key in {
                "docs/architecture.md": "architecture_max_chars",
                "docs/subsystems/": "subsystem_max_chars",
                "docs/cookbook/": "cookbook_max_chars",
                ".agents/notes/": "note_max_chars",
                "docs/postmortem/": "postmortem_max_chars",
                ".agents/tasks/": "task_max_chars",
            }.items():
                if relative.startswith(prefix):
                    budget = budgets[key]
                    break
        if budget is not None and len(re.sub(r"\s", "", text)) > budget:
            errors.append(f"{relative}: character budget exceeded ({budget})")
        content = prose(text)
        destinations = re.findall(r"!?\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+\"[^\"]*\")?\)", content)
        destinations += re.findall(r"(?m)^\s*\[[^\]]+\]:\s*<?([^\s>]+)>?", content)
        for destination in destinations:
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc:
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not target.is_relative_to(root.resolve()) or not target.exists():
                errors.append(f"{relative}: broken local link {destination}")
            elif (
                parsed.fragment
                and target.suffix == ".md"
                and unquote(parsed.fragment) not in anchors(target.read_text(encoding="utf-8"))
            ):
                errors.append(f"{relative}: missing anchor {destination}")
    return errors


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def imported_modules(tree: ast.AST) -> list[str]:
    names: list[str] = []
    module_aliases = {"importlib"}
    function_aliases = {"__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
            module_aliases.update(a.asname or a.name for a in node.names if a.name == "importlib")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
                if node.module == "importlib":
                    function_aliases.update(
                        a.asname or a.name for a in node.names if a.name == "import_module"
                    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        call = node.func
        dynamic = (isinstance(call, ast.Name) and call.id in function_aliases) or (
            isinstance(call, ast.Attribute)
            and call.attr == "import_module"
            and isinstance(call.value, ast.Name)
            and call.value.id in module_aliases
        )
        if dynamic and isinstance(node.args[0], ast.Constant):
            value = node.args[0].value
            if isinstance(value, str):
                names.append(value)
    return names


def check_architecture(root: Path, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    architecture = policy["architecture"]
    configs = {p.parent.relative_to(root).as_posix(): read_toml(p) for p in package_configs(root)}
    imports: dict[str, set[str]] = {}
    for relative, config in configs.items():
        entries = config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        imports[relative] = set()
        for entry in entries:
            package = inside(root, f"{relative}/{entry}")
            if not (package / "__init__.py").is_file():
                errors.append(f"{relative}: missing package __init__.py")
            imports[relative].add(package.name)
    core = architecture["core_path"]
    adapters = architecture["adapter_paths"]
    shared = architecture["shared_paths"]
    for relative, config in configs.items():
        forbidden_paths = (
            [*adapters, *shared]
            if relative == core
            else adapters
            if relative in shared
            else [p for p in adapters if p != relative]
        )
        forbidden = {name for p in forbidden_paths for name in imports[p]}
        distributions = {normalized(configs[p]["project"]["name"]) for p in forbidden_paths}
        if relative == core or relative in shared:
            forbidden.update(architecture["platform_imports"])
            distributions.update(map(normalized, architecture["platform_distributions"]))
            if relative == core:
                distributions.update({"pillow", "playwright"})
        else:
            own_sdk = architecture["adapter_sdk_imports"][relative]
            forbidden.update(set(architecture["platform_imports"]) - {own_sdk})
            distributions.update(
                normalized(name)
                for name in architecture["platform_distributions"]
                if normalized(name) != normalized(own_sdk)
            )
        dependencies = list(config["project"].get("dependencies", []))
        dependencies += config["build-system"]["requires"]
        for group in config["project"].get("optional-dependencies", {}).values():
            dependencies.extend(group)
        for group in config.get("dependency-groups", {}).values():
            dependencies.extend(item for item in group if isinstance(item, str))
        for dependency in dependencies:
            name = re.split(r"[\s\[<>=!~;@]", dependency, maxsplit=1)[0]
            if normalized(name) in distributions:
                errors.append(f"{relative}: forbidden dependency {name}")
        for path in files(root / relative, "*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for name in imported_modules(tree):
                if name.split(".")[0] in forbidden:
                    errors.append(f"{path.relative_to(root)}: forbidden import {name}")
                if relative == core and name.split(".")[0] in {"PIL", "playwright"}:
                    errors.append(f"{path.relative_to(root)}: forbidden rendering import {name}")
    return errors


def check_notes(root: Path, policy: dict[str, Any], changed: set[str] | None) -> list[str]:
    errors: list[str] = []
    notes = policy["notes"]
    implemented: set[str] = set()
    for path in files(root / ".agents/notes", "*.md"):
        if path.name == "AGENTS.md":
            continue
        relative = path.relative_to(root).as_posix()
        if path.parent.name not in {"proposed", "implemented", "archived"}:
            errors.append(f"{relative}: invalid note lifecycle directory")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-.+\.md", path.name):
            errors.append(f"{relative}: invalid note filename")
        text = path.read_text(encoding="utf-8")
        category = re.search(r"(?m)^Category: (.+)$", text)
        if not category or category[1] not in notes["categories"]:
            errors.append(f"{relative}: invalid note category")
        for section in notes["required_sections"]:
            if not re.search(rf"(?m)^## {re.escape(section)}\s*$", text):
                errors.append(f"{relative}: missing note section {section}")
        for field in ["Related task", "Related code", "Related docs"]:
            if not re.search(rf"(?m)^{field}: \[.+\]\(.+\)$", text):
                errors.append(f"{relative}: missing linked field {field}")
        if path.parent.name == "implemented":
            implemented.add(relative)
    if not implemented:
        errors.append("Missing implemented decision record")
    if changed is not None:
        sensitive = any(name.startswith(tuple(notes["sensitive_paths"])) for name in changed)
        if sensitive and not implemented.intersection(changed):
            errors.append("Sensitive change requires a changed implemented decision record")
    return errors


def changed_paths(root: Path, base: str) -> set[str]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, text=True)

    # Verify the ref before passing it to diff; include committed, staged and working changes.
    commit = git("rev-parse", "--verify", f"{base}^{{commit}}").strip()
    ancestor = git("merge-base", commit, "HEAD").strip()
    paths = git("diff", "--name-only", "--no-renames", "-z", ancestor, "--").split("\0")
    paths += git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return set(filter(None, paths))


def check_repository(root: Path, changed: set[str] | None = None) -> list[str]:
    try:
        policy = load_policy(root)
        errors = check_documents(root, policy)
        errors += check_architecture(root, policy)
        errors += check_notes(root, policy, changed)
        generated = root / OUTPUT
        if not generated.exists() or generated.read_text(encoding="utf-8") != render(root):
            errors.append(f"Generated reference drift: {OUTPUT}")
        return errors
    except (ValueError, KeyError, TypeError, OSError, SyntaxError) as exc:
        return [f"Governance input error: {exc}"]


def run_checks(root: Path, commands: list[list[str]]) -> int:
    for command in commands:
        print("RUN " + " ".join(command), flush=True)
        invocation = [sys.executable, *command[1:]] if command[0] == "python" else command
        try:
            result = subprocess.run(invocation, cwd=root, check=False)
        except OSError as exc:
            print(f"Required command unavailable: {exc}", file=sys.stderr)
            return 1
        if result.returncode:
            print(f"Required command failed: {command[0]}", file=sys.stderr)
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true")
    mode.add_argument(
        "--base", help="Compare merge-base through working tree; still run all checks"
    )
    args = parser.parse_args(argv)
    try:
        changed = changed_paths(ROOT, args.base) if args.base else None
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Cannot determine change scope: {exc}", file=sys.stderr)
        return 1
    errors = check_repository(ROOT, changed)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Governance checks passed. Live host verification is recorded separately in tasks.")
    return run_checks(ROOT, load_policy(ROOT)["verification"]["commands"])


if __name__ == "__main__":
    raise SystemExit(main())

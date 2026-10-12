"""Gated cold deployment; default is read-only candidate validation.

Run on the already authorized remote server. Output is sanitized JSON only.
The candidate must be a fresh public-main clone under the dedicated /tmp prefix.
"""

import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import sysconfig
from pathlib import Path, PurePosixPath

CONTAINER = "gscore"
ROOT = Path("/gsuid_core")
PLUGIN = ROOT / "gsuid_core/plugins/Dota2UID"
DATA = ROOT / "data/Dota2UID"
SERVICE = ROOT / "data/plugins_configs/Dota2UID.json"
BACKUP_PARENT = "/srv/data/services/bot-stack/backups"
EXPECTED_IMAGE = "sha256:288105490f0231cbd9117a04bbfd44c2b5c6ec579317d4ed37a8641a38bd2fc1"
EXPECTED_SDK = "70eeeacb151d1b92f4cad9aa766efec5d567c25e"
EXPECTED_PREVIOUS_HEAD = "72259b18d98199d9b883da7bee48d5783cdc769f"
EXPECTED_VERSIONS = {
    "dota2forge-assets": "0.1.0a1",
    "dota2forge-core": "0.1.0a7",
    "dota2forge-renderer": "0.1.0a7",
    "dota2uid": "0.1.0a14",
}
SAFE_RESTART_ORIGINAL = False


class DeploymentError(Exception):
    pass


class MaintenanceFailure(DeploymentError):
    def __init__(self, code, safe_restart_original):
        super().__init__(code)
        self.safe_restart_original = safe_restart_original


def require(condition, code):
    if not condition:
        raise DeploymentError(code)


def run(command, *, input_text=None, timeout=90):
    process = subprocess.run(
        command, input=input_text, text=True, capture_output=True, timeout=timeout
    )
    require(process.returncode == 0, "subprocess_failed")
    return process.stdout


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(path, *, exclude=()):
    root = Path(path)
    require(root.is_dir() and not root.is_symlink(), "invalid_tree_root")
    files = {}
    for entry in root.rglob("*"):
        relative = entry.relative_to(root)
        if any(part in exclude for part in relative.parts):
            continue
        require(not entry.is_symlink(), "symlink_rejected")
        require(entry.resolve().is_relative_to(root.resolve()), "path_escape")
        if entry.is_file():
            files[relative.as_posix()] = sha(entry)
    return files


def fingerprint(files):
    return {
        "files": len(files),
        "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    }


def library_fingerprint():
    root = Path(sysconfig.get_paths()["purelib"])
    files = {}
    for entry in root.rglob("*"):
        relative = entry.relative_to(root)
        if "__pycache__" in relative.parts or entry.suffix == ".pyc":
            continue
        if entry.is_symlink():
            files[relative.as_posix()] = hashlib.sha256(os.readlink(entry).encode()).hexdigest()
        elif entry.is_file():
            files[relative.as_posix()] = sha(entry)
    return fingerprint(files)


def git(path, *args):
    return run(
        [
            "git",
            "-c",
            "safe.directory=" + str(path),
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(path),
            *args,
        ]
    ).strip()


def database(path, tables):
    record = {"exists": path.exists()}
    if not path.exists():
        return record
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        record["schema_version"] = connection.execute("PRAGMA user_version").fetchone()[0]
        record["counts"] = {}
        record["table_sha256"] = {}
        for table in tables:
            rows = connection.execute("SELECT * FROM " + table).fetchall()
            encoded = [json.dumps(row, ensure_ascii=True, separators=(",", ":")) for row in rows]
            record["counts"][table] = len(rows)
            record["table_sha256"][table] = hashlib.sha256(
                json.dumps(sorted(encoded), separators=(",", ":")).encode()
            ).hexdigest()
        record["files_sha256"] = {
            suffix: sha(Path(str(path) + suffix))
            for suffix in ("", "-wal", "-shm")
            if Path(str(path) + suffix).is_file()
        }
    finally:
        connection.close()
    return record


def snapshot():
    def version(name):
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None

    config = DATA / "config.json"
    raw = json.loads(config.read_text())

    def field(name):
        value = raw.get(name)
        return value.get("data") if isinstance(value, dict) else value

    data_files = tree(DATA)
    sdk_files = tree(ROOT / "gsuid_core", exclude=("plugins", "__pycache__"))
    pillow = importlib.metadata.distribution("pillow")
    native_files = {
        str(name): sha(pillow.locate_file(name))
        for name in pillow.files or ()
        if str(name).endswith((".so", ".pyd", ".dll"))
    }
    active_path = DATA / "runtime/active.json"
    active = json.loads(active_path.read_text()) if active_path.exists() else None
    runtime = {"exists": active is not None}
    if active:
        require(re.fullmatch(r"[0-9a-f]{64}", active["manifest_sha256"]), "invalid_active_digest")
        require(re.fullmatch(r"[0-9a-f]{32}", active["generation"]), "invalid_active_generation")
        generation = DATA / "runtime" / active["manifest_sha256"] / active["generation"]
        marker = json.loads((generation / ".complete.json").read_text())
        generation_files = tree(generation)
        runtime.update(
            versions=active.get("versions"),
            manifest_sha256=active["manifest_sha256"],
            file_count=len(marker["files"]),
            complete_matches=(marker["manifest_sha256"] == active["manifest_sha256"]),
            files_match=(
                set(generation_files) == set(marker["files"]) | {".complete.json"}
                and all(
                    generation_files.get(name) == digest for name, digest in marker["files"].items()
                )
            ),
        )
    return {
        "sdk_head": git(ROOT, "rev-parse", "HEAD"),
        "sdk_tree": fingerprint(sdk_files),
        "global_versions": {
            name: version(name)
            for name in (
                "gsuid-core",
                "httpx",
                "pillow",
                "dota2forge-core",
                "dota2forge-renderer",
                "dota2forge-assets",
                "dota2uid",
            )
        },
        "pillow_native": fingerprint(native_files),
        "python_libraries": library_fingerprint(),
        "plugin_head": git(PLUGIN, "rev-parse", "HEAD"),
        "plugin_tree": fingerprint(tree(PLUGIN, exclude=(".git", "__pycache__"))),
        "data_tree": fingerprint(data_files),
        "material_files": {
            name: digest
            for name, digest in data_files.items()
            if name.startswith("illustrations/")
            and PurePosixPath(name).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        },
        "configuration": {
            "sha256": sha(config),
            "token_configured": bool(field("stratz_token")),
            "reply_mode": field("reply_mode"),
            "subscriptions_enabled": field("subscriptions_enabled"),
        },
        "service_configuration_sha256": sha(SERVICE),
        "databases": {
            "bindings.sqlite3": database(DATA / "bindings.sqlite3", ("bindings",)),
            "subscriptions.sqlite3": database(
                DATA / "subscriptions.sqlite3",
                ("subscriptions", "subscription_events", "subscription_attempts"),
            ),
        },
        "active_runtime": runtime,
    }


def inspect_container():
    item = json.loads(run(["docker", "inspect", CONTAINER]))[0]
    mounts = {mount["Destination"]: mount for mount in item["Mounts"]}
    require(
        mounts["/gsuid_core/data"]["Source"] == "/srv/data/services/bot-stack/data/gscore/data",
        "data_mount_changed",
    )
    require(
        mounts["/gsuid_core/gsuid_core/plugins"]["Source"]
        == "/srv/data/services/bot-stack/data/gscore/plugins",
        "plugin_mount_changed",
    )
    require(mounts["/venv"]["Name"] == "bot-stack_gscore_venv", "venv_mount_changed")
    return item


def log_evidence(since):
    process = subprocess.run(
        ["docker", "logs", "--since", since, "--tail", "3000", CONTAINER],
        capture_output=True,
        text=True,
        timeout=30,
    )
    content = re.sub(r"\x1b\[[0-9;]*m", "", process.stdout + process.stderr)
    starts = re.findall(
        r"Dota2UID initialized state=([a-z_]+) subscriptions_enabled=(True|False) "
        r"job_registered=(True|False)",
        content,
    )
    return {
        "log_read_success": process.returncode == 0,
        "shutdown_confirmed": (
            "Dota2UID stopped state=stopped client_closed=True job_registered=False" in content
        ),
        "startup_states": [state for state, _, _ in starts],
        "ready_with_subscription_job": any(
            state == "ready" and enabled == "True" and job == "True"
            for state, enabled, job in starts
        ),
        "known_bootstrap_error": any(
            "Dota2UID" in line and "code=" in line and ("failed" in line or "unavailable" in line)
            for line in content.splitlines()
        ),
        "raw_logs_output": False,
    }


def source_snapshot():
    source = Path(__file__).read_text()
    return json.loads(
        run(
            [
                "docker",
                "exec",
                "-i",
                CONTAINER,
                "/venv/bin/python",
                "-I",
                "-B",
                "-c",
                source,
                "--snapshot",
            ]
        )
    )


def staging_path(path):
    value = Path(path)
    require(value.is_absolute() and not value.is_symlink(), "invalid_staging_path")
    resolved = value.resolve()
    require(resolved.is_relative_to(Path("/tmp")), "staging_outside_tmp")
    require(
        len(resolved.parts) > 2 and resolved.parts[2].startswith("dota2forge-subscription-cards-"),
        "invalid_staging_prefix",
    )
    return resolved


def expected_files(manifest, digest):
    require(sha(manifest) == digest, "manifest_bytes_changed")
    raw = json.loads(Path(manifest).read_text())
    files = {
        name.removeprefix("Dota2UID/"): value
        for name, value in raw["files_sha256"].items()
        if name.startswith("Dota2UID/")
    }
    require(bool(files), "empty_expected_files")
    for name, value in files.items():
        relative = PurePosixPath(name)
        require(
            not relative.is_absolute()
            and not any(part in ("..", ".git", "__pycache__") for part in relative.parts),
            "invalid_manifest_path",
        )
        require(re.fullmatch(r"[0-9a-f]{64}", value), "invalid_manifest_digest")
    return files


def validate_candidate(candidate, files, head):
    require(tree(candidate, exclude=(".git", "__pycache__")) == files, "candidate_file_mismatch")
    require(not any(path.is_symlink() for path in candidate.rglob("*")), "candidate_git_symlink")
    require(git(candidate, "rev-parse", "HEAD") == head, "candidate_head_mismatch")
    require(git(candidate, "rev-parse", "v0.1.0a14^{commit}") == head, "candidate_tag_mismatch")
    require(
        git(candidate, "symbolic-ref", "--short", "HEAD") == "main", "candidate_branch_mismatch"
    )
    require(
        git(candidate, "remote", "get-url", "origin").rstrip("/")
        in ("https://github.com/HBLADEH/Dota2UID", "https://github.com/HBLADEH/Dota2UID.git"),
        "candidate_origin_mismatch",
    )
    require(
        git(candidate, "status", "--porcelain", "--untracked-files=no") == "", "candidate_dirty"
    )
    require(
        json.loads((candidate / "release.json").read_text())["versions"] == EXPECTED_VERSIONS,
        "candidate_versions_mismatch",
    )
    manifest_digest = sha(candidate / "runtime-wheels.json")
    require(
        json.loads((candidate / "deployment.json").read_text())["manifest_sha256"]
        == manifest_digest,
        "candidate_runtime_manifest_mismatch",
    )
    return manifest_digest


def maintenance(request):
    global SAFE_RESTART_ORIGINAL
    SAFE_RESTART_ORIGINAL = True
    require(re.fullmatch(r"dota2uid-a14-[0-9TZ-]+", request["backup_name"]), "invalid_backup_name")
    candidate = Path("/candidate")
    files = request["expected_files"]
    validate_candidate(candidate, files, request["expected_head"])
    backup = Path("/backups") / request["backup_name"]
    require(not backup.exists(), "backup_already_exists")
    backup.mkdir(mode=0o700)
    backup.chmod(0o700)
    before = snapshot()
    require(before["sdk_head"] == request["sdk_head"], "sdk_drift_before_install")
    for key in (
        "sdk_head",
        "sdk_tree",
        "global_versions",
        "pillow_native",
        "python_libraries",
        "configuration",
        "service_configuration_sha256",
        "plugin_head",
        "plugin_tree",
    ):
        require(before[key] == request["prestop_snapshot"][key], "prestop_drift_" + key)
    data_files = tree(DATA)
    plugin_files = tree(PLUGIN)
    shutil.copytree(PLUGIN, backup / "plugin", copy_function=shutil.copy2)
    shutil.copytree(DATA, backup / "data", copy_function=shutil.copy2)
    shutil.copy2(SERVICE, backup / "service.json")
    require(tree(backup / "plugin") == plugin_files, "plugin_backup_mismatch")
    require(tree(backup / "data") == data_files, "data_backup_mismatch")
    require(
        sha(backup / "service.json") == before["service_configuration_sha256"],
        "service_backup_mismatch",
    )
    (backup / "stopped-snapshot.json").write_text(json.dumps(before, sort_keys=True))
    (backup / "restore-image.json").write_text(
        json.dumps(
            {
                "container": CONTAINER,
                "image_id": request["image_id"],
                "sdk_head": before["sdk_head"],
            }
        )
    )
    parent = PLUGIN.parent.resolve()
    prepared = parent / (".Dota2UID-a14-prepared-" + request["backup_name"])
    retired = parent / (".Dota2UID-before-a14-" + request["backup_name"])
    require(
        prepared.parent == parent
        and retired.parent == parent
        and not prepared.exists()
        and not retired.exists(),
        "unsafe_replacement_paths",
    )
    installed = False
    try:
        shutil.copytree(candidate, prepared, copy_function=shutil.copy2)
        require(tree(prepared) == tree(candidate), "prepared_copy_mismatch")
        SAFE_RESTART_ORIGINAL = False
        PLUGIN.rename(retired)
        prepared.rename(PLUGIN)
        installed = True
        require(tree(PLUGIN, exclude=(".git", "__pycache__")) == files, "installed_file_mismatch")
        require(
            git(PLUGIN, "rev-parse", "HEAD") == request["expected_head"], "installed_head_mismatch"
        )
        require(
            tree(DATA) == data_files and sha(SERVICE) == before["service_configuration_sha256"],
            "business_data_changed_during_install",
        )
        after = snapshot()
        for key in (
            "sdk_head",
            "sdk_tree",
            "global_versions",
            "pillow_native",
            "python_libraries",
            "configuration",
            "service_configuration_sha256",
            "databases",
            "data_tree",
        ):
            require(after[key] == before[key], "beforestart_preservation_failed_" + key)
        # The independently verified private backup preserves the full old
        # checkout. A second directory in the discovery path must not survive.
        require(
            retired.resolve().parent == parent and not retired.is_symlink(), "unsafe_retired_delete"
        )
        shutil.rmtree(retired)
        return {
            "passed": True,
            "backup_path": BACKUP_PARENT + "/" + request["backup_name"],
            "snapshot": before,
            "before_start": after,
            "candidate_files_verified": len(files),
            "beforestart_data_and_attempts_unchanged": True,
            "rollback_performed": False,
        }
    except BaseException:
        if installed and PLUGIN.exists():
            require(
                PLUGIN.resolve().parent == parent and not PLUGIN.is_symlink(),
                "unsafe_plugin_rollback",
            )
            shutil.rmtree(PLUGIN)
        if retired.exists():
            if tree(retired) == plugin_files:
                retired.rename(PLUGIN)
            else:
                require(
                    retired.resolve().parent == parent and not retired.is_symlink(),
                    "unsafe_retired_rollback",
                )
                shutil.rmtree(retired)
                shutil.copytree(backup / "plugin", PLUGIN, copy_function=shutil.copy2)
        elif installed:
            shutil.copytree(backup / "plugin", PLUGIN, copy_function=shutil.copy2)
        if prepared.exists():
            require(
                prepared.resolve().parent == parent and not prepared.is_symlink(),
                "unsafe_prepared_rollback",
            )
            shutil.rmtree(prepared)
        require(tree(PLUGIN) == plugin_files, "rollback_plugin_integrity_failed")
        require(
            tree(DATA) == data_files and sha(SERVICE) == before["service_configuration_sha256"],
            "rollback_data_integrity_failed",
        )
        SAFE_RESTART_ORIGINAL = True
        raise


def maintenance_run(candidate, request):
    helper_root = Path(__file__).resolve().parent
    command = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--user",
        "0:0",
        "--volumes-from",
        CONTAINER,
        "--volume",
        str(candidate) + ":/candidate:ro",
        "--volume",
        str(helper_root) + ":/helpers:ro",
        "--volume",
        BACKUP_PARENT + ":/backups",
        "--entrypoint",
        "/venv/bin/python",
        request["image_id"],
        "-I",
        "-B",
        "/helpers/deploy_install.py",
        "--maintenance",
    ]
    process = subprocess.run(
        command, input=json.dumps(request), capture_output=True, text=True, timeout=120
    )
    try:
        result = json.loads(process.stdout)
    except ValueError:
        raise MaintenanceFailure("maintenance_result_invalid", False) from None
    if process.returncode != 0:
        code = result.get("error_category", "maintenance_failed")
        require(re.fullmatch(r"[A-Za-z0-9_]+", code), "invalid_maintenance_error_category")
        raise MaintenanceFailure(code, result.get("safe_to_restart_original") is True)
    require(result.get("passed") is True, "maintenance_did_not_pass")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--backup-name", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--expected-image", default=EXPECTED_IMAGE)
    parser.add_argument("--expected-sdk-head", default=EXPECTED_SDK)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    candidate = staging_path(args.candidate)
    manifest = staging_path(args.manifest)
    record_path = staging_path(args.record)
    require(not record_path.exists(), "record_already_exists")
    require(re.fullmatch(r"dota2uid-a14-[0-9TZ-]+", args.backup_name), "invalid_backup_name")
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_head), "invalid_expected_head")
    files = expected_files(manifest, args.manifest_sha256)
    runtime_digest = validate_candidate(candidate, files, args.expected_head)
    container = inspect_container()
    require(container["Image"] == args.expected_image, "image_drift")
    require(container["State"]["Running"], "host_not_running")
    before = source_snapshot()
    require(before["sdk_head"] == args.expected_sdk_head, "sdk_drift")
    require(before["plugin_head"] == EXPECTED_PREVIOUS_HEAD, "previous_plugin_drift")
    require(
        before["active_runtime"]["versions"]
        == {**EXPECTED_VERSIONS, "dota2uid": "0.1.0a13", "dota2forge-renderer": "0.1.0a6"},
        "previous_runtime_drift",
    )
    require(
        before["active_runtime"]["files_match"] and before["active_runtime"]["complete_matches"],
        "previous_runtime_integrity_failed",
    )
    require(
        before["configuration"]["token_configured"]
        and before["configuration"]["reply_mode"] == "image"
        and before["configuration"]["subscriptions_enabled"],
        "production_configuration_drift",
    )
    result = {
        "schema_version": 1,
        "passed": True,
        "applied": False,
        "read_only": not args.apply,
        "candidate_head": args.expected_head,
        "candidate_file_count": len(files),
        "runtime_manifest_sha256": runtime_digest,
        "expected_files": files,
        "expected_image": args.expected_image,
        "expected_versions": EXPECTED_VERSIONS,
        "backup_name": args.backup_name,
        "prestop_snapshot": before,
        "privacy": {
            "credentials_or_identity_output": False,
            "raw_logs_output": False,
            "provider_called_by_helper": False,
            "messages_sent_by_helper": False,
        },
    }
    if not args.apply:
        print(json.dumps(result, indent=2))
        return
    since = datetime.datetime.now(datetime.UTC).isoformat()
    run(["docker", "stop", "--time", "60", CONTAINER], timeout=75)
    stopped = inspect_container()
    require(not stopped["State"]["Running"], "host_still_running")
    result["shutdown"] = {
        "since": since,
        "exit_code": stopped["State"]["ExitCode"],
        "forced_kill": stopped["State"]["ExitCode"] == 137,
        **log_evidence(since),
    }
    if result["shutdown"]["forced_kill"] or not result["shutdown"]["shutdown_confirmed"]:
        run(["docker", "start", CONTAINER], timeout=45)
        raise DeploymentError("shutdown_lifecycle_not_confirmed_original_restarted")
    request = {
        "expected_files": files,
        "expected_head": args.expected_head,
        "backup_name": args.backup_name,
        "image_id": args.expected_image,
        "sdk_head": args.expected_sdk_head,
        "prestop_snapshot": before,
    }
    try:
        result["installation"] = maintenance_run(candidate, request)
    except MaintenanceFailure as error:
        result["passed"] = False
        result["installation_failure"] = {
            "error_category": str(error),
            "safe_to_restart_original": error.safe_restart_original,
        }
        if error.safe_restart_original:
            run(["docker", "start", CONTAINER], timeout=45)
            result["original_container_restarted"] = True
        else:
            result["original_container_restarted"] = False
        record_path.write_text(json.dumps(result, indent=2))
        raise
    result["applied"] = True
    result["read_only"] = False
    result["restart_since"] = datetime.datetime.now(datetime.UTC).isoformat()
    result["restart"] = {"postflight_pending": True}
    record_path.write_text(json.dumps(result, indent=2))
    run(["docker", "start", CONTAINER], timeout=45)
    restarted = inspect_container()
    require(restarted["State"]["Running"], "host_not_running_after_restart")
    result["restart"] = {
        "running": True,
        "started_at": restarted["State"]["StartedAt"],
        "postflight_pending": True,
    }
    record_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--snapshot"]:
            print(json.dumps(snapshot()))
        elif sys.argv[1:] == ["--maintenance"]:
            print(json.dumps(maintenance(json.load(sys.stdin))))
        else:
            main()
    except Exception as error:
        code = str(error) if isinstance(error, DeploymentError) else type(error).__name__
        print(
            json.dumps(
                {
                    "passed": False,
                    "error_category": code,
                    "safe_to_restart_original": SAFE_RESTART_ORIGINAL,
                    "raw_exception_output": False,
                }
            )
        )
        sys.exit(1)

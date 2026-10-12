"""Create a private current-state restore point with read-only SQLite sources."""

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deploy_install import (
    BACKUP_PARENT,
    CONTAINER,
    DATA,
    EXPECTED_IMAGE,
    PLUGIN,
    SERVICE,
    DeploymentError,
    database,
    expected_files,
    inspect_container,
    require,
    sha,
    staging_path,
    tree,
    validate_candidate,
)


def save_current(request):
    candidate = Path("/candidate")
    validate_candidate(candidate, request["files"], request["head"])
    require(
        re.fullmatch(r"dota2uid-a14-current-[0-9TZ]+", request["name"]),
        "invalid_current_backup_name",
    )
    require(
        DATA.stat().st_uid == 0 and PLUGIN.stat().st_uid == 0, "current_source_ownership_changed"
    )
    require(
        tree(PLUGIN, exclude=(".git", "__pycache__")) == request["files"],
        "current_source_plugin_changed",
    )
    root = Path("/backups") / request["name"]
    require(not root.exists() and not root.is_symlink(), "current_backup_already_exists")
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    config_sha, service_sha = sha(DATA / "config.json"), sha(SERVICE)
    shutil.copy2(DATA / "config.json", root / "config.json")
    shutil.copy2(SERVICE, root / "service.json")
    (root / "config.json").chmod(0o600)
    (root / "service.json").chmod(0o600)
    shutil.copytree(candidate, root / "plugin", copy_function=shutil.copy2)
    require(tree(root / "plugin") == tree(candidate), "current_backup_plugin_mismatch")
    records = {}
    for name, tables in (
        ("bindings.sqlite3", ("bindings",)),
        (
            "subscriptions.sqlite3",
            ("subscriptions", "subscription_events", "subscription_attempts"),
        ),
    ):
        source_path, target_path = DATA / name, root / name
        source = sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True, timeout=5)
        destination = sqlite3.connect(target_path)
        try:
            source.execute("PRAGMA query_only=ON")
            source.execute("BEGIN")
            schema = source.execute("PRAGMA user_version").fetchone()[0]
            counts = {
                table: source.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in tables
            }
            source.backup(destination)
            destination.commit()
            require(
                destination.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                "current_backup_database_invalid",
            )
        finally:
            destination.close()
            source.close()
        target_path.chmod(0o600)
        record = database(target_path, tables)
        require(
            record["schema_version"] == schema and record["counts"] == counts,
            "current_backup_database_snapshot_mismatch",
        )
        records[name] = record
    require(
        sha(root / "config.json") == config_sha == sha(DATA / "config.json"),
        "current_backup_config_changed",
    )
    require(
        sha(root / "service.json") == service_sha == sha(SERVICE), "current_backup_service_changed"
    )
    require(
        tree(PLUGIN, exclude=(".git", "__pycache__")) == request["files"],
        "current_source_plugin_changed_during_backup",
    )
    result = {
        "passed": True,
        "scope": "current_a14_restore_point",
        "is_pre_upgrade_backup": False,
        "backup_path": BACKUP_PARENT + "/" + request["name"],
        "directory_mode": "0700",
        "private_configuration_and_database_modes": "0600",
        "plugin_source": "verified_fresh_public_clone",
        "plugin_head": request["head"],
        "plugin_files_verified": len(request["files"]),
        "configuration_sha256": config_sha,
        "service_configuration_sha256": service_sha,
        "databases": records,
        "sqlite_source_mode": "ro_query_only_read_transaction",
        "sqlite_backup_integrity_check": "ok",
        "production_stop_restart_or_business_data_mutation": False,
        "private_restorepoint_created": True,
        "source_database_writes_performed": False,
        "privacy": {
            "credentials_or_identity_output": False,
            "raw_logs_output": False,
            "provider_called": False,
            "messages_sent": False,
        },
    }
    (root / "restorepoint.json").write_text(json.dumps(result, indent=2))
    (root / "restorepoint.json").chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    candidate = staging_path(args.candidate)
    files = expected_files(staging_path(args.manifest), args.manifest_sha256)
    validate_candidate(candidate, files, args.expected_head)
    container = inspect_container()
    require(
        container["Image"] == EXPECTED_IMAGE and container["State"]["Running"],
        "current_backup_target_changed",
    )
    request = {"files": files, "head": args.expected_head, "name": args.name}
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
        str(Path(__file__).resolve().parent) + ":/helpers:ro",
        "--volume",
        BACKUP_PARENT + ":/backups",
        "--entrypoint",
        "/venv/bin/python",
        EXPECTED_IMAGE,
        "-I",
        "-B",
        "/helpers/deploy_current_restorepoint.py",
        "--save-current",
    ]
    process = subprocess.run(
        command, input=json.dumps(request), capture_output=True, text=True, timeout=90
    )
    result = json.loads(process.stdout)
    print(json.dumps(result, indent=2))
    sys.exit(process.returncode)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--save-current"]:
            print(json.dumps(save_current(json.load(sys.stdin)), indent=2))
        else:
            main()
    except Exception as error:
        code = str(error) if isinstance(error, DeploymentError) else type(error).__name__
        print(json.dumps({"passed": False, "error_category": code, "raw_exception_output": False}))
        sys.exit(1)

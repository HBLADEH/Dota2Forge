"""Read-only production verification after the pinned GsCore cold update.

Only aggregate counts, digests, versions and redacted lifecycle evidence leave
the host. This helper imports no SDK/business module and calls no Provider.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deploy_install import (
    DeploymentError,
    fingerprint,
    inspect_container,
    log_evidence,
    require,
    source_snapshot,
    staging_path,
)


def check(record, after, container, logs):
    before = record["installation"]["snapshot"]
    require(container["State"]["Running"], "postflight_container_stopped")
    require(container["Image"] == record["expected_image"], "postflight_image_changed")
    require(after["plugin_head"] == record["candidate_head"], "postflight_plugin_head_mismatch")
    require(
        after["plugin_tree"] == fingerprint(record["expected_files"]),
        "postflight_plugin_files_mismatch",
    )
    preserved = {}
    for key in (
        "sdk_head",
        "sdk_tree",
        "global_versions",
        "pillow_native",
        "python_libraries",
        "configuration",
        "service_configuration_sha256",
    ):
        preserved[key] = after[key] == before[key]
        require(preserved[key], "postflight_preservation_failed_" + key)
    runtime = after["active_runtime"]
    require(
        runtime["versions"] == record["expected_versions"], "postflight_runtime_versions_mismatch"
    )
    require(
        runtime["manifest_sha256"] == record["runtime_manifest_sha256"],
        "postflight_runtime_manifest_mismatch",
    )
    require(
        runtime["files_match"] and runtime["complete_matches"], "postflight_runtime_files_mismatch"
    )
    materials = before["material_files"]
    require(
        all(after["material_files"].get(name) == digest for name, digest in materials.items()),
        "postflight_materials_changed",
    )
    databases = {}
    for name, tables in (
        ("bindings.sqlite3", ("bindings",)),
        ("subscriptions.sqlite3", ("subscriptions",)),
    ):
        old, new = before["databases"][name], after["databases"][name]
        require(old["exists"] and new["exists"], "postflight_database_missing")
        require(
            new["schema_version"] == old["schema_version"], "postflight_database_schema_changed"
        )
        require(
            all(new["table_sha256"][table] == old["table_sha256"][table] for table in tables),
            "postflight_business_rows_changed",
        )
        databases[name] = {
            "schema_version": new["schema_version"],
            "business_rows_preserved": True,
            "before_start_counts": old["counts"],
            "after_start_counts": new["counts"],
            "file_sha_changed_after_start": new["files_sha256"] != old["files_sha256"],
        }
    require(
        logs["log_read_success"] and logs["ready_with_subscription_job"], "postflight_not_ready"
    )
    require(not logs["known_bootstrap_error"], "postflight_bootstrap_error")
    return {
        "schema_version": 1,
        "passed": True,
        "production_read_only": True,
        "candidate_head": record["candidate_head"],
        "container": {
            "name": "gscore",
            "running": True,
            "image_id": container["Image"],
            "started_at": container["State"]["StartedAt"],
        },
        "backup_path": record["installation"]["backup_path"],
        "active_runtime": runtime,
        "plugin_files_verified": len(record["expected_files"]),
        "preserved": preserved,
        "databases": databases,
        "materials": {
            "prior_files_preserved": len(materials),
            "present_files": len(after["material_files"]),
            "prior_file_hashes_unchanged": True,
        },
        "shutdown": record["shutdown"],
        "startup": logs,
        "database_bytes_verified_unchanged_while_stopped": record["installation"][
            "beforestart_data_and_attempts_unchanged"
        ],
        "privacy": {
            "credentials_or_identity_output": False,
            "raw_logs_output": False,
            "provider_called_by_helper": False,
            "messages_sent_by_helper": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    require(0 <= args.timeout <= 60, "invalid_postflight_timeout")
    record_path, output_path = staging_path(args.record), staging_path(args.output)
    require(not output_path.exists(), "postflight_output_already_exists")
    record = json.loads(record_path.read_text())
    require(record["applied"] and record["installation"]["passed"], "installation_not_applied")
    require(
        record["shutdown"]["shutdown_confirmed"] and not record["shutdown"]["forced_kill"],
        "shutdown_unverified",
    )
    deadline = time.monotonic() + args.timeout
    while True:
        container = inspect_container()
        logs = log_evidence(record["restart_since"])
        if (
            logs["ready_with_subscription_job"]
            or not container["State"]["Running"]
            or time.monotonic() >= deadline
        ):
            break
        time.sleep(min(3, max(0, deadline - time.monotonic())))
    result = check(record, source_snapshot(), container, logs)
    output_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, DeploymentError) else type(error).__name__
        print(json.dumps({"passed": False, "error_category": code, "raw_exception_output": False}))
        sys.exit(1)

"""Verify a target already at the public release without installing or restarting."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deploy_install import (
    CONTAINER,
    EXPECTED_VERSIONS,
    PLUGIN,
    DeploymentError,
    expected_files,
    fingerprint,
    inspect_container,
    require,
    run,
    source_snapshot,
    staging_path,
    validate_candidate,
)


def lifecycle(since):
    process = subprocess.run(
        ["docker", "logs", "--timestamps", "--since", since, "--tail", "5000", CONTAINER],
        capture_output=True,
        text=True,
        timeout=30,
    )
    require(process.returncode == 0, "current_logs_unavailable")
    content = re.sub(r"\x1b\[[0-9;]*m", "", process.stdout + process.stderr)
    evidence = []
    for line in content.splitlines():
        timestamp = re.match(r"([0-9TZ:.-]+)\s", line)
        init = re.search(
            r"Dota2UID initialized state=([a-z_]+) subscriptions_enabled=(True|False) "
            r"job_registered=(True|False)",
            line,
        )
        stop = re.search(
            r"Dota2UID stopped state=([a-z_]+) client_closed=(True|False) "
            r"job_registered=(True|False)",
            line,
        )
        item = init or stop
        if item:
            evidence.append(
                {
                    "timestamp_utc": timestamp.group(1) if timestamp else None,
                    "kind": "initialized" if init else "stopped",
                    "state": item.group(1),
                    "subscriptions_enabled" if init else "client_closed": item.group(2) == "True",
                    "job_registered": item.group(3) == "True",
                }
            )
        elif "Dota2UID" in line and any(
            term in line for term in ("更新", "重载", "reload", "update")
        ):
            evidence.append(
                {
                    "timestamp_utc": timestamp.group(1) if timestamp else None,
                    "kind": "native_plugin_update_or_reload_marker",
                    "raw_log_output": False,
                }
            )
    return evidence


def reflog():
    source = r"""
import json,re,subprocess
process=subprocess.run(['git','-C','/gsuid_core/gsuid_core/plugins/Dota2UID','reflog','--max-count=8','--date=iso-strict','--format=%H%x09%gD%x09%gs'],capture_output=True,text=True)
records=[]
if process.returncode==0:
    for line in process.stdout.splitlines():
        parts=line.split('\t',2)
        if len(parts)!=3 or not re.fullmatch('[0-9a-f]{40}',parts[0]):continue
        stamp=re.search(r'\{([^}]+)\}',parts[1])
        message=parts[2].lower()
        if 'pull' in message and 'fast-forward' in message:
            action='pull_fast_forward'
        elif 'clone' in message:
            action='clone'
        elif 'reset' in message:
            action='reset'
        else:
            action='other'
        records.append({'commit':parts[0],
                        'observed_at':stamp.group(1) if stamp else None,
                        'action':action,'raw_reflog_output':False})
print(json.dumps({'available':process.returncode==0,'records':records}))
"""
    return json.loads(
        run(["docker", "exec", CONTAINER, "/venv/bin/python", "-I", "-B", "-c", source])
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--since", default="2026-10-12T16:00:00Z")
    args = parser.parse_args()
    files = expected_files(staging_path(args.manifest), args.manifest_sha256)
    runtime_digest = validate_candidate(staging_path(args.candidate), files, args.expected_head)
    original = json.loads(staging_path(args.baseline).read_text())["hosts"]["gscore"]
    before = original["audit"]
    container = inspect_container()
    current = source_snapshot()
    require(container["State"]["Running"], "current_container_not_running")
    require(container["Image"] == original["image_id"], "current_image_changed")
    require(current["plugin_head"] == args.expected_head, "current_head_mismatch")
    require(current["plugin_tree"] == fingerprint(files), "current_plugin_files_mismatch")
    runtime = current["active_runtime"]
    require(runtime["versions"] == EXPECTED_VERSIONS, "current_versions_mismatch")
    require(runtime["manifest_sha256"] == runtime_digest, "current_manifest_mismatch")
    require(
        runtime["files_match"] and runtime["complete_matches"], "current_runtime_integrity_failed"
    )
    preserved = {
        "sdk_head": current["sdk_head"] == before["sdk_head"],
        "sdk_tree": current["sdk_tree"] == before["sdk_tree"],
        "global_versions": current["global_versions"] == before["global_versions"],
        "configuration_sha256": current["configuration"]["sha256"]
        == before["configuration"]["sha256"],
        "service_configuration_sha256": current["service_configuration_sha256"]
        == before["service_configuration"]["sha256"],
    }
    require(all(preserved.values()), "current_preservation_failed")
    require(
        current["configuration"]["reply_mode"] == "image"
        and current["configuration"]["subscriptions_enabled"]
        and current["configuration"]["token_configured"],
        "current_configuration_not_ready",
    )
    databases = {}
    for name, value in current["databases"].items():
        old = before["databases"][name]
        require(value["schema_version"] == old["schema_version"], "current_database_schema_changed")
        require(value["counts"] == old["counts"], "current_database_counts_changed")
        databases[name] = {
            "schema_version": value["schema_version"],
            "counts": value["counts"],
            "counts_match_baseline": True,
            "current_table_sha256": value["table_sha256"],
            "current_files_sha256": value["files_sha256"],
        }
    events = lifecycle(args.since)
    ready = [
        item
        for item in events
        if item["kind"] == "initialized"
        and item["state"] == "ready"
        and item["subscriptions_enabled"]
        and item["job_registered"]
    ]
    require(bool(ready), "current_ready_job_not_observed")
    business_events = [item for item in events if item["kind"] in {"initialized", "stopped"}]
    require(business_events[-1] == ready[-1], "current_latest_lifecycle_not_ready")
    result = {
        "schema_version": 1,
        "passed": True,
        "already_current": True,
        "manual_apply_performed": False,
        "manual_stop_or_restart_performed": False,
        "manual_backup_created_by_verification_helper": False,
        "production_read_only": True,
        "plugin": {
            "path": str(PLUGIN),
            "head": current["plugin_head"],
            "expected_public_head": args.expected_head,
            "files_verified": len(files),
            "tree": current["plugin_tree"],
        },
        "container": {
            "running": True,
            "image_id": container["Image"],
            "started_at": container["State"]["StartedAt"],
            "started_at_matches_baseline": container["State"]["StartedAt"]
            == original["started_at"],
        },
        "active_runtime": runtime,
        "preserved": preserved,
        "databases": databases,
        "materials": {
            "present_image_files": len(current["material_files"]),
            "current_files_fingerprint": fingerprint(current["material_files"]),
            "baseline_file_hashes_available": False,
        },
        "python_libraries": {
            "current_fingerprint": current["python_libraries"],
            "current_pillow_native": current["pillow_native"],
            "baseline_file_hashes_available": False,
        },
        "lifecycle_evidence": events,
        "plugin_reflog": reflog(),
        "update_actor": "unknown",
        "proof_limits": [
            "Preflight contains database schema/counts, not prior row/file hashes.",
            "Preflight contains library versions and SDK tree, "
            "not prior library/material file hashes.",
            "No manual cold-deployment backup or shutdown record was created by this helper.",
        ],
        "privacy": {
            "credentials_or_identity_output": False,
            "raw_logs_output": False,
            "raw_reflog_output": False,
            "provider_called_by_helper": False,
            "messages_sent_by_helper": False,
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, DeploymentError) else type(error).__name__
        print(json.dumps({"passed": False, "error_category": code, "raw_exception_output": False}))
        sys.exit(1)

"""Read-only, sanitized audit of the existing remote bot containers."""

import json
import subprocess

GSCORE_AUDIT = r"""
import hashlib, importlib.metadata as metadata, json, pathlib, sqlite3, subprocess, sys

root = pathlib.Path("/gsuid_core")
plugin = root / "gsuid_core/plugins/Dota2UID"
data = root / "data/Dota2UID"


def version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_tree(folder, exclude=()):
    files = {
        p.relative_to(folder).as_posix(): sha(p)
        for p in folder.rglob("*")
        if p.is_file() and not any(part in exclude for part in p.relative_to(folder).parts)
    }
    return {
        "files": len(files),
        "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    }


configuration = data / "config.json"
raw = json.loads(configuration.read_text()) if configuration.exists() else {}


def field(name):
    value = raw.get(name)
    return value.get("data") if isinstance(value, dict) else value


databases = {}
for name, tables in (
    ("bindings.sqlite3", ("bindings",)),
    ("subscriptions.sqlite3", ("subscriptions", "subscription_events", "subscription_attempts")),
):
    path = data / name
    record = {"exists": path.exists()}
    if path.exists():
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        record["schema_version"] = connection.execute("PRAGMA user_version").fetchone()[0]
        record["counts"] = {
            table: connection.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for table in tables
        }
        connection.close()
    databases[name] = record
runtime = data / "runtime"
active_path = runtime / "active.json"
active = json.loads(active_path.read_text()) if active_path.exists() else None
active_record = {"exists": active is not None}
if active is not None:
    generation = runtime / active["manifest_sha256"] / active["generation"]
    marker = json.loads((generation / ".complete.json").read_text())
    active_record.update(
        {
            "versions": active.get("versions"),
            "manifest_sha256": active["manifest_sha256"],
            "generation_file_count": len(marker["files"]),
            "generation_files_match": all(
                sha(generation / path) == digest for path, digest in marker["files"].items()
            ),
            "generation_complete_manifest_matches": marker["manifest_sha256"]
            == active["manifest_sha256"],
        }
    )
service = root / "data/plugins_configs/Dota2UID.json"
print(
    json.dumps(
        {
            "python": sys.version.split()[0],
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
            "sdk_head": subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip(),
            "sdk_tree": digest_tree(root / "gsuid_core", ("plugins", "__pycache__")),
            "plugin_head": subprocess.check_output(
                ["git", "-C", str(plugin), "rev-parse", "HEAD"], text=True
            ).strip(),
            "plugin_tree": digest_tree(plugin, (".git", "__pycache__")),
            "plugin_status_changes": len(
                subprocess.check_output(
                    ["git", "-C", str(plugin), "status", "--porcelain", "--untracked-files=no"],
                    text=True,
                ).splitlines()
            ),
            "release": json.loads((plugin / "release.json").read_text()),
            "configuration": {
                "exists": configuration.exists(),
                "sha256": sha(configuration) if configuration.exists() else None,
                "token_configured": bool(field("stratz_token")),
                "reply_mode": field("reply_mode"),
                "subscriptions_enabled": field("subscriptions_enabled"),
                "subscription_interval_seconds": field("subscription_interval_seconds"),
                "asset_download_mode": field("asset_download_mode"),
            },
            "databases": databases,
            "service_configuration": {
                "exists": service.exists(),
                "sha256": sha(service) if service.exists() else None,
            },
            "active_runtime": active_record,
            "runtime_top_files": sorted(p.name for p in runtime.iterdir())
            if runtime.is_dir()
            else [],
            "data_owner_uid": data.stat().st_uid,
            "data_owner_gid": data.stat().st_gid,
            "plugin_owner_uid": plugin.stat().st_uid,
            "plugin_owner_gid": plugin.stat().st_gid,
            "privacy": {
                "credentials_or_identity_output": False,
                "sdk_or_business_imported": False,
                "provider_called": False,
                "messages_sent": False,
                "production_mutations": False,
            },
        }
    )
)
"""


ASTRBOT_AUDIT = r"""
import importlib.metadata as metadata, json, pathlib, sys

root = pathlib.Path("/AstrBot")
data = root / "data"
plugin = data / "plugins/astrbot_plugin_dota2forge"


def version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


print(
    json.dumps(
        {
            "python": sys.version.split()[0],
            "global_versions": {
                name: version(name)
                for name in (
                    "astrbot",
                    "httpx",
                    "pillow",
                    "dota2forge-core",
                    "dota2forge-renderer",
                    "dota2forge-assets",
                    "astrbot-plugin-dota2forge",
                )
            },
            "source_version_lines": [
                line
                for line in (root / "pyproject.toml").read_text().splitlines()
                if line.startswith("version")
            ],
            "dota2forge_plugin_exists": plugin.exists(),
            "dota2forge_related_data_exists": any(
                "dota" in p.name.lower() for p in (data / "plugin_data").iterdir()
            ),
            "gscore_adapter_plugin_exists": (
                data / "plugins/astrbot_plugin_gscore_adapter"
            ).is_dir(),
            "privacy": {
                "credentials_or_identity_output": False,
                "sdk_or_business_imported": False,
                "provider_called": False,
                "messages_sent": False,
                "production_mutations": False,
            },
        }
    )
)
"""


def main():
    result = {"schema_version": 1, "read_only": True, "hosts": {}}
    for name, python, script in (
        ("gscore", "/venv/bin/python", GSCORE_AUDIT),
        ("astrbot", "python", ASTRBOT_AUDIT),
    ):
        container = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
        process = subprocess.run(
            ["docker", "exec", name, python, "-B", "-c", script],
            capture_output=True,
            text=True,
        )
        result["hosts"][name] = {
            "state": container["State"]["Status"],
            "started_at": container["State"]["StartedAt"],
            "image_id": container["Image"],
            "image": container["Config"]["Image"],
            "working_dir": container["Config"]["WorkingDir"],
            "mounts": [
                {key: mount.get(key) for key in ("Type", "Source", "Destination", "Name")}
                for mount in container["Mounts"]
            ],
            "audit_exit_code": process.returncode,
            "audit": json.loads(process.stdout) if process.returncode == 0 else None,
            "error_category": None if process.returncode == 0 else "metadata_preflight_failed",
        }
    result["passed"] = all(host["audit_exit_code"] == 0 for host in result["hosts"].values())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

"""Disposable real GsCore source, synthetic settings, no network or chat connections."""

import asyncio
import base64
import csv
import hashlib
import importlib.metadata as metadata
import io
import json
import socket
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

host, candidate, output = map(lambda value: Path(value).resolve(), sys.argv[1:4])
plugin = host / "gsuid_core/plugins/Dota2UID"
data = host / "data/Dota2UID"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, str(host))
sys.path.append(str(host / "gsuid_core"))
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


def denied(*args, **kwargs):
    raise AssertionError("External network disabled")


socket.socket.connect = denied
socket.socket.connect_ex = denied
socket.socket.sendto = denied
socket.getaddrinfo = denied


def load_sdk():
    from gsuid_core import server
    from gsuid_core.aps import scheduler
    from gsuid_core.gss import gss
    from gsuid_core.sv import SL
    from gsuid_core.utils.plugins_config.gs_config import all_config_list
    from gsuid_core.utils.plugins_update.reload_plugin import _plugin_start_tasks, reload_plugin

    return server, gss, scheduler, SL, all_config_list, _plugin_start_tasks, reload_plugin


server, gss, scheduler, SL, all_config_list, _plugin_start_tasks, reload_plugin = load_sdk()


def ledger():
    return {
        p.relative_to(host / "gsuid_core").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (host / "gsuid_core").rglob("*.py")
        if "plugins" not in p.relative_to(host / "gsuid_core").parts
    }


def entry():
    return sys.modules["plugins.Dota2UID"]


def data_digest():
    return {
        name: hashlib.sha256((data / name).read_bytes()).hexdigest()
        for name in ("config.json", "bindings.sqlite3", "subscriptions.sqlite3")
        if (data / name).exists()
    }


def stage_next_core_fixture():
    """Build a different valid test wheel without modifying any release or source."""
    manifest = json.loads((plugin / "runtime-wheels.json").read_bytes())
    release = json.loads((plugin / "release.json").read_bytes())
    current = release["versions"]["dota2forge-core"]
    following = "0.1.0a8"
    old_info = f"dota2forge_core-{current}.dist-info"
    new_info = f"dota2forge_core-{following}.dist-info"
    wheel = plugin / "runtime-wheels" / manifest["wheels"]["dota2forge-core"]["filename"]
    with ZipFile(wheel) as packed:
        files = {name.replace(old_info, new_info): packed.read(name) for name in packed.namelist()}
    files[f"{new_info}/METADATA"] = files[f"{new_info}/METADATA"].replace(
        f"Version: {current}\n".encode(), f"Version: {following}\n".encode()
    )
    files["dota2forge_core/__init__.py"] += b'\nHOT_UPDATE_CANARY = "synthetic-next-core"\n'
    record_path = f"{new_info}/RECORD"
    files.pop(record_path)
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, body in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
        writer.writerow((name, "sha256=" + digest, len(body)))
    writer.writerow((record_path, "", ""))
    files[record_path] = record.getvalue().encode()
    filename = f"dota2forge_core-{following}-py3-none-any.whl"
    target = plugin / "runtime-wheels" / filename
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as packed:
        for name, body in sorted(files.items()):
            packed.writestr(name, body)
    manifest["wheels"]["dota2forge-core"] = {
        "filename": filename,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    release["versions"]["dota2forge-core"] = following
    (plugin / "release.json").write_text(json.dumps(release), "utf-8")
    (plugin / "runtime-wheels.json").write_text(json.dumps(manifest), "utf-8")


async def reload():
    result = reload_plugin("Dota2UID")
    assert not result.lstrip().startswith("❌"), result
    pending = _plugin_start_tasks.get("Dota2UID")
    assert pending is not None
    await pending
    return entry()


async def check():
    before = ledger()
    server.auto_install_dep = False
    server.auto_update_dep = False
    modules = gss.load_plugin(plugin)
    assert isinstance(modules, list) and len(modules) == 1
    name, path, kind = modules[0]
    assert name == "plugins.Dota2UID"
    gss.cached_import(name, path, kind)
    initial = entry()
    await initial.start_dota2uid()
    assert initial.owner.status()["business_state"] == "awaiting_config", initial.owner.status()
    config = all_config_list["Dota2UID"]
    config.set_config("stratz_token", "synthetic-hot-update-token")
    config.set_config("subscriptions_enabled", True)
    configured = await reload()
    assert configured.owner.status()["business_state"] == "ready", configured.owner.status()
    assert initial.owner.business.runtime.state.value == "stopped"
    assert scheduler.get_job("Dota2UID-subscriptions") is not None
    runtime = configured.owner.business.runtime
    commands = sys.modules["Dota2UID.commands"]
    caller = commands.Caller("onebot", "synthetic-bot", "synthetic-user", "synthetic-connection")
    assert "绑定已保存" in (await runtime.handle(caller, "do绑定", "42"))[0]
    preserved = data_digest()
    original_generation = configured.owner.active_manager.generation
    original_class = type(runtime)
    # The disposable next wheel has a new version and executable canary. It is
    # solely a synthetic update fixture, never a released project artifact.
    stage_next_core_fixture()
    manifest = plugin / "runtime-wheels.json"
    deployment = plugin / "deployment.json"
    payload = json.loads(deployment.read_bytes())
    payload["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    deployment.write_text(json.dumps(payload), "utf-8")
    sending_entered, cancellation_entered, sending_release = (
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )

    async def synthetic_transport(reply):
        sending_entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancellation_entered.set()
            await sending_release.wait()
            raise

    sending = asyncio.create_task(runtime.dispatch(caller, "do菜单", "", synthetic_transport))
    await sending_entered.wait()
    updating = asyncio.create_task(reload())
    await asyncio.wait_for(cancellation_entered.wait(), 20)
    assert not updating.done() and not runtime._close_task.done()
    assert entry().owner.status()["state"] == "switching"
    assert entry().owner.status()["business_state"] == "stopping"
    assert entry().owner.status()["client_closed"] is False
    sending_release.set()
    updated = await updating
    await asyncio.gather(sending, return_exceptions=True)
    status = updated.owner.status()
    assert status["business_state"] == "ready" and status["switch_state"] == "idle", status
    assert updated.owner.active_manager.generation != original_generation
    assert type(updated.owner.business.runtime) is not original_class
    assert sys.modules["dota2forge_core"].HOT_UPDATE_CANARY == "synthetic-next-core"
    assert runtime.state.value == "stopped" and runtime.client_closed
    assert data_digest() == preserved
    import httpx
    from gsuid_core.webconsole import plugins_api  # noqa: F401
    from gsuid_core.webconsole.app_app import app
    from gsuid_core.webconsole.session_store import session_store

    def headers(role):
        bearer = session_store.create(
            {
                "id": "synthetic-hot-" + role,
                "email": role + "@synthetic.invalid",
                "name": "Synthetic " + role,
                "role": role,
                "avatar": None,
            }
        )
        return {"Authorization": "Bearer " + bearer}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://sdk"
    ) as client:
        assert (await client.get("/api/dota2uid/status")).status_code == 401
        assert (await client.post("/api/dota2uid/stop")).status_code == 401
        assert (
            await client.get("/api/dota2uid/status", headers=headers("user"))
        ).status_code == 403
        assert (
            await client.get("/api/dota2uid/status", headers=headers("admin"))
        ).status_code == 200
    for root in ("Dota2UID", "dota2forge_core", "dota2forge_renderer", "dota2forge_assets"):
        assert (
            Path(sys.modules[root].__file__)
            .resolve()
            .is_relative_to(updated.owner.active_manager.generation.resolve())
        )
    assert SL.lst["Dota2UID账号与查询"].self_plugin_name == "Dota2UID"
    assert len(all_config_list["Dota2UID"].config) == 11
    assert sum(job.id == "Dota2UID-subscriptions" for job in scheduler.get_jobs()) == 1
    assert (
        sum(getattr(h.func, "__module__", "") == "plugins.Dota2UID" for h in server.core_start_def)
        == 1
    )
    # Invalid wheel preparation must restore old business registration after the
    # host has removed it, retaining the last proven active generation.
    stable_runtime = updated.owner.business.runtime
    stable_generation = updated.owner.active_manager.generation
    broken = json.loads(manifest.read_bytes())
    first = next(iter(broken["wheels"].values()))
    first["sha256"] = "0" * 64
    manifest.write_text(json.dumps(broken), "utf-8")
    payload["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    deployment.write_text(json.dumps(payload), "utf-8")
    failed = await reload()
    assert failed.owner.switch_state == "retained", failed.owner.status()
    assert failed.owner.business.runtime is stable_runtime and not stable_runtime.client_closed
    assert failed.owner.active_manager.generation == stable_generation
    assert "do绑定" in [
        str(key) for group in SL.lst["Dota2UID账号与查询"].TL.values() for key in group
    ]
    assert len(scheduler.get_jobs()) == 1
    assert data_digest() == preserved
    await failed.stop_dota2uid()
    assert stable_runtime.client_closed and scheduler.get_job("Dota2UID-subscriptions") is None
    assert ledger() == before
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "passed": True,
                "python": sys.version.split()[0],
                "sdk_metadata_version": metadata.version("gsuid-core"),
                "pillow_version": metadata.version("pillow"),
                "source_files_checked": len(before),
                "sdk_source_unchanged": True,
                "sdk_functions_replaced": False,
                "external_network_disabled": True,
                "real_chat_or_production_modified": False,
                "candidate_versions": updated.owner.active_manager.versions,
                "cold_awaiting_config": True,
                "live_configuration_reload_ready": True,
                "native_generation_reload_ready": True,
                "new_runtime_type_and_four_module_origins": True,
                "new_core_code_canary_verified": True,
                "native_reload_waits_for_active_send_cancellation_cleanup": True,
                "native_api_401_403_admin_status": True,
                "configuration_binding_subscription_hashes_preserved": True,
                "unique_config_command_hook_scheduler_registration": True,
                "failed_preparation_retains_live_runtime_and_restores_registration": True,
                "final_shutdown_drained": True,
                "upgrade_fixture": (
                    "disposable synthetic Core a7-to-a8 wheel with an executable canary; "
                    "derived from canonical wheel, never a public release"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "utf-8",
    )
    print("Real SDK isolated native reload validation passed.")


try:
    loop.run_until_complete(check())
finally:
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.run_until_complete(loop.shutdown_default_executor())
    loop.close()

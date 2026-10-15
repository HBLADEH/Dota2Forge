"""M0 packaging contracts, not claims about host plugin compatibility."""

import importlib
import importlib.metadata
import importlib.util
from importlib.resources import files
from pathlib import Path

import pytest
from packaging.requirements import Requirement


@pytest.mark.parametrize(
    ("distribution", "module"),
    [
        ("dota2forge-core", "dota2forge_core"),
        ("astrbot-plugin-dota2forge", "astrbot_plugin_dota2forge"),
        ("dota2uid", "Dota2UID"),
        ("dota2forge-renderer", "dota2forge_renderer"),
        ("dota2forge-assets", "dota2forge_assets"),
    ],
)
def test_workspace_package_installed(distribution, module):
    assert importlib.import_module(module).__doc__
    assert importlib.metadata.version(distribution) == (
        {
            "astrbot-plugin-dota2forge": "0.1.0a14",
            "dota2uid": "0.1.0a16",
            "dota2forge-core": "0.1.0a9",
            "dota2forge-renderer": "0.1.0a8",
            "dota2forge-assets": "0.1.0a1",
        }.get(distribution, "0.1.0a4")
    )


@pytest.mark.parametrize("distribution", ["astrbot-plugin-dota2forge", "dota2uid"])
def test_feature_renderer_consumers_reject_the_previous_public_renderer(distribution):
    requirements = [Requirement(value) for value in importlib.metadata.requires(distribution) or ()]
    renderer = next(value for value in requirements if value.name == "dota2forge-renderer")
    assert not renderer.specifier.contains("0.1.0a7", prereleases=True)
    assert renderer.specifier.contains("0.1.0a8", prereleases=True)
    core = next(value for value in requirements if value.name == "dota2forge-core")
    assert not core.specifier.contains("0.1.0a8", prereleases=True)
    assert core.specifier.contains("0.1.0a9", prereleases=True)


def test_astrbot_development_bridge_declares_matching_local_components():
    host = files("astrbot_plugin_dota2forge").joinpath("host")
    requirements = {
        requirement.name: requirement
        for line in host.joinpath("requirements.txt").read_text("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        for requirement in [Requirement(line)]
    }
    for name in (
        "astrbot-plugin-dota2forge",
        "dota2forge-core",
        "dota2forge-renderer",
        "dota2forge-assets",
    ):
        assert str(requirements[name].specifier) == "==" + importlib.metadata.version(name)
    assert "version: 0.1.0-alpha.14\n" in host.joinpath("metadata.yaml").read_text("utf-8")


def test_core_keeps_http_optional_and_has_no_host_sdks():
    requirements = importlib.metadata.requires("dota2forge-core")
    assert requirements is not None and 1 <= len(requirements) <= 2
    dependencies = [Requirement(value) for value in requirements]
    assert {dependency.name for dependency in dependencies} == {"httpx"}
    assert all(dependency.marker is not None for dependency in dependencies)
    enabled_extras = {
        extra
        for dependency in dependencies
        for extra in ("stratz", "opendota")
        if dependency.marker.evaluate({"extra": extra})
    }
    assert "stratz" in enabled_extras
    assert enabled_extras <= {"stratz", "opendota"}
    assert importlib.util.find_spec("astrbot") is None
    assert importlib.util.find_spec("gsuid_core") is None


def test_network_is_disabled():
    import socket

    from pytest_socket import SocketBlockedError

    with pytest.warns(UserWarning, match="socket.socket"), pytest.raises(SocketBlockedError):
        socket.socket()


def test_distribution_licenses_match_project_license():
    root = Path(__file__).resolve().parents[1]
    expected = (root / "LICENSE").read_text()
    for folder in [
        "packages/dota2forge-core",
        "packages/dota2forge-renderer",
        "packages/dota2forge-assets",
        "adapters/astrbot_plugin_dota2forge",
        "adapters/Dota2UID",
    ]:
        assert (root / folder / "LICENSE").read_text() == expected

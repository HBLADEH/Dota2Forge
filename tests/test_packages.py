"""M0 packaging contracts, not claims about host plugin compatibility."""

import importlib
import importlib.metadata
import importlib.util
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
    ],
)
def test_workspace_package_installed(distribution, module):
    assert importlib.import_module(module).__doc__
    assert importlib.metadata.version(distribution) == (
        "0.1.0a6" if distribution == "astrbot-plugin-dota2forge" else "0.1.0a4"
    )


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
        "adapters/astrbot_plugin_dota2forge",
        "adapters/Dota2UID",
    ]:
        assert (root / folder / "LICENSE").read_text() == expected

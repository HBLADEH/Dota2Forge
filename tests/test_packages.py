"""M0 packaging contracts, not claims about host plugin compatibility."""

import importlib
import importlib.metadata
import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("distribution", "module"),
    [
        ("dota2forge-core", "dota2forge_core"),
        ("astrbot-plugin-dota2forge", "astrbot_plugin_dota2forge"),
        ("dota2uid", "Dota2UID"),
    ],
)
def test_workspace_package_installed(distribution, module):
    assert importlib.import_module(module).__doc__
    assert importlib.metadata.version(distribution) == "0.1.0a1"


def test_core_has_no_runtime_dependencies_or_host_sdks():
    assert importlib.metadata.requires("dota2forge-core") is None
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
        "adapters/astrbot_plugin_dota2forge",
        "adapters/Dota2UID",
    ]:
        assert (root / folder / "LICENSE").read_text() == expected

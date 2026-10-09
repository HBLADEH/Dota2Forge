"""Path containment keeps its guards during Windows directory creation races."""

import sys
from pathlib import PureWindowsPath

import pytest
from dota2forge_assets import AssetError
from dota2forge_assets.validation import _windows_namespace, safe_path


@pytest.mark.parametrize(
    "ordinary,extended",
    [
        (r"C:\assets\ranks\1.png", r"\\?\C:\assets\ranks\1.png"),
        (r"c:\assets\ranks\1.png", r"\\?\c:\assets\ranks\1.png"),
        (r"\\server\share\assets\ranks\1.png", r"\\?\UNC\server\share\assets\ranks\1.png"),
        (r"\\server\share\assets\ranks\1.png", r"\\?\unc\server\share\assets\ranks\1.png"),
    ],
)
def test_windows_ordinary_and_extended_paths_use_the_same_namespace(ordinary, extended):
    assert PureWindowsPath(_windows_namespace(extended)) == PureWindowsPath(ordinary)
    assert _windows_namespace(ordinary) == ordinary


@pytest.mark.parametrize(
    "device",
    [
        r"\\?\GLOBALROOT\Device\HarddiskVolume1\assets",
        r"\\?\Volume{synthetic}\assets",
        r"\\.\C:\assets",
        r"\\.\PIPE\synthetic",
        r"\??\C:\assets",
        r"\\?\C:assets",
        r"\\?\UNC\.\share\assets",
        r"\\?\UNC\server\..\assets",
        r"\\?\UNC\server",
    ],
)
def test_windows_device_and_malformed_namespaces_are_rejected(device):
    with pytest.raises(AssetError, match="path"):
        _windows_namespace(device)


def test_safe_path_keeps_relative_escape_rejection(tmp_path):
    with pytest.raises(AssetError, match="path"):
        safe_path(tmp_path, "../outside/image.png")


@pytest.mark.parametrize("position", ["root", "parent", "file"])
def test_safe_path_keeps_symbolic_link_rejection(tmp_path, position):
    root = tmp_path / "root"
    root.mkdir()
    target = root / "target"
    target.mkdir()
    (target / "image.png").write_bytes(b"synthetic")
    if position == "root":
        link = tmp_path / "linked-root"
        destination, is_directory = root, True
        checked_root, relative = link, "target/image.png"
    elif position == "parent":
        link = root / "linked-parent"
        destination, is_directory = target, True
        checked_root, relative = root, "linked-parent/image.png"
    else:
        link = root / "linked-file.png"
        destination, is_directory = target / "image.png", False
        checked_root, relative = root, "linked-file.png"
    try:
        link.symlink_to(destination, target_is_directory=is_directory)
    except OSError:
        pytest.skip("Symbolic links require unavailable host permissions")
    with pytest.raises(AssetError, match="path"):
        safe_path(checked_root, relative)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows GetFinalPathName race")
def test_windows_parent_creation_during_resolve_keeps_containment(tmp_path, monkeypatch):
    import ntpath

    target = tmp_path / "ranks/1.png"
    original = ntpath._getfinalpathname
    injected = False
    errors = []

    def create_parent_after_first_resolution_failure(path):
        nonlocal injected
        is_target = ntpath.normcase(str(path)) == ntpath.normcase(str(target))
        if is_target and not injected:
            injected = True
            try:
                return original(path)
            except OSError as error:
                assert error.winerror == 3
                errors.append(error.winerror)
                target.parent.mkdir()
                raise
        try:
            return original(path)
        except OSError as error:
            if is_target:
                errors.append(error.winerror)
            raise

    monkeypatch.setattr(ntpath, "_getfinalpathname", create_parent_after_first_resolution_failure)
    assert safe_path(tmp_path, "ranks/1.png") == target
    assert target.parent.is_dir() and not target.exists()
    assert errors[0] == 3 and 2 in errors[1:]
    assert target.resolve().is_relative_to(tmp_path.resolve())

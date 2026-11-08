"""Headless regression tests for Linux GUI setup and Debian packaging."""

from __future__ import annotations

import importlib.util
import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[5]
GUI_FILE = ROOT / "deployment/linux/installer/gui/installer.py"
DEB_BUILDER = ROOT / "deployment/linux/installer/gui/build-gui-deb.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gui():
    return load_module(GUI_FILE, "careqflow_gtk_setup_test")


def test_gui_import_does_not_require_gtk(gui):
    assert callable(gui.build_command)
    assert callable(gui.main)


@pytest.mark.parametrize("operation", ("install", "upgrade", "repair", "rollback", "uninstall"))
def test_local_only_and_non_network_operations(gui, operation):
    command = gui.build_command(operation, "LocalOnly", "")
    assert command[:3] == ["sudo", "bash", str(gui.INSTALL_SCRIPT)]
    assert command[3] == operation
    if operation in {"rollback", "uninstall"}:
        assert len(command) == 4
    else:
        assert command[-2:] == ["--network-mode", "LocalOnly"]


@pytest.mark.parametrize("operation", ("upgrade", "repair"))
def test_existing_network_is_preserved(gui, operation):
    assert len(gui.build_command(operation, "Preserve", "")) == 4


@pytest.mark.parametrize(
    ("mode", "address", "expected"),
    (
        ("SecureLan", "192.168.1.20", "https://192.168.1.20"),
        ("SecureLan", "10.0.1.2", "https://10.0.1.2"),
        ("Tailscale", "100.126.8.9", "https://100.126.8.9"),
    ),
)
def test_network_address_validation(gui, mode, address, expected):
    assert gui.build_command("install", mode, address)[-1] == expected


@pytest.mark.parametrize(
    ("mode", "address"),
    (
        ("SecureLan", "8.8.8.8"),
        ("Tailscale", "192.168.1.20"),
        ("SecureLan", "https://192.168.1.20"),
        ("SecureLan", "abc"),
    ),
)
def test_invalid_network_address_is_rejected(gui, mode, address):
    with pytest.raises(ValueError):
        gui.build_command("install", mode, address)


def test_invalid_operations_and_missing_network_selection(gui):
    for operation, mode in (("other", "LocalOnly"), ("install", "Preserve")):
        with pytest.raises(ValueError):
            gui.build_command(operation, mode, "")


@pytest.mark.parametrize("code", (0, 1, 13, 255))
def test_installer_exit_code(gui, code):
    assert gui.parse_installer_result(f" {code}\n") == code


@pytest.mark.parametrize("value", ("", "-1", "256", "failed", "1\n2", "١"))
def test_invalid_exit_code_is_rejected(gui, value):
    with pytest.raises(ValueError):
        gui.parse_installer_result(value)


@pytest.mark.parametrize(
    ("pid", "alive", "terminal_return", "elapsed", "expected"),
    (
        (123, True, None, 30, False),
        (123, False, None, 30, True),
        (None, False, 1, 0, True),
        (None, False, 0, 4, False),
        (None, False, 0, 8, True),
    ),
)
def test_installer_interruption_signals(
    gui, pid, alive, terminal_return, elapsed, expected
):
    assert gui.interruption_detected(
        worker_pid=pid,
        worker_alive=alive,
        terminal_return=terminal_return,
        elapsed=elapsed,
    ) is expected


def test_installer_detection_handles_permission_denied(gui, tmp_path):
    with (
        patch.object(gui, "INSTALL_STATE", tmp_path / "restricted"),
        patch.object(gui, "INSTALL_DIRECTORY", tmp_path),
        patch.object(Path, "is_file", side_effect=PermissionError("restricted")),
    ):
        title, description = gui.detect_installation()
    assert title == "Existing installation detected"
    assert "privileged installer" in description


def test_deb_builder_and_gui_are_in_module_folder():
    assert DEB_BUILDER.is_file()
    assert GUI_FILE.is_file()


def build_test_archive(path: Path) -> None:
    content = {
        "carequeue-release.env": (
            b"CAREQUEUE_RELEASE_METADATA_SCHEMA=1\n"
            b"CAREQUEUE_APP_VERSION=0.7.1\n"
            b"CAREQUEUE_PACKAGE_PLATFORM=linux\n"
        ),
        "LICENSE": b"Test license\n",
        "LICENSES/BUSL-1.1.txt": b"Test license\n",
        "backend/requirements.txt": b"fastapi\n",
        "frontend/dist/index.html": b"<html></html>\n",
        "deployment/linux/installer/gui/installer.py": GUI_FILE.read_bytes(),
        "deployment/linux/installer/invoke-install.sh": b"#!/bin/bash\n",
        "deployment/linux/install-production.sh": b"#!/bin/bash\n",
    }
    with tarfile.open(path, "w:gz") as tar:
        for name, data in content.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))


@pytest.mark.skipif(shutil.which("dpkg-deb") is None, reason="Debian tooling not installed")
def test_deb_package_contents_and_dependencies(tmp_path):
    archive = tmp_path / "release.tar.gz"
    build_test_archive(archive)
    result = subprocess.run(
        [sys.executable, str(DEB_BUILDER), str(archive), "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Created" in result.stdout
    deb = tmp_path / "CareQFlow-Setup-GUI_0.7.1_all.deb"
    assert deb.is_file()
    listing = subprocess.run(
        ["dpkg-deb", "--contents", str(deb)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "usr/bin/careqflow-setup" in listing
    assert "usr/share/applications/org.careqflow.Setup.desktop" in listing
    assert "usr/share/careqflow-setup/deployment/linux/installer/gui/installer.py" in listing
    depends = subprocess.run(
        ["dpkg-deb", "--field", str(deb), "Depends"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "python3-gi" in depends
    assert "gir1.2-gtk-4.0" in depends
    for line in listing.splitlines():
        if not line.startswith(("d", "-")):
            continue
        if line.startswith("d"):
            assert line[:10] == "drwxr-xr-x", line
        elif "/usr/bin/careqflow-setup" in line:
            assert line[:10] == "-rwxr-xr-x", line
        else:
            assert line[:10] == "-rw-r--r--", line


@pytest.mark.skipif(shutil.which("dpkg-deb") is None, reason="Debian tooling not installed")
def test_deb_rejects_link_members(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        entry = tarfile.TarInfo("deployment/linux/installer/gui/installer.py")
        entry.type = tarfile.SYMTYPE
        entry.linkname = "/etc/passwd"
        tar.addfile(entry)
    result = subprocess.run(
        [sys.executable, str(DEB_BUILDER), str(archive), "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Unsupported release entry" in result.stderr


def test_excluded_development_artifacts():
    builder = load_module(DEB_BUILDER, "careqflow_deb_exclusions_test")
    for name in (
        "backend/authstatus_api/__pycache__/settings.cpython-314.pyc",
        "deployment/linux/installer/gui/__pycache__/installer.cpython-313.pyc",
        "backend/.pytest_cache/README.md",
        "backend/scripts/temporary.pyo",
        "deployment/linux/.ruff_cache/metadata",
    ):
        assert builder.is_development_artifact(PurePosixPath(name))
    assert not builder.is_development_artifact(
        PurePosixPath("deployment/linux/installer/gui/installer.py")
    )


def test_deb_unpack_filters_caches_and_normalizes_permissions(tmp_path):
    builder = load_module(DEB_BUILDER, "careqflow_deb_cleanup_test")
    archive = tmp_path / "with-caches.tar.gz"
    data = {
        "backend/authstatus_api/main.py": b"print('ok')\n",
        "backend/authstatus_api/__pycache__/main.cpython-314.pyc": b"compiled",
        "backend/authstatus_api/.pytest_cache/README.md": b"test cache",
        "backend/scripts/debug.pyo": b"compiled",
    }
    with tarfile.open(archive, "w:gz") as tar:
        for name, content in data.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o777
            tar.addfile(member, io.BytesIO(content))
    with pytest.raises(ValueError, match="Linux release is missing"):
        builder.unpack_release(archive, tmp_path / "unpacked")
    root = tmp_path / "unpacked"
    assert (root / "backend/authstatus_api/main.py").is_file()
    assert (root / "backend/authstatus_api/main.py").stat().st_mode & 0o777 == 0o644
    assert (root / "backend/authstatus_api").stat().st_mode & 0o777 == 0o755
    assert not (root / "backend/authstatus_api/__pycache__").exists()
    assert not (root / "backend/authstatus_api/.pytest_cache").exists()
    assert not (root / "backend/scripts/debug.pyo").exists()


def test_tar_builder_removes_development_artifacts():
    source = (ROOT / "deployment/linux/installer/build-payload.ps1").read_text(
        encoding="utf-8"
    )
    assert '"__pycache__"' in source
    assert '".pyc"' in source
    assert '".pyo"' in source
    assert '".pytest_cache"' in source
    assert "unsafePayloadFiles" in source

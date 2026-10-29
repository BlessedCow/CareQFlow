from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

LINUX_PACKAGE_BUILDER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "build-payload.ps1"
)


def _read() -> str:
    return LINUX_PACKAGE_BUILDER.read_text(encoding="utf-8")


def test_linux_package_builder_only_copies_linux_deployment():
    content = _read()

    assert '"deployment\\linux"' in content
    assert '"deploymentStagingDirectory"' not in content

    assert ("Join-Path $repositoryRoot " '"deployment"') not in content

    assert ("-Destination $deploymentStagingDirectory") in content


def test_linux_package_builder_does_not_use_tar_for_archive_creation():
    content = _read()

    creation_section = content.split(
        'Write-Host "Creating Linux installer package..."',
        maxsplit=1,
    )[1]

    assert "& tar.exe" not in creation_section
    assert 'tarfile.open(destination, "w:gz")' in creation_section


def test_linux_package_builder_normalizes_archive_permissions():
    content = _read()

    assert "member.mode = 0o755 if member.isdir() else 0o644" in content
    assert "member.uid = 0" in content
    assert "member.gid = 0" in content
    assert 'member.uname = "root"' in content
    assert 'member.gname = "root"' in content


def test_linux_package_builder_rejects_links_and_unsafe_paths():
    content = _read()

    assert "member.issym() or member.islnk()" in content
    assert 'path.is_absolute() or ".." in path.parts' in content
    assert "Unsupported archive entry type" in content


def test_linux_package_builder_verifies_created_archive_modes():
    content = _read()

    assert 'tarfile.open(destination, "r:gz")' in content
    assert "actual_mode = member.mode & 0o777" in content
    assert "actual_mode != expected_mode" in content
    assert "Archive contains a link" in content


LINUX_INSTALLER = PROJECT_ROOT / "deployment" / "linux" / "install-production.sh"


def test_linux_caddy_repository_requires_https_and_scoped_key():
    content = LINUX_INSTALLER.read_text(encoding="utf-8")

    assert "caddy-stable-archive-keyring.gpg" in content
    assert ("https://dl.cloudsmith.io/public/caddy/stable/") in content
    assert "if len(entries) != 1:" in content
    assert 'parts[1] != f"[{expected_key}]"' in content
    assert "parts[2].startswith(expected_url)" in content

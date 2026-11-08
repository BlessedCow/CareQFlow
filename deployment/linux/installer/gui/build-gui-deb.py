"""Build a Debian GTK setup package from a reviewed CareQFlow Linux release tarball."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

PACKAGE_ID = "careqflow-setup-gui"
INSTALL_ROOT = "usr/share/careqflow-setup"
REQUIRED_FILES = (
    "carequeue-release.env",
    "LICENSE",
    "LICENSES/BUSL-1.1.txt",
    "backend/requirements.txt",
    "frontend/dist/index.html",
    "deployment/linux/installer/gui/installer.py",
    "deployment/linux/installer/invoke-install.sh",
    "deployment/linux/install-production.sh",
)
MAX_TOTAL_BYTES = 600 * 1024 * 1024
EXCLUDED_DIRECTORIES = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".venv", "node_modules"}
)
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})


def is_development_artifact(path: PurePosixPath) -> bool:
    """Identify files that must not be installed from a release archive."""
    return bool(EXCLUDED_DIRECTORIES.intersection(path.parts)) or (
        path.suffix in EXCLUDED_SUFFIXES
    )




def unpack_release(archive: Path, destination: Path) -> None:
    """Copy only regular release files and directories, rejecting unsafe entries."""
    seen: set[str] = set()
    total = 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            name = member.name.removeprefix("./").rstrip("/")
            if not name or name == ".":
                continue
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or any(not part or any(ord(c) < 32 for c in part) for part in path.parts)
                or name in seen
            ):
                raise ValueError(f"Unsafe or duplicate release entry: {member.name}")
            seen.add(name)
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported release entry: {member.name}")
            if is_development_artifact(path):
                continue
            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(0o755)
            elif member.isfile():
                total += member.size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("Release payload exceeds the size limit.")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError(f"Missing release content: {member.name}")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)
            else:
                raise ValueError(f"Unsupported release entry: {member.name}")
    for directory in sorted(destination.rglob("*")):
        if directory.is_dir():
            directory.chmod(0o755)
    destination.chmod(0o755)
    for required in REQUIRED_FILES:
        if not (destination / required).is_file():
            raise ValueError(f"Linux release is missing: {required}")


def read_version(release_root: Path) -> str:
    metadata = (release_root / "carequeue-release.env").read_text(encoding="utf-8")
    fields = dict(
        line.split("=", 1)
        for line in metadata.splitlines()
        if line and "=" in line
    )
    if fields.get("CAREQUEUE_RELEASE_METADATA_SCHEMA") != "1":
        raise ValueError("Unsupported Linux release metadata schema.")
    if fields.get("CAREQUEUE_PACKAGE_PLATFORM") != "linux":
        raise ValueError("This archive is not a Linux release.")
    version = fields.get("CAREQUEUE_APP_VERSION", "")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Invalid Linux release version.")
    return version


def write_setup_files(package_root: Path, version: str) -> None:
    control = package_root / "DEBIAN/control"
    control.parent.mkdir(parents=True)
    control.write_text(
        f"Package: {PACKAGE_ID}\n"
        f"Version: {version}\n"
        "Section: utils\nPriority: optional\nArchitecture: all\n"
        "Maintainer: CareQFlow Project\n"
        "Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, "
        "sudo, xterm | gnome-terminal | xfce4-terminal | konsole\n"
        "Description: CareQFlow graphical Linux setup\n"
        " GTK4 installation, repair, upgrade, rollback and uninstall launcher.\n"
        " Clinical application data remains managed by the Linux installer.\n",
        encoding="utf-8",
    )
    control.chmod(0o644)

    launcher = package_root / "usr/bin/careqflow-setup"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "#!/bin/sh\n"
        "exec /usr/bin/python3 "
        "/usr/share/careqflow-setup/deployment/linux/installer/gui/installer.py \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    desktop = package_root / "usr/share/applications/org.careqflow.Setup.desktop"
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=CareQFlow Setup\n"
        "Comment=Install, repair or upgrade CareQFlow\n"
        "Exec=/usr/bin/careqflow-setup\n"
        "Icon=utilities-terminal\n"
        "Terminal=false\n"
        "Categories=System;Utility;\n",
        encoding="utf-8",
    )
    desktop.chmod(0o644)


def build(archive: Path, output_directory: Path) -> Path:
    """Produce an uninstalled Debian setup artifact using dpkg-deb."""
    if shutil.which("dpkg-deb") is None:
        raise RuntimeError("dpkg-deb is required to build the GUI installer.")
    archive = archive.resolve(strict=True)
    output_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="careqflow-deb-") as temp:
        root = Path(temp) / "package"
        release_root = root / INSTALL_ROOT
        release_root.mkdir(parents=True)
        unpack_release(archive, release_root)
        version = read_version(release_root)
        write_setup_files(root, version)
        for directory in root.rglob("*"):
            if directory.is_dir():
                directory.chmod(0o755)
        root.chmod(0o755)
        output = output_directory / f"CareQFlow-Setup-GUI_{version}_all.deb"
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(root), str(output)],
            check=True,
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="CareQFlow-Linux-Setup-*.tar.gz")
    parser.add_argument("--output-dir", type=Path, default=Path("build/linux/installer"))
    args = parser.parse_args()
    try:
        result = build(args.archive, args.output_dir)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"GUI package build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Created {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ARCHIVE_VALIDATOR = PROJECT_ROOT / "deployment" / "validate-source-archive.ps1"


def _read() -> str:
    return ARCHIVE_VALIDATOR.read_text(encoding="utf-8")


def test_source_archive_validator_exists():
    assert ARCHIVE_VALIDATOR.is_file()


def test_source_archive_validator_checks_sensitive_runtime_paths():
    content = _read()

    expected_patterns = (
        "local_backups/",
        "local_vobs/",
        "backend/data/",
        "backend/backups/",
        "backend/restores/",
        "local_installer_assets/",
    )

    for pattern in expected_patterns:
        assert pattern in content


def test_source_archive_validator_checks_secret_and_database_files():
    content = _read()

    assert r"\.env($|\.)" in content
    assert r"\.db$" in content
    assert r"\.sqlite$" in content
    assert r"\.sqlite3$" in content
    assert r"\.db\.enc$" in content


def test_source_archive_validator_rejects_cache_and_environment_content():
    content = _read()

    expected_patterns = (
        "__pycache__/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".venv/",
        "node_modules/",
    )

    for pattern in expected_patterns:
        assert pattern in content


def test_source_archive_validator_normalizes_zip_entry_separators():
    content = _read()

    assert "$entry.FullName -replace '\\\\', '/'" in content


def test_source_archive_validator_reports_forbidden_entries():
    content = _read()

    assert "$forbiddenEntries.Count -gt 0" in content
    assert "Archive contains forbidden local, runtime, or sensitive files" in content


def test_source_archive_validator_allows_environment_templates():
    content = _read()

    assert r"(^|/)\.env\.(example|sample|template)($|\.)" in content
    assert "if ($isEnvironmentTemplate)" in content


def test_source_archive_validator_does_not_block_source_backup_modules():
    content = _read()

    assert "'(^|/)backups/'" not in content
    assert "'(^|/)data/'" not in content
    assert "'(^|/)restores/'" not in content

    assert "'(^|/)backend/backups/'" in content
    assert "'(^|/)backend/data/'" in content
    assert "'(^|/)backend/restores/'" in content

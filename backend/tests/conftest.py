from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def pytest_configure() -> None:
    from authstatus_api.settings import get_settings

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def isolate_test_settings(monkeypatch, tmp_path):
    from authstatus_api import settings as settings_module
    from authstatus_api.settings import get_settings

    monkeypatch.setattr(settings_module, "ROOT_ENV_FILE", tmp_path / ".env")
    monkeypatch.setenv(
        "AUTHSTATUS_APP_ENVIRONMENT",
        "test",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_ENCRYPTION",
        "plaintext",
    )
    monkeypatch.setenv("AUTHSTATUS_SQLCIPHER_KEY", "")
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def assume_current_governance_for_unrelated_tests(
    monkeypatch,
    request,
):
    test_path = Path(str(request.node.path))

    if "governance" in test_path.parts:
        return

    monkeypatch.setattr(
        "authstatus_api.security.dependencies.is_governance_attestation_current",
        lambda: True,
    )

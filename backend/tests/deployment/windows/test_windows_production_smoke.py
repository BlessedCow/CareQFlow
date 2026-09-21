from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

WINDOWS_PRODUCTION_SMOKE = (
    PROJECT_ROOT / "deployment" / "windows" / "Test-CareQFlowProduction.ps1"
)


def _read() -> str:
    return WINDOWS_PRODUCTION_SMOKE.read_text(encoding="utf-8")


def test_windows_production_smoke_uses_installed_paths_and_services():
    content = _read()

    assert '[string]$DataDirectory = "C:\\ProgramData\\CareQueue"' in content
    assert '[string]$InstallDirectory = "C:\\Program Files\\CareQueue"' in content

    assert '$apiServiceName = "CareQueueApi"' in content
    assert '$caddyServiceName = "CareQueueCaddy"' in content
    assert '$backupTaskName = "CareQFlow Encrypted Backup"' in content

    assert '"Config"' in content
    assert '"carequeue.env"' in content
    assert '"install-state.json"' in content
    assert '"Backups"' in content


def test_windows_production_smoke_checks_required_services():
    content = _read()

    assert "Test-ServiceRunning `" in content
    assert "-ServiceName $apiServiceName" in content
    assert '-DisplayName "API service"' in content

    assert "-ServiceName $caddyServiceName" in content
    assert '-DisplayName "HTTPS service"' in content


def test_windows_production_smoke_prefers_packaged_python_runtime():
    content = _read()

    assert '"runtime\\python\\python.exe"' in content
    assert '".venv\\Scripts\\python.exe"' in content

    packaged_index = content.index('"runtime\\python\\python.exe"')
    legacy_index = content.index('".venv\\Scripts\\python.exe"')

    assert packaged_index < legacy_index

    assert "function Get-CareQFlowPythonExecutable {" in content
    assert "return $privatePythonExecutable" in content
    assert "return $legacyPythonExecutable" in content


def test_windows_production_smoke_checks_direct_and_https_health():
    content = _read()

    assert '"http://127.0.0.1:8000/api/health/live"' in content
    assert 'Host = "careqflow.local"' in content

    assert '-Name "Direct loopback API health"' in content
    assert '-Name "HTTPS frontend"' in content
    assert '-Name "HTTPS API liveness"' in content
    assert '-Name "HTTPS API readiness"' in content

    assert '"$applicationOrigin/api/health/live"' in content
    assert '"$applicationOrigin/api/health/ready"' in content

    assert '-ExpectedBodyStatus "ok"' in content


def test_windows_production_smoke_checks_sqlcipher_database():
    content = _read()

    assert "from authstatus_api.persistence.connections import get_conn" in content
    assert "from authstatus_api.settings import get_settings" in content
    assert "get_settings.cache_clear()" in content

    assert "conn.execute('SELECT 1')" in content

    assert "$env:CAREQFLOW_SMOKE_ENV = $environmentFile" in content

    assert '-Name "Production database access"' in content
    assert '"SQLCipher database query succeeded."' in content


def test_windows_production_smoke_checks_backup_directory_and_task():
    content = _read()

    assert '-Name "Backup directory access"' in content

    assert "Get-ScheduledTask `" in content
    assert "-TaskName $backupTaskName" in content
    assert '-Name "Scheduled backup task"' in content

    assert '$_.Name -like "*.enc"' in content
    assert "-Property LastWriteTimeUtc" in content

    assert '-Name "Recent encrypted backup"' in content
    assert "$MaximumBackupAgeHours" in content


def test_windows_production_smoke_limits_backup_age_parameter():
    content = _read()

    assert "[ValidateRange(1, 168)]" in content
    assert "[int]$MaximumBackupAgeHours = 48" in content


def test_windows_production_smoke_checks_log_directories():
    content = _read()

    assert '"Logs\\Api"' in content
    assert '"Logs\\Caddy"' in content

    assert '-Name "API log directory"' in content
    assert '-Name "Caddy log directory"' in content


def test_windows_production_smoke_fails_when_any_check_fails():
    content = _read()

    assert '$_.Result -eq "FAIL"' in content
    assert "$failedResults.Count -gt 0" in content

    assert '"CareQFlow production smoke test FAILED: "' in content
    assert "exit 1" in content


def test_windows_production_smoke_exits_zero_after_success():
    content = _read()

    assert '"CareQFlow production smoke test PASSED."' in content

    passed_message_index = content.index('"CareQFlow production smoke test PASSED."')
    exit_zero_index = content.rindex("exit 0")

    assert passed_message_index < exit_zero_index

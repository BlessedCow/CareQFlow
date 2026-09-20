[CmdletBinding()]
param(
    [string]$DataDirectory = "C:\ProgramData\CareQueue",
    [string]$InstallDirectory = "C:\Program Files\CareQueue",
    [ValidateRange(1, 168)]
    [int]$MaximumBackupAgeHours = 48
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$apiServiceName = "CareQueueApi"
$caddyServiceName = "CareQueueCaddy"
$backupTaskName = "CareQFlow Encrypted Backup"

$configDirectory = Join-Path $DataDirectory "Config"
$environmentFile = Join-Path $configDirectory "carequeue.env"
$installStatePath = Join-Path $configDirectory "install-state.json"
$backupDirectory = Join-Path $DataDirectory "Backups"

$apiLogDirectory = Join-Path $DataDirectory "Logs\Api"
$caddyLogDirectory = Join-Path $DataDirectory "Logs\Caddy"

$backendDirectory = Join-Path $InstallDirectory "backend"
$privatePythonExecutable = Join-Path `
    $InstallDirectory `
    "runtime\python\python.exe"

$legacyPythonExecutable = Join-Path `
    $backendDirectory `
    ".venv\Scripts\python.exe"

$results = [System.Collections.Generic.List[object]]::new()

function Add-SmokeTestResult {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [bool]$Passed,

        [Parameter(Mandatory)]
        [string]$Detail
    )

    $results.Add(
        [pscustomobject]@{
            Check  = $Name
            Result = if ($Passed) { "PASS" } else { "FAIL" }
            Detail = $Detail
        }
    )
}

function Test-ServiceRunning {
    param(
        [Parameter(Mandatory)]
        [string]$ServiceName,

        [Parameter(Mandatory)]
        [string]$DisplayName
    )

    try {
        $service = Get-Service `
            -Name $ServiceName `
            -ErrorAction Stop

        if ($service.Status -eq "Running") {
            Add-SmokeTestResult `
                -Name $DisplayName `
                -Passed $true `
                -Detail "Service is running."
        }
        else {
            Add-SmokeTestResult `
                -Name $DisplayName `
                -Passed $false `
                -Detail "Service status is $($service.Status)."
        }
    }
    catch {
        Add-SmokeTestResult `
            -Name $DisplayName `
            -Passed $false `
            -Detail $_.Exception.Message
    }
}

function Test-WebEndpoint {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$Uri,

        [string]$ExpectedBodyStatus
    )

    try {
        $response = Invoke-WebRequest `
            -Uri $Uri `
            -UseBasicParsing `
            -TimeoutSec 10 `
            -ErrorAction Stop

        if (
            $response.StatusCode -lt 200 `
                -or $response.StatusCode -ge 400
        ) {
            Add-SmokeTestResult `
                -Name $Name `
                -Passed $false `
                -Detail "HTTP status $($response.StatusCode)."

            return
        }

        if ($ExpectedBodyStatus) {
            try {
                $body = $response.Content | ConvertFrom-Json
            }
            catch {
                Add-SmokeTestResult `
                    -Name $Name `
                    -Passed $false `
                    -Detail "Response body was not valid JSON."

                return
            }

            if ($body.status -ne $ExpectedBodyStatus) {
                Add-SmokeTestResult `
                    -Name $Name `
                    -Passed $false `
                    -Detail (
                    "Expected status '$ExpectedBodyStatus' but received " +
                    "'$($body.status)'."
                )

                return
            }
        }

        Add-SmokeTestResult `
            -Name $Name `
            -Passed $true `
            -Detail "HTTP $($response.StatusCode)."
    }
    catch {
        Add-SmokeTestResult `
            -Name $Name `
            -Passed $false `
            -Detail $_.Exception.Message
    }
}

function Get-CareQFlowPythonExecutable {
    if (
        Test-Path `
            -LiteralPath $privatePythonExecutable `
            -PathType Leaf
    ) {
        return $privatePythonExecutable
    }

    if (
        Test-Path `
            -LiteralPath $legacyPythonExecutable `
            -PathType Leaf
    ) {
        return $legacyPythonExecutable
    }

    return $null
}

Write-Host ""
Write-Host "CareQFlow production smoke test"
Write-Host "=============================="
Write-Host ""

if (-not (Test-Path -LiteralPath $installStatePath -PathType Leaf)) {
    Add-SmokeTestResult `
        -Name "Installation state" `
        -Passed $false `
        -Detail "Installation state file was not found at $installStatePath."
}
else {
    try {
        $installState = Get-Content `
            -LiteralPath $installStatePath `
            -Raw `
            -ErrorAction Stop |
        ConvertFrom-Json

        $applicationOrigin = [string]$installState.application_origin
        $installedVersion = [string]$installState.installed_version

        if (
            [string]::IsNullOrWhiteSpace($applicationOrigin) `
                -or [string]::IsNullOrWhiteSpace($installedVersion)
        ) {
            Add-SmokeTestResult `
                -Name "Installation state" `
                -Passed $false `
                -Detail (
                "Installation state is missing the application origin " +
                "or installed version."
            )
        }
        else {
            $applicationOrigin = $applicationOrigin.TrimEnd("/")

            Add-SmokeTestResult `
                -Name "Installation state" `
                -Passed $true `
                -Detail (
                "Version $installedVersion at $applicationOrigin."
            )
        }
    }
    catch {
        $applicationOrigin = $null
        $installedVersion = $null

        Add-SmokeTestResult `
            -Name "Installation state" `
            -Passed $false `
            -Detail $_.Exception.Message
    }
}

Test-ServiceRunning `
    -ServiceName $apiServiceName `
    -DisplayName "API service"

Test-ServiceRunning `
    -ServiceName $caddyServiceName `
    -DisplayName "HTTPS service"

if (
    Test-Path `
        -LiteralPath $environmentFile `
        -PathType Leaf
) {
    Add-SmokeTestResult `
        -Name "Production environment" `
        -Passed $true `
        -Detail "Environment file is present."
}
else {
    Add-SmokeTestResult `
        -Name "Production environment" `
        -Passed $false `
        -Detail "Environment file was not found at $environmentFile."
}

$pythonExecutable = Get-CareQFlowPythonExecutable

if ($null -eq $pythonExecutable) {
    Add-SmokeTestResult `
        -Name "Production Python runtime" `
        -Passed $false `
        -Detail "No installed CareQFlow Python runtime was found."
}
else {
    Add-SmokeTestResult `
        -Name "Production Python runtime" `
        -Passed $true `
        -Detail $pythonExecutable
}

try {
    $directResponse = Invoke-WebRequest `
        -Uri "http://127.0.0.1:8000/api/health/live" `
        -Headers @{
        Host = "careqflow.local"
    } `
        -UseBasicParsing `
        -TimeoutSec 10 `
        -ErrorAction Stop

    if ($directResponse.StatusCode -eq 200) {
        $directBody = $directResponse.Content | ConvertFrom-Json

        if ($directBody.status -eq "ok") {
            Add-SmokeTestResult `
                -Name "Direct loopback API health" `
                -Passed $true `
                -Detail "Loopback API returned status ok."
        }
        else {
            Add-SmokeTestResult `
                -Name "Direct loopback API health" `
                -Passed $false `
                -Detail (
                "Loopback API returned unexpected status " +
                "'$($directBody.status)'."
            )
        }
    }
    else {
        Add-SmokeTestResult `
            -Name "Direct loopback API health" `
            -Passed $false `
            -Detail "HTTP status $($directResponse.StatusCode)."
    }
}
catch {
    Add-SmokeTestResult `
        -Name "Direct loopback API health" `
        -Passed $false `
        -Detail $_.Exception.Message
}

if (-not [string]::IsNullOrWhiteSpace($applicationOrigin)) {
    Test-WebEndpoint `
        -Name "HTTPS frontend" `
        -Uri "$applicationOrigin/"

    Test-WebEndpoint `
        -Name "HTTPS API liveness" `
        -Uri "$applicationOrigin/api/health/live" `
        -ExpectedBodyStatus "ok"

    Test-WebEndpoint `
        -Name "HTTPS API readiness" `
        -Uri "$applicationOrigin/api/health/ready" `
        -ExpectedBodyStatus "ok"
}
else {
    Add-SmokeTestResult `
        -Name "HTTPS frontend" `
        -Passed $false `
        -Detail "Application origin is unavailable."

    Add-SmokeTestResult `
        -Name "HTTPS API liveness" `
        -Passed $false `
        -Detail "Application origin is unavailable."

    Add-SmokeTestResult `
        -Name "HTTPS API readiness" `
        -Passed $false `
        -Detail "Application origin is unavailable."
}

if (
    $null -ne $pythonExecutable `
        -and (
        Test-Path `
            -LiteralPath $environmentFile `
            -PathType Leaf
    )
) {
    try {
$databaseCheckScript = @'
import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(os.environ['CAREQFLOW_SMOKE_ENV'])
load_dotenv(env_path, override=True)

from authstatus_api.persistence.connections import get_conn
from authstatus_api.settings import get_settings

get_settings.cache_clear()

with get_conn() as conn:
    value = conn.execute('SELECT 1').fetchone()[0]

if value != 1:
    raise SystemExit(1)

print('Database query succeeded.')
'@
        $previousSmokeEnvironment = $env:CAREQFLOW_SMOKE_ENV
        $env:CAREQFLOW_SMOKE_ENV = $environmentFile

        Push-Location $backendDirectory

        try {
            $databaseOutput = & $pythonExecutable `
                -c $databaseCheckScript `
                2>&1

            if ($LASTEXITCODE -eq 0) {
                Add-SmokeTestResult `
                    -Name "Production database access" `
                    -Passed $true `
                    -Detail "SQLCipher database query succeeded."
            }
            else {
                Add-SmokeTestResult `
                    -Name "Production database access" `
                    -Passed $false `
                    -Detail (
                    "Database check exited with code " +
                    "$LASTEXITCODE."
                )
            }
        }
        finally {
            Pop-Location

            if ($null -eq $previousSmokeEnvironment) {
                Remove-Item Env:CAREQFLOW_SMOKE_ENV `
                    -ErrorAction SilentlyContinue
            }
            else {
                $env:CAREQFLOW_SMOKE_ENV = $previousSmokeEnvironment
            }
        }
    }
    catch {
        Add-SmokeTestResult `
            -Name "Production database access" `
            -Passed $false `
            -Detail $_.Exception.Message
    }
}

if (
    Test-Path `
        -LiteralPath $backupDirectory `
        -PathType Container
) {
    try {
        Get-ChildItem `
            -LiteralPath $backupDirectory `
            -ErrorAction Stop |
        Out-Null

        Add-SmokeTestResult `
            -Name "Backup directory access" `
            -Passed $true `
            -Detail "Backup directory is accessible."
    }
    catch {
        Add-SmokeTestResult `
            -Name "Backup directory access" `
            -Passed $false `
            -Detail $_.Exception.Message
    }
}
else {
    Add-SmokeTestResult `
        -Name "Backup directory access" `
        -Passed $false `
        -Detail "Backup directory was not found at $backupDirectory."
}

try {
    $backupTask = Get-ScheduledTask `
        -TaskName $backupTaskName `
        -ErrorAction Stop

    Add-SmokeTestResult `
        -Name "Scheduled backup task" `
        -Passed $true `
        -Detail "Scheduled backup task is registered."

    $recentBackup = Get-ChildItem `
        -LiteralPath $backupDirectory `
        -File `
        -ErrorAction Stop |
    Where-Object {
        $_.Name -like "*.enc"
    } |
    Sort-Object `
        -Property LastWriteTimeUtc `
        -Descending |
    Select-Object -First 1

    if ($null -eq $recentBackup) {
        Add-SmokeTestResult `
            -Name "Recent encrypted backup" `
            -Passed $false `
            -Detail "No encrypted backups were found."
    }
    else {
        $backupAge = (
            [DateTime]::UtcNow - $recentBackup.LastWriteTimeUtc
        )

        if ($backupAge.TotalHours -le $MaximumBackupAgeHours) {
            Add-SmokeTestResult `
                -Name "Recent encrypted backup" `
                -Passed $true `
                -Detail (
                "Newest backup is " +
                "$([math]::Round($backupAge.TotalHours, 1)) hours old."
            )
        }
        else {
            Add-SmokeTestResult `
                -Name "Recent encrypted backup" `
                -Passed $false `
                -Detail (
                "Newest backup is " +
                "$([math]::Round($backupAge.TotalHours, 1)) hours old, " +
                "exceeding the $MaximumBackupAgeHours hour limit."
            )
        }
    }
}
catch {
    Add-SmokeTestResult `
        -Name "Scheduled backup task" `
        -Passed $false `
        -Detail $_.Exception.Message
}

if (
    Test-Path `
        -LiteralPath $apiLogDirectory `
        -PathType Container
) {
    Add-SmokeTestResult `
        -Name "API log directory" `
        -Passed $true `
        -Detail $apiLogDirectory
}
else {
    Add-SmokeTestResult `
        -Name "API log directory" `
        -Passed $false `
        -Detail "Directory was not found."
}

if (
    Test-Path `
        -LiteralPath $caddyLogDirectory `
        -PathType Container
) {
    Add-SmokeTestResult `
        -Name "Caddy log directory" `
        -Passed $true `
        -Detail $caddyLogDirectory
}
else {
    Add-SmokeTestResult `
        -Name "Caddy log directory" `
        -Passed $false `
        -Detail "Directory was not found."
}

Write-Host ""
$results | Format-Table -AutoSize
Write-Host ""

$failedResults = @(
    $results |
    Where-Object {
        $_.Result -eq "FAIL"
    }
)

if ($failedResults.Count -gt 0) {
    Write-Host (
        "CareQFlow production smoke test FAILED: " +
        "$($failedResults.Count) check(s) failed."
    ) -ForegroundColor Red

    Write-Host ""
    Write-Host "Relevant logs:"
    Write-Host "  API:   $apiLogDirectory"
    Write-Host "  Caddy: $caddyLogDirectory"

    exit 1
}

Write-Host "CareQFlow production smoke test PASSED." `
    -ForegroundColor Green

exit 0
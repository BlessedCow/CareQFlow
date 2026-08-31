[CmdletBinding()]
param(
    [string]$InstallDirectory = "C:\Program Files\CareQueue",
    [string]$EnvironmentFile = "C:\ProgramData\CareQueue\Config\carequeue.env",
    [string]$HostAddress = "127.0.0.1",
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [ValidateRange(1, 32)]
    [int]$Workers = 1
)

$ErrorActionPreference = "Stop"

if ($HostAddress -notin @("127.0.0.1", "::1", "localhost")) {
    throw (
        "CareQFlow production API must bind only to loopback. " +
        "Unsupported host address: $HostAddress"
    )
}

$backendDirectory = Join-Path $InstallDirectory "backend"

$privatePythonExecutable = Join-Path `
    $InstallDirectory `
    "runtime\python\python.exe"

$legacyPythonExecutable = Join-Path `
    $backendDirectory `
    ".venv\Scripts\python.exe"

if (
    Test-Path `
        -LiteralPath $privatePythonExecutable `
        -PathType Leaf
) {
    $pythonExecutable = $privatePythonExecutable
}
elseif (
    Test-Path `
        -LiteralPath $legacyPythonExecutable `
        -PathType Leaf
) {
    $pythonExecutable = $legacyPythonExecutable
}
else {
    throw (
        "CareQFlow Python executable was not found. Checked: " +
        "$privatePythonExecutable and $legacyPythonExecutable"
    )
}

if (-not (Test-Path -LiteralPath $backendDirectory -PathType Container)) {
    throw "CareQFlow backend directory was not found at: $backendDirectory"
}

if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) {
    throw "CareQFlow environment file was not found at: $EnvironmentFile"
}

Get-Content -LiteralPath $EnvironmentFile | ForEach-Object {
    $line = $_.Trim()

    if (
        -not $line `
            -or $line.StartsWith("#") `
            -or -not $line.Contains("=")
    ) {
        return
    }

    $name, $value = $line.Split("=", 2)

    $name = $name.Trim()
    $value = $value.Trim()

    if (-not $name) {
        return
    }

    [Environment]::SetEnvironmentVariable(
        $name,
        $value,
        [EnvironmentVariableTarget]::Process
    )
}

[Environment]::SetEnvironmentVariable(
    "AUTHSTATUS_APP_ENVIRONMENT",
    "production",
    [EnvironmentVariableTarget]::Process
)

Push-Location $backendDirectory

try {
    & $pythonExecutable `
        -m uvicorn `
        authstatus_api.main:app `
        --host $HostAddress `
        --port $Port `
        --workers $Workers `
        --proxy-headers `
        --forwarded-allow-ips "127.0.0.1" `
        --no-access-log

    if ($LASTEXITCODE -ne 0) {
        throw "CareQFlow API exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
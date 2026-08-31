[CmdletBinding()]
param(
    [string]$InstallDirectory = "C:\Program Files\CareQueue",
    [string]$BackupDirectory = "C:\ProgramData\CareQueue\Backups",
    [string]$EnvironmentFile = "C:\ProgramData\CareQueue\Config\carequeue.env"
)

$ErrorActionPreference = "Stop"

$backendDirectory = Join-Path $InstallDirectory "backend"
$pythonExecutable = Join-Path $backendDirectory ".venv\Scripts\python.exe"
$backupScript = Join-Path $backendDirectory "scripts\create_encrypted_backup.py"

if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    throw "CareQFlow Python executable was not found at: $pythonExecutable"
}

if (-not (Test-Path -LiteralPath $backupScript -PathType Leaf)) {
    throw "CareQFlow backup script was not found at: $backupScript"
}

if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) {
    throw "CareQFlow environment file was not found at: $EnvironmentFile"
}

if (-not (Test-Path -LiteralPath $BackupDirectory -PathType Container)) {
    New-Item `
        -ItemType Directory `
        -Path $BackupDirectory `
        -Force | Out-Null
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
    "AUTHSTATUS_BACKUP_DIRECTORY",
    $BackupDirectory,
    [EnvironmentVariableTarget]::Process
)

Push-Location $InstallDirectory

try {
    & $pythonExecutable `
        $backupScript `
        --backup-directory $BackupDirectory

    if ($LASTEXITCODE -ne 0) {
        throw "CareQFlow backup creation failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
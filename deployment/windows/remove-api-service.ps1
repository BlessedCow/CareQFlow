[CmdletBinding()]
param(
    [string]$ServiceDirectory = "C:\Program Files\CareQueue\Service"
)

$ErrorActionPreference = "Stop"

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = [Security.Principal.WindowsPrincipal]::new(
    $currentIdentity
)

$isAdministrator = $currentPrincipal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {
    throw "This script must be run from PowerShell as Administrator."
}

$serviceExecutable = Join-Path `
    $ServiceDirectory `
    "CareQueueApi.exe"

if (-not (Test-Path -LiteralPath $serviceExecutable -PathType Leaf)) {
    throw "WinSW service executable was not found at: $serviceExecutable"
}

$existingService = Get-Service `
    -Name "CareQueueApi" `
    -ErrorAction SilentlyContinue

if (-not $existingService) {
    Write-Host "CareQFlow API service is not installed."
    exit 0
}

if ($existingService.Status -ne "Stopped") {
    & $serviceExecutable stop

    if ($LASTEXITCODE -ne 0) {
        throw "WinSW failed to stop the CareQFlow API service."
    }
}

& $serviceExecutable uninstall

if ($LASTEXITCODE -ne 0) {
    throw "WinSW failed to uninstall the CareQFlow API service."
}

Write-Host "CareQFlow API service removed successfully."
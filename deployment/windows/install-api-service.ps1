[CmdletBinding()]
param(
    [string]$InstallDirectory = "C:\Program Files\CareQueue",
    [string]$ServiceDirectory = "C:\Program Files\CareQueue\Service",
    [switch]$StartService
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

$sourceConfiguration = Join-Path `
    $InstallDirectory `
    "deployment\windows\CareQueueApi.xml"

$serviceExecutable = Join-Path `
    $ServiceDirectory `
    "CareQueueApi.exe"

$serviceConfiguration = Join-Path `
    $ServiceDirectory `
    "CareQueueApi.xml"

if (-not (Test-Path -LiteralPath $sourceConfiguration -PathType Leaf)) {
    throw "Service configuration was not found at: $sourceConfiguration"
}

if (-not (Test-Path -LiteralPath $serviceExecutable -PathType Leaf)) {
    throw "WinSW service executable was not found at: $serviceExecutable"
}

if (-not (Test-Path -LiteralPath $ServiceDirectory -PathType Container)) {
    throw "Service directory was not found at: $ServiceDirectory"
}

[xml]$configuration = Get-Content `
    -LiteralPath $sourceConfiguration `
    -Raw

if ($configuration.service.id -ne "CareQueueApi") {
    throw "The service configuration has an unexpected service ID."
}

Copy-Item `
    -LiteralPath $sourceConfiguration `
    -Destination $serviceConfiguration `
    -Force

$existingService = Get-Service `
    -Name "CareQueueApi" `
    -ErrorAction SilentlyContinue

if ($existingService) {
    throw (
        "The CareQFlow API service is already installed. " +
        "Remove or refresh it before reinstalling."
    )
}

& $serviceExecutable install

if ($LASTEXITCODE -ne 0) {
    throw "WinSW failed to install the CareQFlow API service."
}

$installedService = Get-Service `
    -Name "CareQueueApi" `
    -ErrorAction Stop

Write-Host "CareQFlow API service installed successfully."
Write-Host "Service status: $($installedService.Status)"
Write-Host "Service executable: $serviceExecutable"
Write-Host "Service configuration: $serviceConfiguration"

if ($StartService) {
    & $serviceExecutable start

    if ($LASTEXITCODE -ne 0) {
        throw "The CareQFlow API service was installed but failed to start."
    }

    $installedService.Refresh()

    Write-Host "Service status: $($installedService.Status)"
}
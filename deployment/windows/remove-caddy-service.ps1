[CmdletBinding()]
param(
    [string]$ServiceDirectory = "C:\Program Files\CareQueue\Service"
)

$ErrorActionPreference = "Stop"

$currentIdentity = (
    [Security.Principal.WindowsIdentity]::GetCurrent()
)

$currentPrincipal = (
    [Security.Principal.WindowsPrincipal]::new(
        $currentIdentity
    )
)

$isAdministrator = $currentPrincipal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {
    throw "This script must be run from PowerShell as Administrator."
}

$serviceName = "CareQueueCaddy"

$serviceExecutable = Join-Path `
    $ServiceDirectory `
    "CareQueueCaddy.exe"

$serviceConfiguration = Join-Path `
    $ServiceDirectory `
    "CareQueueCaddy.xml"

$installedService = Get-Service `
    -Name $serviceName `
    -ErrorAction SilentlyContinue

if (-not $installedService) {
    Write-Host "The CareQFlow HTTPS service is not installed."
    return
}

if (
    -not (
        Test-Path `
            -LiteralPath $serviceExecutable `
            -PathType Leaf
    )
) {
    throw (
        "The CareQFlow HTTPS service exists, but its WinSW " +
        "executable was not found at: $serviceExecutable"
    )
}

if ($installedService.Status -ne "Stopped") {
    Write-Host "Stopping the CareQFlow HTTPS service..."

    & $serviceExecutable stop

    if ($LASTEXITCODE -ne 0) {
        throw "WinSW failed to stop the CareQFlow HTTPS service."
    }

    $installedService.WaitForStatus(
        [System.ServiceProcess.ServiceControllerStatus]::Stopped,
        [TimeSpan]::FromSeconds(30)
    )
}

Write-Host "Removing the CareQFlow HTTPS service..."

& $serviceExecutable uninstall

if ($LASTEXITCODE -ne 0) {
    throw "WinSW failed to remove the CareQFlow HTTPS service."
}

$serviceRemovalDeadline = (Get-Date).AddSeconds(30)

do {
    Start-Sleep -Milliseconds 250

    $remainingService = Get-Service `
        -Name $serviceName `
        -ErrorAction SilentlyContinue
}
while (
    $remainingService `
    -and (Get-Date) -lt $serviceRemovalDeadline
)

if ($remainingService) {
    throw (
        "The CareQFlow HTTPS service did not disappear within " +
        "the expected time."
    )
}

Remove-Item `
    -LiteralPath $serviceExecutable `
    -Force `
    -ErrorAction SilentlyContinue

Remove-Item `
    -LiteralPath $serviceConfiguration `
    -Force `
    -ErrorAction SilentlyContinue

Write-Host "CareQFlow HTTPS service removed successfully."
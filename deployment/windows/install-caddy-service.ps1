[CmdletBinding()]
param(
    [string]$InstallDirectory = "C:\Program Files\CareQueue",

    [string]$ServiceDirectory = "C:\Program Files\CareQueue\Service",

    [string]$DataDirectory = "C:\ProgramData\CareQueue",

    [string]$CaddyExecutable = (
        "C:\Program Files\CareQueue\vendor\caddy\caddy.exe"
    ),

    [switch]$StartService
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

$sourceConfiguration = Join-Path `
    $InstallDirectory `
    "deployment\windows\CareQueueCaddy.xml"

$caddyfile = Join-Path `
    $InstallDirectory `
    "deployment\windows\Caddyfile"

$serviceExecutable = Join-Path `
    $ServiceDirectory `
    "CareQueueCaddy.exe"

$serviceConfiguration = Join-Path `
    $ServiceDirectory `
    "CareQueueCaddy.xml"

$caddyDataDirectory = Join-Path `
    $DataDirectory `
    "Caddy\Data"

$caddyConfigDirectory = Join-Path `
    $DataDirectory `
    "Caddy\Config"

$caddyLogDirectory = Join-Path `
    $DataDirectory `
    "Logs\Caddy"

if (
    -not (
        Test-Path `
            -LiteralPath $sourceConfiguration `
            -PathType Leaf
    )
) {
    throw (
        "Caddy service configuration was not found at: " +
        $sourceConfiguration
    )
}

if (
    -not (
        Test-Path `
            -LiteralPath $caddyfile `
            -PathType Leaf
    )
) {
    throw "Caddyfile was not found at: $caddyfile"
}

if (
    -not (
        Test-Path `
            -LiteralPath $CaddyExecutable `
            -PathType Leaf
    )
) {
    throw "Caddy executable was not found at: $CaddyExecutable"
}

if (
    -not (
        Test-Path `
            -LiteralPath $serviceExecutable `
            -PathType Leaf
    )
) {
    throw (
        "The CareQFlow HTTPS WinSW executable was not found at: " +
        $serviceExecutable
    )
}

if (
    -not (
        Test-Path `
            -LiteralPath $ServiceDirectory `
            -PathType Container
    )
) {
    throw "Service directory was not found at: $ServiceDirectory"
}

[xml]$configuration = Get-Content `
    -LiteralPath $sourceConfiguration `
    -Raw

if ($configuration.service.id -ne "CareQueueCaddy") {
    throw "The Caddy service configuration has an unexpected service ID."
}

$configuredExecutable = (
    $configuration.service.executable
).Trim()

if ($configuredExecutable -ne $CaddyExecutable) {
    throw (
        "The Caddy executable in the service configuration does " +
        "not match the requested executable path."
    )
}

$apiService = Get-Service `
    -Name "CareQueueApi" `
    -ErrorAction SilentlyContinue

if (-not $apiService) {
    throw (
        "The CareQFlow API service must be installed before the " +
        "CareQFlow HTTPS service."
    )
}

$existingService = Get-Service `
    -Name "CareQueueCaddy" `
    -ErrorAction SilentlyContinue

if ($existingService) {
    throw (
        "The CareQFlow HTTPS service is already installed. " +
        "Remove it before reinstalling."
    )
}

$requiredDirectories = @(
    $caddyDataDirectory,
    $caddyConfigDirectory,
    $caddyLogDirectory
)

foreach ($directory in $requiredDirectories) {
    if (
        -not (
            Test-Path `
                -LiteralPath $directory `
                -PathType Container
        )
    ) {
        New-Item `
            -ItemType Directory `
            -Path $directory `
            -Force | Out-Null
    }
}

Write-Host "Validating the installed Caddy configuration..."

& $CaddyExecutable `
    validate `
    --config $caddyfile `
    --adapter caddyfile

if ($LASTEXITCODE -ne 0) {
    throw "The installed Caddy configuration is invalid."
}

Copy-Item `
    -LiteralPath $sourceConfiguration `
    -Destination $serviceConfiguration `
    -Force

& $serviceExecutable install

if ($LASTEXITCODE -ne 0) {
    throw "WinSW failed to install the CareQFlow HTTPS service."
}

$installedService = Get-Service `
    -Name "CareQueueCaddy" `
    -ErrorAction Stop

Write-Host "CareQFlow HTTPS service installed successfully."
Write-Host "Service status: $($installedService.Status)"
Write-Host "Service executable: $serviceExecutable"
Write-Host "Service configuration: $serviceConfiguration"
Write-Host "Caddy configuration: $caddyfile"

if ($StartService) {
    & $serviceExecutable start

    if ($LASTEXITCODE -ne 0) {
        throw (
            "The CareQFlow HTTPS service was installed but " +
            "failed to start."
        )
    }

    $installedService.Refresh()

    Write-Host "Service status: $($installedService.Status)"
}
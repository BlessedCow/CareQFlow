[CmdletBinding()]
param(
    [string]$InstallDirectory = "C:\Program Files\CareQueue",

    [string]$DataDirectory = "C:\ProgramData\CareQueue",

    [string]$DeploymentDirectory = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Test-Administrator {
    $currentIdentity = (
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )

    $currentPrincipal = (
        [Security.Principal.WindowsPrincipal]::new(
            $currentIdentity
        )
    )

    return $currentPrincipal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
}

function Remove-CareQueueLocalHostname {
    $hostsPath = Join-Path `
        $env:SystemRoot `
        "System32\drivers\etc\hosts"

    if (
        -not (
            Test-Path `
                -LiteralPath $hostsPath `
                -PathType Leaf
        )
    ) {
        throw "The Windows hosts file was not found: $hostsPath"
    }

    $originalLines = @(
        Get-Content `
            -LiteralPath $hostsPath `
            -ErrorAction Stop
    )

    $filteredLines = @(
        $originalLines |
        Where-Object {
            $_ -notmatch (
                "^\s*127\.0\.0\.1\s+carequeue\.local" +
                "\s+#\s*CareQueue\s*$"
            )
        }
    )

    if ($filteredLines.Count -eq $originalLines.Count) {
        Write-Output (
            "No CareQueue-managed local hostname entry was found."
        )

        return
    }

    Write-Output "Removing the CareQueue local hostname entry..."

    Set-Content `
        -LiteralPath $hostsPath `
        -Value $filteredLines `
        -Encoding ASCII `
        -ErrorAction Stop

    Clear-DnsClientCache `
        -ErrorAction Stop
}

function Invoke-RemovalScript {
    param(
        [Parameter(Mandatory)]
        [string]$ScriptPath,

        [hashtable]$Arguments = @{}
    )

    if (
        -not (
            Test-Path `
                -LiteralPath $ScriptPath `
                -PathType Leaf
        )
    ) {
        throw "Required removal script was not found: $ScriptPath"
    }

    & $ScriptPath @Arguments
}

if (-not (Test-Administrator)) {
    throw (
        "CareQueue uninstallation requires Administrator privileges."
    )
}

$resolvedDeploymentDirectory = (
    Resolve-Path `
        -LiteralPath $DeploymentDirectory `
        -ErrorAction Stop
).Path

$removeCaddyServiceScript = Join-Path `
    $resolvedDeploymentDirectory `
    "remove-caddy-service.ps1"

$removeApiServiceScript = Join-Path `
    $resolvedDeploymentDirectory `
    "remove-api-service.ps1"

$removeBackupTaskScript = Join-Path `
    $resolvedDeploymentDirectory `
    "remove-backup-task.ps1"

$serviceDirectory = Join-Path `
    $InstallDirectory `
    "Service"

Write-Output "Removing the CareQueue Caddy service..."

Invoke-RemovalScript `
    -ScriptPath $removeCaddyServiceScript `
    -Arguments @{
        ServiceDirectory = $serviceDirectory
    }

Write-Output "Removing the CareQueue API service..."

Invoke-RemovalScript `
    -ScriptPath $removeApiServiceScript `
    -Arguments @{
        ServiceDirectory = $serviceDirectory
    }

Write-Output "Removing the CareQueue backup task..."

Invoke-RemovalScript `
    -ScriptPath $removeBackupTaskScript

Remove-CareQueueLocalHostname

if (
    Test-Path `
        -LiteralPath $InstallDirectory
) {
    Write-Output "Removing CareQueue application files..."

    Remove-Item `
        -LiteralPath $InstallDirectory `
        -Recurse `
        -Force `
        -ErrorAction Stop
}
else {
    Write-Output (
        "The CareQueue application directory was not found: " +
        $InstallDirectory
    )
}

if (
    Test-Path `
        -LiteralPath $InstallDirectory
) {
    throw (
        "The CareQueue application directory still exists after " +
        "uninstallation: $InstallDirectory"
    )
}

Write-Output (
    "CareQueue application files and Windows services were removed."
)

if (
    Test-Path `
        -LiteralPath $DataDirectory
) {
    Write-Output (
        "CareQueue data was preserved at: $DataDirectory"
    )
}
else {
    Write-Output (
        "No CareQueue data directory was found at: $DataDirectory"
    )
}

Write-Output "CareQueue uninstallation completed successfully."
[CmdletBinding()]
param(
    [ValidateSet(
        "LocalOnly",
        "SecureLan"
    )]
    [string]$NetworkMode = "LocalOnly",

    [string]$CaddyExecutable = (
        "C:\Program Files\CareQueue\vendor\caddy\caddy.exe"
    )
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$firewallRuleName = "CareQFlow Secure LAN HTTPS"


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


function Remove-CareQFlowSecureLanFirewallRule {
    $existingRules = @(
        Get-NetFirewallRule `
            -DisplayName $firewallRuleName `
            -ErrorAction SilentlyContinue
    )

    if ($existingRules.Count -eq 0) {
        return
    }

    Write-Host "Removing the CareQFlow Secure LAN firewall rule..."

    $existingRules |
    Remove-NetFirewallRule `
        -ErrorAction Stop
}


function Enable-CareQFlowSecureLanFirewallRule {
    $resolvedCaddyExecutable = (
        Resolve-Path `
            -LiteralPath $CaddyExecutable `
            -ErrorAction Stop
    ).Path

    if (
        -not (
            Test-Path `
                -LiteralPath $resolvedCaddyExecutable `
                -PathType Leaf
        )
    ) {
        throw (
            "The CareQFlow Caddy executable was not found: " +
            $resolvedCaddyExecutable
        )
    }

    Remove-CareQFlowSecureLanFirewallRule

    Write-Host (
        "Allowing CareQFlow HTTPS from the local subnet on " +
        "Private Windows networks..."
    )

    New-NetFirewallRule `
        -DisplayName $firewallRuleName `
        -Direction Inbound `
        -Action Allow `
        -Enabled True `
        -Profile Private `
        -Program $resolvedCaddyExecutable `
        -Protocol TCP `
        -LocalPort 443 `
        -RemoteAddress LocalSubnet `
        -EdgeTraversalPolicy Block `
        -ErrorAction Stop |
    Out-Null
}


if (-not (Test-Administrator)) {
    throw (
        "CareQFlow network access configuration requires " +
        "Administrator privileges."
    )
}

switch ($NetworkMode) {
    "LocalOnly" {
        Remove-CareQFlowSecureLanFirewallRule

        Write-Host (
            "CareQFlow network mode: LocalOnly. " +
            "No LAN firewall access is enabled."
        )
    }

    "SecureLan" {
        Enable-CareQFlowSecureLanFirewallRule

        Write-Host (
            "CareQFlow network mode: SecureLan. " +
            "HTTPS is permitted from the local subnet on " +
            "Private Windows networks."
        )
    }

    default {
        throw "Unsupported CareQFlow network mode: $NetworkMode"
    }
}
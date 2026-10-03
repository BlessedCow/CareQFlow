[CmdletBinding()]
param(
    [ValidateSet(
        "LocalOnly",
        "SecureLan",
        "Tailscale"
    )]
    [string]$NetworkMode = "LocalOnly",
    
    [string]$ApplicationOrigin,
    
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


function Test-CareQFlowTailscaleIPv4Address {
    param(
        [Parameter(Mandatory)]
        [string]$Address
    )

    $parsedAddress = $null

    if (
        -not [Net.IPAddress]::TryParse(
            $Address,
            [ref]$parsedAddress
        )
    ) {
        return $false
    }

    if (
        $parsedAddress.AddressFamily -ne
        [Net.Sockets.AddressFamily]::InterNetwork
    ) {
        return $false
    }

    $bytes = $parsedAddress.GetAddressBytes()

    return (
        $bytes[0] -eq 100 `
            -and $bytes[1] -ge 64 `
            -and $bytes[1] -le 127
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


function Assert-CareQFlowTailscaleAddress {
    if ([string]::IsNullOrWhiteSpace($ApplicationOrigin)) {
        throw (
            "Tailscale mode requires ApplicationOrigin using " +
            "the CareQFlow host Tailscale IPv4 address."
        )
    }

    try {
        $applicationUri = [Uri]$ApplicationOrigin
    }
    catch {
        throw (
            "Tailscale ApplicationOrigin is not a valid URI: " +
            $ApplicationOrigin
        )
    }

    if (
        -not $applicationUri.IsAbsoluteUri `
            -or $applicationUri.Scheme -ne "https" `
            -or -not $applicationUri.Host `
            -or $applicationUri.UserInfo `
            -or $applicationUri.AbsolutePath -ne "/" `
            -or $applicationUri.Query `
            -or $applicationUri.Fragment `
            -or $applicationUri.Port -ne 443
    ) {
        throw (
            "Tailscale mode requires an HTTPS origin using the " +
            "default HTTPS port with no path, query, or fragment."
        )
    }

    if (
        -not (
            Test-CareQFlowTailscaleIPv4Address `
                -Address $applicationUri.Host
        )
    ) {
        throw (
            "Tailscale mode requires an IPv4 address in " +
            "100.64.0.0/10."
        )
    }

    $tailscaleCommand = Get-Command `
        "tailscale.exe" `
        -ErrorAction SilentlyContinue

    if (-not $tailscaleCommand) {
        throw (
            "Tailscale mode requires the Tailscale client " +
            "to be installed."
        )
    }

    $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processStartInfo.FileName = $tailscaleCommand.Source
    $processStartInfo.Arguments = "ip -4"
    $processStartInfo.UseShellExecute = $false
    $processStartInfo.CreateNoWindow = $true
    $processStartInfo.RedirectStandardOutput = $true
    $processStartInfo.RedirectStandardError = $true
    
    $tailscaleProcess = New-Object System.Diagnostics.Process
    $tailscaleProcess.StartInfo = $processStartInfo
    
    if (-not $tailscaleProcess.Start()) {
        throw "CareQFlow could not start the Tailscale client."
    }
    
    if (-not $tailscaleProcess.WaitForExit(10000)) {
        try {
            $tailscaleProcess.Kill()
        }
        catch {
        }
    
        throw (
            "Tailscale did not respond within 10 seconds. " +
            "Verify that the Tailscale service is running normally."
        )
    }
    
    $tailscaleOutput = $tailscaleProcess.StandardOutput.ReadToEnd()
    
    if ($tailscaleProcess.ExitCode -ne 0) {
        throw (
            "Tailscale is not connected or does not have " +
            "an IPv4 address."
        )
    }
    
    $tailscaleAddresses = @(
        $tailscaleOutput -split "\r?\n" |
        ForEach-Object {
            $_.Trim()
        } |
        Where-Object {
            -not [string]::IsNullOrWhiteSpace($_)
        }
    )
    
    if ($tailscaleAddresses.Count -eq 0) {
        throw (
            "Tailscale is not connected or does not have " +
            "an IPv4 address."
        )
    }

    if ($applicationUri.Host -notin $tailscaleAddresses) {
        throw (
            "The selected Tailscale address is not assigned " +
            "to this host."
        )
    }
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

    "Tailscale" {
        Remove-CareQFlowSecureLanFirewallRule
        Assert-CareQFlowTailscaleAddress

        Write-Host (
            "CareQFlow network mode: Tailscale. " +
            "No CareQFlow LAN firewall rule is enabled."
        )
    }

    default {
        throw "Unsupported CareQFlow network mode: $NetworkMode"
    }
}
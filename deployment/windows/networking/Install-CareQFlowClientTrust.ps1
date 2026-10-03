[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$CertificatePath,

    [Parameter(Mandatory)]
    [string]$ExpectedFingerprint,

    [string]$ApplicationOrigin
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


function Get-CertificateSha256Fingerprint {
    param(
        [Parameter(Mandatory)]
        [System.Security.Cryptography.X509Certificates.X509Certificate2]
        $Certificate
    )

    $sha256 = (
        [System.Security.Cryptography.SHA256]::Create()
    )

    try {
        $fingerprintBytes = $sha256.ComputeHash(
            $Certificate.RawData
        )
    }
    finally {
        $sha256.Dispose()
    }

    return (
        $fingerprintBytes |
        ForEach-Object {
            $_.ToString("X2")
        }
    ) -join ""
}


function Set-CareQFlowClientHostname {
    param(
        [Parameter(Mandatory)]
        [string]$ApplicationOrigin
    )

    try {
        $applicationUri = [Uri]$ApplicationOrigin
    }
    catch {
        throw (
            "The CareQFlow application origin is not a valid URI: " +
            $ApplicationOrigin
        )
    }

    if (
        -not $applicationUri.IsAbsoluteUri `
            -or $applicationUri.Scheme -ne "https" `
            -or $applicationUri.Port -ne 443 `
            -or -not $applicationUri.HostNameType.Equals(
            [System.UriHostNameType]::IPv4
        )
    ) {
        throw (
            "CareQFlow client hostname configuration requires " +
            "an HTTPS IPv4 application origin on port 443."
        )
    }

    $ipAddress = [System.Net.IPAddress]::Parse(
        $applicationUri.Host
    )

    $bytes = $ipAddress.GetAddressBytes()

    $isPrivateAddress = (
        $bytes[0] -eq 10 `
            -or (
            $bytes[0] -eq 172 `
                -and $bytes[1] -ge 16 `
                -and $bytes[1] -le 31
        ) `
            -or (
            $bytes[0] -eq 192 `
                -and $bytes[1] -eq 168
        )
    )
    
    $isTailscaleAddress = (
        $bytes[0] -eq 100 `
            -and $bytes[1] -ge 64 `
            -and $bytes[1] -le 127
    )
    
    if (
        -not $isPrivateAddress `
            -and -not $isTailscaleAddress
    ) {
        throw (
            "CareQFlow client hostname configuration requires " +
            "an RFC1918 or Tailscale IPv4 address."
        )
    }

    $hostsPath = Join-Path `
        $env:SystemRoot `
        "System32\drivers\etc\hosts"

    $hostsContent = @(
        Get-Content `
            -LiteralPath $hostsPath `
            -ErrorAction Stop
    )

    $hostname = "careqflow.local"
    $replacementLine = "$($applicationUri.Host) $hostname"

    $updatedHostsContent = @()
    $mappingAdded = $false

    foreach ($line in $hostsContent) {
        $trimmedLine = $line.Trim()

        if (
            $trimmedLine `
                -and -not $trimmedLine.StartsWith("#")
        ) {
            $lineWithoutComment = (
                $line.Split("#", 2)[0]
            ).Trim()

            $parts = @(
                $lineWithoutComment -split "\s+"
            )

            if (
                $parts.Count -ge 2 `
                    -and $parts[1..($parts.Count - 1)] `
                    -contains $hostname
            ) {
                if (-not $mappingAdded) {
                    $updatedHostsContent += $replacementLine
                    $mappingAdded = $true
                }

                continue
            }
        }

        $updatedHostsContent += $line
    }

    if (-not $mappingAdded) {
        $updatedHostsContent += $replacementLine
    }

    Set-Content `
        -LiteralPath $hostsPath `
        -Value $updatedHostsContent `
        -Encoding ASCII `
        -ErrorAction Stop

    Clear-DnsClientCache `
        -ErrorAction Stop

    Write-Host (
        "CareQFlow hostname configured: " +
        "$hostname -> $($applicationUri.Host)"
    )
}


if (-not (Test-Administrator)) {
    throw (
        "Installing the CareQFlow client trust certificate " +
        "requires Administrator privileges."
    )
}

$resolvedCertificatePath = (
    Resolve-Path `
        -LiteralPath $CertificatePath `
        -ErrorAction Stop
).Path

if (
    -not (
        Test-Path `
            -LiteralPath $resolvedCertificatePath `
            -PathType Leaf
    )
) {
    throw (
        "The CareQFlow client trust certificate was not found: " +
        $resolvedCertificatePath
    )
}

$normalizedExpectedFingerprint = (
    $ExpectedFingerprint -replace "[^0-9A-Fa-f]", ""
).ToUpperInvariant()

if (
    $normalizedExpectedFingerprint.Length -ne 64 `
        -or $normalizedExpectedFingerprint -notmatch "^[0-9A-F]{64}$"
) {
    throw (
        "ExpectedFingerprint must be a complete SHA-256 " +
        "certificate fingerprint."
    )
}

try {
    $certificate = (
        [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
            $resolvedCertificatePath
        )
    )
}
catch {
    throw (
        "The CareQFlow client trust certificate could not be read. " +
        "Error: $($_.Exception.Message)"
    )
}

if ($certificate.HasPrivateKey) {
    throw (
        "The CareQFlow client trust certificate unexpectedly " +
        "contains private key material."
    )
}

$basicConstraintsExtension = (
    $certificate.Extensions |
    Where-Object {
        $_.Oid.Value -eq "2.5.29.19"
    } |
    Select-Object -First 1
)

if (-not $basicConstraintsExtension) {
    throw (
        "The CareQFlow client trust certificate does not contain " +
        "X.509 basic constraints."
    )
}

$basicConstraints = (
    [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new()
)

$basicConstraints.CopyFrom(
    $basicConstraintsExtension
)

if (-not $basicConstraints.CertificateAuthority) {
    throw (
        "The supplied CareQFlow certificate is not marked " +
        "as a certificate authority."
    )
}

$keyUsageExtension = (
    $certificate.Extensions |
    Where-Object {
        $_.Oid.Value -eq "2.5.29.15"
    } |
    Select-Object -First 1
)

if ($keyUsageExtension) {
    $keyUsage = (
        [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new()
    )

    $keyUsage.CopyFrom(
        $keyUsageExtension
    )

    $certificateSigningFlag = (
        [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::
        KeyCertSign
    )

    if (
        (
            $keyUsage.KeyUsages -band $certificateSigningFlag
        ) -eq 0
    ) {
        throw (
            "The CareQFlow certificate is not permitted to sign " +
            "certificates."
        )
    }
}

$now = [DateTime]::Now

if (
    $certificate.NotBefore -gt $now `
        -or $certificate.NotAfter -le $now
) {
    throw (
        "The CareQFlow client trust certificate is not " +
        "currently valid."
    )
}

$actualFingerprint = (
    Get-CertificateSha256Fingerprint `
        -Certificate $certificate
)

if (
    $actualFingerprint -cne $normalizedExpectedFingerprint
) {
    throw (
        "The CareQFlow certificate SHA-256 fingerprint does not " +
        "match the expected fingerprint. Do not trust this " +
        "certificate."
    )
}

$existingCertificate = (
    Get-ChildItem `
        -Path "Cert:\LocalMachine\Root" `
        -ErrorAction Stop |
    Where-Object {
        $_.Thumbprint -eq $certificate.Thumbprint
    } |
    Select-Object -First 1
)

if ($existingCertificate) {
    Write-Host (
        "The verified CareQFlow root certificate is already " +
        "trusted on this computer."
    )

    Write-Host (
        "SHA-256 fingerprint: " +
        $actualFingerprint
    )
}
else {
    Write-Host (
        "The CareQFlow certificate fingerprint was verified."
    )

    Write-Host (
        "Installing the CareQFlow root certificate into the " +
        "Local Machine trusted root store..."
    )

    $importedCertificate = Import-Certificate `
        -FilePath $resolvedCertificatePath `
        -CertStoreLocation "Cert:\LocalMachine\Root" `
        -ErrorAction Stop

    if (-not $importedCertificate) {
        throw (
            "Windows did not return an installed CareQFlow " +
            "certificate after import."
        )
    }

    $installedCertificate = (
        Get-ChildItem `
            -Path "Cert:\LocalMachine\Root" `
            -ErrorAction Stop |
        Where-Object {
            $_.Thumbprint -eq $certificate.Thumbprint
        } |
        Select-Object -First 1
    )

    if (-not $installedCertificate) {
        throw (
            "The CareQFlow root certificate could not be verified " +
            "in the Windows trusted root store after installation."
        )
    }
}

if (-not [string]::IsNullOrWhiteSpace($ApplicationOrigin)) {
    Set-CareQFlowClientHostname `
        -ApplicationOrigin $ApplicationOrigin
}

Write-Host ""
Write-Host "CareQFlow client trust installed successfully."
Write-Host (
    "SHA-256 fingerprint: " +
    $actualFingerprint
)
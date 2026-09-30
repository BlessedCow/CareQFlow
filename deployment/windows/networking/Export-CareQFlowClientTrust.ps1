[CmdletBinding()]
param(
    [string]$DataDirectory = "C:\ProgramData\CareQueue",

    [string]$OutputDirectory,

    [Parameter(Mandatory)]
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
        -or $applicationUri.UserInfo `
        -or $applicationUri.AbsolutePath -ne "/" `
        -or $applicationUri.Query `
        -or $applicationUri.Fragment `
        -or $applicationUri.Port -ne 443
) {
    throw (
        "CareQFlow client onboarding requires a plain HTTPS " +
        "origin on port 443."
    )
}

$normalizedApplicationOrigin = (
    $ApplicationOrigin.TrimEnd("/")
)


if (-not (Test-Administrator)) {
    throw (
        "CareQFlow client trust export requires " +
        "Administrator privileges."
    )
}

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path `
        $DataDirectory `
        "ClientTrust"
}

$clientInstallerSource = Join-Path `
    $PSScriptRoot `
    "Install-CareQFlowClientTrust.ps1"

if (
    -not (
        Test-Path `
            -LiteralPath $clientInstallerSource `
            -PathType Leaf
    )
) {
    throw (
        "The CareQFlow client trust installer was not found: " +
        $clientInstallerSource
    )
}

$rootCertificatePath = Join-Path `
    $DataDirectory `
    "Caddy\Data\caddy\pki\authorities\local\root.crt"

if (
    -not (
        Test-Path `
            -LiteralPath $rootCertificatePath `
            -PathType Leaf
    )
) {
    throw (
        "The CareQFlow Caddy root certificate was not found: " +
        $rootCertificatePath
    )
}

try {
    $rootCertificate = (
        [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
            $rootCertificatePath
        )
    )
}
catch {
    throw (
        "The CareQFlow Caddy root certificate could not be read. " +
        "Error: $($_.Exception.Message)"
    )
}

if ($rootCertificate.HasPrivateKey) {
    throw (
        "The CareQFlow client trust export refused a certificate " +
        "containing private key material."
    )
}

$basicConstraintsExtension = (
    $rootCertificate.Extensions |
    Where-Object {
        $_.Oid.Value -eq "2.5.29.19"
    } |
    Select-Object -First 1
)

if (-not $basicConstraintsExtension) {
    throw (
        "The CareQFlow root certificate does not contain " +
        "X.509 basic constraints."
    )
}

$basicConstraints = (
    [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new()
)

$basicConstraints.CopyFrom($basicConstraintsExtension)

if (-not $basicConstraints.CertificateAuthority) {
    throw (
        "The CareQFlow client trust certificate is not marked " +
        "as a certificate authority."
    )
}

$now = [DateTime]::Now

if (
    $rootCertificate.NotBefore -gt $now `
        -or $rootCertificate.NotAfter -le $now
) {
    throw (
        "The CareQFlow root certificate is not currently valid."
    )
}

New-Item `
    -ItemType Directory `
    -Path $OutputDirectory `
    -Force |
Out-Null

$exportedCertificatePath = Join-Path `
    $OutputDirectory `
    "CareQFlow-Root-CA.crt"

$verificationPath = Join-Path `
    $OutputDirectory `
    "SHA256SUMS.txt"

$onboardingPath = Join-Path `
    $OutputDirectory `
    "CLIENT-ONBOARDING.txt"

$clientInstallerDestination = Join-Path `
    $OutputDirectory `
    "Install-CareQFlowClientTrust.ps1"

Copy-Item `
    -LiteralPath $rootCertificatePath `
    -Destination $exportedCertificatePath `
    -Force

Copy-Item `
    -LiteralPath $clientInstallerSource `
    -Destination $clientInstallerDestination `
    -Force

$exportedCertificate = (
    [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
        $exportedCertificatePath
    )
)

if ($exportedCertificate.HasPrivateKey) {
    Remove-Item `
        -LiteralPath $exportedCertificatePath `
        -Force `
        -ErrorAction SilentlyContinue

    throw (
        "The exported CareQFlow certificate unexpectedly contains " +
        "private key material."
    )
}

$fileHash = Get-FileHash `
    -LiteralPath $exportedCertificatePath `
    -Algorithm SHA256

$sha256 = (
    [System.Security.Cryptography.SHA256]::Create()
)

try {
    $certificateFingerprintBytes = (
        $sha256.ComputeHash(
            $exportedCertificate.RawData
        )
    )
}
finally {
    $sha256.Dispose()
}

$certificateFingerprint = (
    $certificateFingerprintBytes |
    ForEach-Object {
        $_.ToString("X2")
    }
) -join ":"

@(
    "CareQFlow Secure LAN Client Onboarding"
    ""
    "CareQFlow server URL:"
    $normalizedApplicationOrigin
    ""
    "Friendly client URL:"
    "https://careqflow.local"
    ""
    "Before trusting the included certificate, verify its"
    "SHA-256 fingerprint with the CareQFlow administrator"
    "using a separate trusted method."
    ""
    "Certificate SHA-256 fingerprint:"
    $certificateFingerprint
    ""
    "Windows client:"
    "1. Copy this entire ClientTrust folder to the authorized computer."
    "2. Open PowerShell as Administrator in the copied folder."
    "3. Verify the fingerprint above using a separate trusted method."
    "4. Run:"
    ""
    (
        '   powershell.exe -NoProfile -ExecutionPolicy Bypass ' +
        '-File ".\Install-CareQFlowClientTrust.ps1" ' +
        '-CertificatePath ".\CareQFlow-Root-CA.crt" ' +
        '-ExpectedFingerprint "' +
        $certificateFingerprint +
        '" ' +
        '-ApplicationOrigin "' +
        $normalizedApplicationOrigin +
        '"'
    )
    ""
    "5. Open:"
    "   https://careqflow.local"
    ""
    "The server IP URL also remains available:"
    "   $normalizedApplicationOrigin"
    ""
    "Security:"
    "- Do not install the certificate if the fingerprint is different."
    "- Do not expose CareQFlow using router port forwarding."
    "- Secure LAN is intended only for trusted private networks."
    "- The CareQFlow backend remains inaccessible directly."
) |
Set-Content `
    -LiteralPath $onboardingPath `
    -Encoding UTF8

@(
    "CareQFlow Client Trust Certificate"
    ""
    "File: CareQFlow-Root-CA.crt"
    "File SHA-256: $($fileHash.Hash)"
    "Certificate SHA-256 fingerprint: $certificateFingerprint"
    "Subject: $($exportedCertificate.Subject)"
    "Valid from: $($exportedCertificate.NotBefore.ToString('o'))"
    "Valid until: $($exportedCertificate.NotAfter.ToString('o'))"
) |
Set-Content `
    -LiteralPath $verificationPath `
    -Encoding UTF8

$aclArguments = @(
    $OutputDirectory,
    "/inheritance:r",
    "/grant:r",
    "*S-1-5-18:(OI)(CI)F",
    "*S-1-5-32-544:(OI)(CI)F",
    "*S-1-5-32-545:(OI)(CI)RX"
)

& icacls.exe @aclArguments | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw (
        "CareQFlow could not secure the client trust " +
        "export directory permissions."
    )
}

$unexpectedPrivateKeyFiles = @(
    Get-ChildItem `
        -LiteralPath $OutputDirectory `
        -File `
        -Recurse `
        -ErrorAction Stop |
    Where-Object {
        $_.Extension -in @(
            ".key",
            ".pfx",
            ".p12",
            ".pem"
        )
    }
)

if ($unexpectedPrivateKeyFiles.Count -gt 0) {
    throw (
        "Private key material was detected in the CareQFlow " +
        "client trust export directory."
    )
}

Write-Host "CareQFlow client trust package created successfully."
Write-Host "Certificate: $exportedCertificatePath"
Write-Host "Verification: $verificationPath"
Write-Host "Onboarding instructions: $onboardingPath"
Write-Host "Windows trust installer: $clientInstallerDestination"
Write-Host "CareQFlow URL: $normalizedApplicationOrigin"
Write-Host (
    "Certificate SHA-256 fingerprint: " +
    $certificateFingerprint
)
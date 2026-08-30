[CmdletBinding()]
param(
    [string]$PayloadDirectory,

    [string]$InstallerPath,

    [string]$ApplicationUrl = "https://carequeue.local",

    [string]$ApiHealthUrl = "http://127.0.0.1:8000/api/health",

    [switch]$SkipInstalledAppChecks
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Status {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Message
    )

    Write-Information `
        -MessageData $Message `
        -InformationAction Continue
}

function Assert-DirectoryExists {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Description
    )

    if (
        -not (
            Test-Path `
                -LiteralPath $Path `
                -PathType Container
        )
    ) {
        throw ("Missing {0}: {1}" -f $Description, $Path)
    }
}

function Assert-FileExists {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Description
    )

    if (
        -not (
            Test-Path `
                -LiteralPath $Path `
                -PathType Leaf
        )
    ) {
        throw ("Missing {0}: {1}" -f $Description, $Path)
    }
}

function Assert-ServiceRunning {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    $service = Get-Service `
        -Name $Name `
        -ErrorAction Stop

    if ($service.Status -ne "Running") {
        throw ("Service {0} is {1}, not Running." -f $Name, $service.Status)
    }
}

function Convert-ToRelativePath {
    param(
        [Parameter(Mandatory)]
        [string]$BasePath,

        [Parameter(Mandatory)]
        [string]$FullPath
    )

    return $FullPath.Substring($BasePath.Length).TrimStart(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ).Replace("\", "/")
}

$repositoryRoot = (
    Resolve-Path `
        -LiteralPath (
            Join-Path `
                $PSScriptRoot `
                "..\..\.."
        )
).Path

if (-not $PayloadDirectory) {
    $PayloadDirectory = Join-Path `
        $repositoryRoot `
        "build\windows\payload"
}

if (-not $InstallerPath) {
    $InstallerPath = Join-Path `
        $repositoryRoot `
        "build\windows\installer\CareQueue-Setup-0.4.0.exe"
}

$resolvedPayloadDirectory = (
    Resolve-Path `
        -LiteralPath $PayloadDirectory `
        -ErrorAction Stop
).Path

$resolvedInstallerPath = (
    Resolve-Path `
        -LiteralPath $InstallerPath `
        -ErrorAction Stop
).Path

Write-Status "Validating Windows release package inputs..."
Write-Status ("Payload:   {0}" -f $resolvedPayloadDirectory)
Write-Status ("Installer: {0}" -f $resolvedInstallerPath)

Assert-DirectoryExists `
    -Path $resolvedPayloadDirectory `
    -Description "payload directory"

Assert-FileExists `
    -Path $resolvedInstallerPath `
    -Description "installer executable"

$requiredPayloadDirectories = @(
    "backend/authstatus_api",
    "backend/scripts",
    "frontend/dist",
    "runtime/python",
    "vendor/caddy",
    "vendor/winsw",
    "dependencies/wheelhouse",
    "deployment/windows"
)

foreach ($requiredPayloadDirectory in $requiredPayloadDirectories) {
    Assert-DirectoryExists `
        -Path (
            Join-Path `
                $resolvedPayloadDirectory `
                $requiredPayloadDirectory
        ) `
        -Description "payload directory"
}

$requiredPayloadFiles = @(
    "backend/requirements.txt",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/dist/index.html",
    "runtime/python/python.exe",
    "vendor/caddy/caddy.exe",
    "vendor/winsw/WinSW-x64.exe",
    "vendor/versions.json",
    "deployment/windows/install-production.ps1",
    "deployment/windows/run-api.ps1",
    "deployment/windows/Caddyfile",
    "deployment/windows/CareQueueApi.xml",
    "deployment/windows/CareQueueCaddy.xml",
    "payload.json",
    "SHA256SUMS.txt"
)

foreach ($requiredPayloadFile in $requiredPayloadFiles) {
    Assert-FileExists `
        -Path (
            Join-Path `
                $resolvedPayloadDirectory `
                $requiredPayloadFile
        ) `
        -Description "payload file"
}

Write-Status "Checking payload manifest coverage..."

$manifestPath = Join-Path `
    $resolvedPayloadDirectory `
    "SHA256SUMS.txt"

$manifestContent = Get-Content `
    -LiteralPath $manifestPath `
    -Raw

foreach ($requiredManifestEntry in @(
    "backend/requirements.txt",
    "frontend/dist/index.html",
    "payload.json",
    "vendor/versions.json"
)) {
    if ($manifestContent -notmatch [regex]::Escape($requiredManifestEntry)) {
        throw ("Manifest does not include {0}." -f $requiredManifestEntry)
    }
}

Write-Status "Checking payload for sensitive local files..."

$sensitivePayloadFiles = Get-ChildItem `
    -LiteralPath $resolvedPayloadDirectory `
    -File `
    -Recurse |
Where-Object {
    $_.Name -in @(".env", "carequeue.env") `
        -or $_.Extension -in @(".db", ".sqlite", ".sqlite3", ".pdf")
}

if ($sensitivePayloadFiles) {
    $sensitivePayloadList = $sensitivePayloadFiles |
    ForEach-Object {
        Convert-ToRelativePath `
            -BasePath $resolvedPayloadDirectory `
            -FullPath $_.FullName
    }

    throw (
        "Payload contains sensitive local files: " +
        ($sensitivePayloadList -join ", ")
    )
}

Write-Status "Checking installer artifact..."

$installerItem = Get-Item `
    -LiteralPath $resolvedInstallerPath

if ($installerItem.Length -lt 1MB) {
    throw "Installer executable is unexpectedly small."
}

$installerHash = Get-FileHash `
    -LiteralPath $resolvedInstallerPath `
    -Algorithm SHA256

$installerChecksumPath = "$resolvedInstallerPath.sha256"

"{0}  {1}" -f `
    $installerHash.Hash.ToLowerInvariant(), `
    $installerItem.Name |
Set-Content `
    -LiteralPath $installerChecksumPath `
    -Encoding ascii

Write-Status ("Installer SHA256: {0}" -f $installerHash.Hash)
Write-Status ("Installer checksum: {0}" -f $installerChecksumPath)

if ($SkipInstalledAppChecks) {
    Write-Status "Skipping installed application checks."
    Write-Status "Release package validation completed."
    return
}

Write-Status "Checking installed Windows services..."

Assert-ServiceRunning -Name "CareQueueApi"
Assert-ServiceRunning -Name "CareQueueCaddy"

Write-Status "Checking API health endpoint..."

$applicationUri = [Uri]$ApplicationUrl
$trustedHostHeader = $applicationUri.Authority

$healthResponse = Invoke-RestMethod `
    -Method Get `
    -Uri $ApiHealthUrl `
    -Headers @{
        Host = $trustedHostHeader
    } `
    -TimeoutSec 10

if ($healthResponse.status -ne "ok") {
    throw (
        "API health endpoint did not return status ok. Response: " +
        ($healthResponse | ConvertTo-Json -Compress)
    )
}

Write-Status "Checking HTTPS frontend and security headers..."

$frontendResponse = Invoke-WebRequest `
    -Uri $ApplicationUrl `
    -UseBasicParsing `
    -TimeoutSec 10

if ($frontendResponse.StatusCode -lt 200 -or $frontendResponse.StatusCode -ge 400) {
    throw (
        "Frontend returned unexpected HTTP status code: " +
        $frontendResponse.StatusCode
    )
}

$contentSecurityPolicy = [string]::Join(
    "; ",
    $frontendResponse.Headers["Content-Security-Policy"]
)

if (-not $contentSecurityPolicy) {
    throw "Frontend response is missing Content-Security-Policy."
}

if ($contentSecurityPolicy -notmatch "script-src 'self' 'unsafe-inline'") {
    throw (
        "Content-Security-Policy is not compatible with the packaged " +
        "single-file frontend. Current value: " +
        $contentSecurityPolicy
    )
}

foreach ($requiredHeader in @(
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy"
)) {
    if (-not $frontendResponse.Headers[$requiredHeader]) {
        throw ("Frontend response is missing {0}." -f $requiredHeader)
    }
}

$installedCaddyExecutable = "C:\Program Files\CareQueue\vendor\caddy\caddy.exe"
$installedCaddyfile = "C:\Program Files\CareQueue\deployment\windows\Caddyfile"

if (
    (Test-Path -LiteralPath $installedCaddyExecutable -PathType Leaf) `
        -and (
            Test-Path `
                -LiteralPath $installedCaddyfile `
                -PathType Leaf
        )
) {
    Write-Status "Validating installed Caddy configuration..."

    & $installedCaddyExecutable `
        validate `
        --config $installedCaddyfile

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Installed Caddy configuration validation failed. " +
            "Exit code: $LASTEXITCODE"
        )
    }
}

Write-Status "Release package validation completed."

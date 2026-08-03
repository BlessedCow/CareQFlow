[CmdletBinding()]
param(
    [string]$AssetCacheDirectory,

    [string]$OutputDirectory,

    [switch]$ForceDownload,

    [switch]$KeepExisting
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

function Assert-FileHash {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$ExpectedSha256,

        [Parameter(Mandatory)]
        [string]$AssetName
    )

    $actualSha256 = (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256
    ).Hash.ToLowerInvariant()

    $normalizedExpectedSha256 = $ExpectedSha256.ToLowerInvariant()

    if ($actualSha256 -ne $normalizedExpectedSha256) {
        throw (
            "$AssetName failed SHA256 validation. " +
            "Expected: $normalizedExpectedSha256. " +
            "Actual: $actualSha256. " +
            "File: $Path"
        )
    }
}

function Get-PinnedAsset {
    param(
        [Parameter(Mandatory)]
        [string]$DownloadUrl,

        [Parameter(Mandatory)]
        [string]$DestinationPath,

        [Parameter(Mandatory)]
        [string]$ExpectedSha256,

        [Parameter(Mandatory)]
        [string]$AssetName,

        [switch]$Force
    )

    if (
        (Test-Path -LiteralPath $DestinationPath -PathType Leaf) `
            -and -not $Force
    ) {
        try {
            Assert-FileHash `
                -Path $DestinationPath `
                -ExpectedSha256 $ExpectedSha256 `
                -AssetName $AssetName

            Write-Status (
                "Using the validated cached $AssetName asset."
            )

            return
        }
        catch {
            Write-Status (
                "The cached $AssetName asset is invalid and will be " +
                "downloaded again."
            )

            Remove-Item `
                -LiteralPath $DestinationPath `
                -Force
        }
    }

    $temporaryDownloadPath = "$DestinationPath.download"

    Remove-Item `
        -LiteralPath $temporaryDownloadPath `
        -Force `
        -ErrorAction SilentlyContinue

    Write-Status "Downloading $AssetName..."

    try {
        Invoke-WebRequest `
            -Uri $DownloadUrl `
            -OutFile $temporaryDownloadPath `
            -UseBasicParsing

        Assert-FileHash `
            -Path $temporaryDownloadPath `
            -ExpectedSha256 $ExpectedSha256 `
            -AssetName $AssetName

        Move-Item `
            -LiteralPath $temporaryDownloadPath `
            -Destination $DestinationPath `
            -Force
    }
    finally {
        Remove-Item `
            -LiteralPath $temporaryDownloadPath `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

$repositoryRoot = (
    Resolve-Path `
        -LiteralPath (
            Join-Path `
                $PSScriptRoot `
                "..\..\.."
        )
).Path

$assetLockPath = Join-Path `
    $PSScriptRoot `
    "vendor-assets.json"

if (
    -not (
        Test-Path `
            -LiteralPath $assetLockPath `
            -PathType Leaf
    )
) {
    throw (
        "The vendor asset lock file was not found: " +
        $assetLockPath
    )
}

$assetLock = Get-Content `
    -LiteralPath $assetLockPath `
    -Raw |
ConvertFrom-Json

if ($assetLock.schema_version -ne 1) {
    throw (
        "Unsupported vendor asset lock schema version: " +
        $assetLock.schema_version
    )
}

$caddyAsset = $assetLock.assets.caddy
$winswAsset = $assetLock.assets.winsw

if (-not $AssetCacheDirectory) {
    $AssetCacheDirectory = Join-Path `
        $repositoryRoot `
        "local_installer_assets\vendor"
}

New-Item `
    -ItemType Directory `
    -Path $AssetCacheDirectory `
    -Force |
Out-Null

$resolvedAssetCacheDirectory = (
    Resolve-Path `
        -LiteralPath $AssetCacheDirectory
).Path

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path `
        $repositoryRoot `
        "build\windows\vendor"
}

if (
    (Test-Path -LiteralPath $OutputDirectory) `
        -and -not $KeepExisting
) {
    Write-Status "Removing the existing staged vendor assets..."

    Remove-Item `
        -LiteralPath $OutputDirectory `
        -Recurse `
        -Force
}

New-Item `
    -ItemType Directory `
    -Path $OutputDirectory `
    -Force |
Out-Null

$resolvedOutputDirectory = (
    Resolve-Path `
        -LiteralPath $OutputDirectory
).Path

$caddyCachedArchive = Join-Path `
    $resolvedAssetCacheDirectory `
    $caddyAsset.archive_name

$winswCachedExecutable = Join-Path `
    $resolvedAssetCacheDirectory `
    $winswAsset.file_name

Get-PinnedAsset `
    -DownloadUrl $caddyAsset.download_url `
    -DestinationPath $caddyCachedArchive `
    -ExpectedSha256 $caddyAsset.sha256 `
    -AssetName "Caddy" `
    -Force:$ForceDownload

Get-PinnedAsset `
    -DownloadUrl $winswAsset.download_url `
    -DestinationPath $winswCachedExecutable `
    -ExpectedSha256 $winswAsset.sha256 `
    -AssetName "WinSW" `
    -Force:$ForceDownload

$caddyOutputDirectory = Join-Path `
    $resolvedOutputDirectory `
    "caddy"

$winswOutputDirectory = Join-Path `
    $resolvedOutputDirectory `
    "winsw"

New-Item `
    -ItemType Directory `
    -Path $caddyOutputDirectory `
    -Force |
Out-Null

New-Item `
    -ItemType Directory `
    -Path $winswOutputDirectory `
    -Force |
Out-Null

$caddyExtractionDirectory = Join-Path `
    $resolvedOutputDirectory `
    ".caddy-extract"

Remove-Item `
    -LiteralPath $caddyExtractionDirectory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

try {
    Write-Status "Extracting Caddy..."

    Expand-Archive `
        -LiteralPath $caddyCachedArchive `
        -DestinationPath $caddyExtractionDirectory `
        -Force

    $extractedCaddyExecutable = Join-Path `
        $caddyExtractionDirectory `
        $caddyAsset.executable_name

    if (
        -not (
            Test-Path `
                -LiteralPath $extractedCaddyExecutable `
                -PathType Leaf
        )
    ) {
        throw (
            "The Caddy archive does not contain " +
            "$($caddyAsset.executable_name)."
        )
    }

    $stagedCaddyExecutable = Join-Path `
        $caddyOutputDirectory `
        $caddyAsset.executable_name

    Copy-Item `
        -LiteralPath $extractedCaddyExecutable `
        -Destination $stagedCaddyExecutable `
        -Force
}
finally {
    Remove-Item `
        -LiteralPath $caddyExtractionDirectory `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue
}

$stagedWinSWExecutable = Join-Path `
    $winswOutputDirectory `
    $winswAsset.file_name

Copy-Item `
    -LiteralPath $winswCachedExecutable `
    -Destination $stagedWinSWExecutable `
    -Force

Write-Status "Validating staged Caddy..."

$caddyVersionOutput = (
    & $stagedCaddyExecutable version
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw (
        "Caddy version validation failed with exit code " +
        "$LASTEXITCODE."
    )
}

$expectedCaddyVersionPrefix = "v$($caddyAsset.version) "

if (
    -not $caddyVersionOutput.StartsWith(
        $expectedCaddyVersionPrefix,
        [System.StringComparison]::Ordinal
    )
) {
    throw (
        "Unexpected Caddy version. " +
        "Expected: $($caddyAsset.version). " +
        "Output: $caddyVersionOutput"
    )
}

Write-Status "Validating staged WinSW..."

$winswVersionInfo = (
    Get-Item `
        -LiteralPath $stagedWinSWExecutable
).VersionInfo

$winswFileVersion = $winswVersionInfo.FileVersion

if (
    -not $winswFileVersion.StartsWith(
        "$($winswAsset.version).",
        [System.StringComparison]::Ordinal
    )
) {
    throw (
        "Unexpected WinSW version. " +
        "Expected: $($winswAsset.version). " +
        "File version: $winswFileVersion"
    )
}

$manifestPath = Join-Path `
    $resolvedOutputDirectory `
    "SHA256SUMS.txt"

$manifestFiles = @(
    $stagedCaddyExecutable
    $stagedWinSWExecutable
)

$manifestLines = foreach ($manifestFile in $manifestFiles) {
    $fileHash = Get-FileHash `
        -LiteralPath $manifestFile `
        -Algorithm SHA256

    $relativePath = (
        $manifestFile.Substring(
            $resolvedOutputDirectory.Length
        ).TrimStart(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
    ).Replace("\", "/")

    "{0}  {1}" -f `
        $fileHash.Hash.ToLowerInvariant(), `
        $relativePath
}

$manifestLines |
Set-Content `
    -LiteralPath $manifestPath `
    -Encoding ascii

$metadataPath = Join-Path `
    $resolvedOutputDirectory `
    "versions.json"

$metadata = [ordered]@{
    schema_version = 1
    caddy = [ordered]@{
        version = [string]$caddyAsset.version
        version_output = $caddyVersionOutput
        executable = "caddy/$($caddyAsset.executable_name)"
    }
    winsw = [ordered]@{
        version = [string]$winswAsset.version
        file_version = $winswFileVersion
        product_version = $winswVersionInfo.ProductVersion
        executable = "winsw/$($winswAsset.file_name)"
    }
}

$metadata |
ConvertTo-Json `
    -Depth 4 |
Set-Content `
    -LiteralPath $metadataPath `
    -Encoding utf8

Write-Status ""
Write-Status "CareQueue vendor assets staged successfully."
Write-Status "Output:   $resolvedOutputDirectory"
Write-Status "Caddy:    $caddyVersionOutput"
Write-Status "WinSW:    $winswFileVersion"
Write-Status "Manifest: $manifestPath"
Write-Status "Metadata: $metadataPath"
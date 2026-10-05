[CmdletBinding()]
param(
    [string]$Version = "0.7.0"
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot "..\..\.."
    )
).Path

$buildRoot = Join-Path `
    $repositoryRoot `
    "build\linux"

$stagingDirectory = Join-Path `
    $buildRoot `
    "staging"

$outputDirectory = Join-Path `
    $buildRoot `
    "installer"

$packageName = "CareQFlow-Linux-Setup-$Version.tar.gz"

$packagePath = Join-Path `
    $outputDirectory `
    $packageName

$frontendDist = Join-Path `
    $repositoryRoot `
    "frontend\dist"

$requiredPaths = @(
    "LICENSE"
    "LICENSES\BUSL-1.1.txt"
    "LICENSES\MIT.txt"
    "backend\authstatus_api"
    "backend\scripts"
    "backend\requirements.txt"
    "frontend\dist\index.html"
    "deployment\linux\Caddyfile"
    "deployment\linux\CareQFlow-AdminSetup.sh"
    "deployment\linux\install-production.sh"
    "deployment\linux\uninstall-production.sh"
    "deployment\linux\installer\invoke-install.sh"
    "deployment\linux\systemd\carequeue-api.service"
    "deployment\linux\systemd\carequeue-caddy.service"
    "deployment\linux\systemd\carequeue-backup.service"
    "deployment\linux\systemd\carequeue-backup.timer"
    "deployment\linux\networking\Set-CareQFlowNetworkAccess.sh"
    "deployment\linux\networking\Export-CareQFlowClientTrust.sh"
    "deployment\linux\networking\Install-CareQFlowClientTrust.sh"
)

Write-Host "Validating CareQFlow Linux payload sources..."

foreach ($relativePath in $requiredPaths) {
    $fullPath = Join-Path `
        $repositoryRoot `
        $relativePath

    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw (
            "Required Linux payload source was not found: " +
            $relativePath
        )
    }
}

if (-not (Test-Path -LiteralPath $frontendDist)) {
    throw (
        "The production frontend has not been built. " +
        "Run npm ci and npm run build in frontend first."
    )
}

Write-Host "Preparing Linux staging directory..."

if (Test-Path -LiteralPath $stagingDirectory) {
    Remove-Item `
        -LiteralPath $stagingDirectory `
        -Recurse `
        -Force
}

New-Item `
    -ItemType Directory `
    -Path $stagingDirectory `
    -Force |
Out-Null

New-Item `
    -ItemType Directory `
    -Path $outputDirectory `
    -Force |
Out-Null

$backendDestination = Join-Path `
    $stagingDirectory `
    "backend"

$frontendDestination = Join-Path `
    $stagingDirectory `
    "frontend\dist"

$licenseNoticeDestination = Join-Path `
    $stagingDirectory `
    "LICENSE"

<#
$licenseTextsDestination = Join-Path `
    $stagingDirectory `
    "LICENSES"

$deploymentDestination = Join-Path `
    $stagingDirectory `
    "deployment"
#>

Write-Host "Copying backend production files..."

New-Item `
    -ItemType Directory `
    -Path $backendDestination `
    -Force |
Out-Null

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "backend\authstatus_api"
) `
    -Destination $backendDestination `
    -Recurse `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "backend\scripts"
) `
    -Destination $backendDestination `
    -Recurse `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "backend\requirements.txt"
) `
    -Destination $backendDestination `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "backend\pyproject.toml"
) `
    -Destination $backendDestination `
    -Force

Write-Host "Copying prebuilt frontend..."

New-Item `
    -ItemType Directory `
    -Path $frontendDestination `
    -Force |
Out-Null

Copy-Item `
    -Path (
    Join-Path $frontendDist "*"
) `
    -Destination $frontendDestination `
    -Recurse `
    -Force

Write-Host "Copying Linux deployment files..."

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "deployment"
) `
    -Destination $stagingDirectory `
    -Recurse `
    -Force

Write-Host "Copying CareQFlow licensing files..."

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "LICENSE"
) `
    -Destination $licenseNoticeDestination `
    -Force
    
Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "LICENSES"
) `
    -Destination $stagingDirectory `
    -Recurse `
    -Force

Write-Host "Writing CareQFlow release metadata..."

$releaseMetadataPath = Join-Path `
    $stagingDirectory `
    "carequeue-release.env"

$releaseMetadata = @(
    "CAREQUEUE_RELEASE_METADATA_SCHEMA=1"
    "CAREQUEUE_APP_VERSION=$Version"
    "CAREQUEUE_PACKAGE_PLATFORM=linux"
    "CAREQUEUE_LICENSE_NOTICE=LICENSE"
    "CAREQUEUE_LICENSE_TEXTS=LICENSES"
) -join "`n"

[System.IO.File]::WriteAllText(
    $releaseMetadataPath,
    $releaseMetadata + "`n",
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Normalizing Linux text files to LF..."

$textFiles = Get-ChildItem `
    -LiteralPath (
    Join-Path $stagingDirectory "deployment\linux"
) `
    -File `
    -Recurse |
Where-Object {
    $_.Extension -in @(
        ".sh",
        ".service",
        ".timer"
    ) -or $_.Name -eq "Caddyfile"
}

$utf8NoBom = New-Object `
    System.Text.UTF8Encoding($false)

foreach ($file in $textFiles) {
    $content = [System.IO.File]::ReadAllText(
        $file.FullName
    )

    $content = $content `
        -replace "`r`n", "`n" `
        -replace "`r", "`n"

    [System.IO.File]::WriteAllText(
        $file.FullName,
        $content,
        $utf8NoBom
    )
}

Write-Host "Creating Linux installer package..."

if (Test-Path -LiteralPath $packagePath) {
    Remove-Item `
        -LiteralPath $packagePath `
        -Force
}

$pythonCommand = Get-Command `
    python `
    -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    throw (
        "Python is required to create the Linux installer package " +
        "with normalized archive permissions."
    )
}

$tarScript = @'
from __future__ import annotations

from pathlib import Path, PurePosixPath
import sys
import tarfile

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()


def normalize_member(member: tarfile.TarInfo) -> tarfile.TarInfo:
    path = PurePosixPath(member.name)

    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe archive path: {member.name}")

    if member.issym() or member.islnk():
        raise ValueError(f"Links are not permitted: {member.name}")

    if not (member.isdir() or member.isfile()):
        raise ValueError(
            f"Unsupported archive entry type: {member.name}"
        )

    member.uid = 0
    member.gid = 0
    member.uname = "root"
    member.gname = "root"
    member.mode = 0o755 if member.isdir() else 0o644

    return member


with tarfile.open(destination, "w:gz") as archive:
    archive.add(
        source,
        arcname=".",
        recursive=True,
        filter=normalize_member,
    )

with tarfile.open(destination, "r:gz") as archive:
    for member in archive.getmembers():
        if member.issym() or member.islnk():
            raise ValueError(
                f"Archive contains a link: {member.name}"
            )

        if member.isdir():
            expected_mode = 0o755
        elif member.isfile():
            expected_mode = 0o644
        else:
            raise ValueError(
                "Archive contains an unsupported entry type: "
                f"{member.name}"
            )

        actual_mode = member.mode & 0o777

        if actual_mode != expected_mode:
            raise ValueError(
                f"Unsafe mode {actual_mode:o} for {member.name}; "
                f"expected {expected_mode:o}"
            )
'@

$tarScript | & $pythonCommand.Source `
    - `
    $stagingDirectory `
    $packagePath

if ($LASTEXITCODE -ne 0) {
    throw (
        "Unable to create a permission-normalized Linux installer package. " +
        "Python exited with code " +
        $LASTEXITCODE
    )
}

if (-not (Test-Path -LiteralPath $packagePath)) {
    throw "Linux installer package was not created."
}

$package = Get-Item `
    -LiteralPath $packagePath

$hash = Get-FileHash `
    -LiteralPath $packagePath `
    -Algorithm SHA256

$checksumPath = "$packagePath.sha256"

"{0}  {1}" -f `
    $hash.Hash.ToLowerInvariant(), `
    $package.Name |
Set-Content `
    -LiteralPath $checksumPath `
    -Encoding ascii

Write-Host ""
Write-Host "CareQFlow Linux installer package created successfully."
Write-Host "Package:  $($package.FullName)"
Write-Host "Size:     $($package.Length) bytes"
Write-Host "SHA256:   $($hash.Hash)"
Write-Host "Checksum: $checksumPath"
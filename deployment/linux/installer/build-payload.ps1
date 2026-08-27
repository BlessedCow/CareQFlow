[CmdletBinding()]
param(
    [string]$Version = "0.3.0"
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

$packageName = "CareQueue-Linux-Setup-$Version.tar.gz"

$packagePath = Join-Path `
    $outputDirectory `
    $packageName

$frontendDist = Join-Path `
    $repositoryRoot `
    "frontend\dist"

$requiredPaths = @(
    "backend\authstatus_api"
    "backend\scripts"
    "backend\requirements.txt"
    "frontend\dist\index.html"
    "deployment\linux\Caddyfile"
    "deployment\linux\CareQueue-AdminSetup.sh"
    "deployment\linux\install-production.sh"
    "deployment\linux\uninstall-production.sh"
    "deployment\linux\installer\invoke-install.sh"
    "deployment\linux\systemd\carequeue-api.service"
    "deployment\linux\systemd\carequeue-caddy.service"
    "deployment\linux\systemd\carequeue-backup.service"
    "deployment\linux\systemd\carequeue-backup.timer"
)

Write-Host "Validating CareQueue Linux payload sources..."

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

<#
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

Write-Host "Writing CareQueue release metadata..."

$releaseMetadataPath = Join-Path `
    $stagingDirectory `
    "carequeue-release.env"

$releaseMetadata = @(
    "CAREQUEUE_RELEASE_METADATA_SCHEMA=1"
    "CAREQUEUE_APP_VERSION=$Version"
    "CAREQUEUE_PACKAGE_PLATFORM=linux"
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

& tar.exe `
    -czf $packagePath `
    -C $stagingDirectory `
    .

if ($LASTEXITCODE -ne 0) {
    throw (
        "tar.exe failed with exit code " +
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
Write-Host "CareQueue Linux installer package created successfully."
Write-Host "Package:  $($package.FullName)"
Write-Host "Size:     $($package.Length) bytes"
Write-Host "SHA256:   $($hash.Hash)"
Write-Host "Checksum: $checksumPath"
[CmdletBinding()]
param(
    [string]$Version = "0.5.0"
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot "..\..\.."
    )
).Path

$productionBuilder = Join-Path `
    $PSScriptRoot `
    "build-payload.ps1"

$buildRoot = Join-Path `
    $repositoryRoot `
    "build\linux"

$outputDirectory = Join-Path `
    $buildRoot `
    "installer"

$testStagingDirectory = Join-Path `
    $buildRoot `
    "test-staging"

$productionPackageName = "CareQFlow-Linux-Setup-$Version.tar.gz"

$productionPackagePath = Join-Path `
    $outputDirectory `
    $productionPackageName

$testPackageName = "CareQFlow-Linux-Test-$Version.tar.gz"

$testPackagePath = Join-Path `
    $outputDirectory `
    $testPackageName

$requiredTestPaths = @(
    "backend\tests"
    "backend\requirements-dev.txt"
)

Write-Host "Validating CareQFlow Linux test payload sources..."

if (-not (Test-Path -LiteralPath $productionBuilder)) {
    throw "Linux production package builder was not found."
}

foreach ($relativePath in $requiredTestPaths) {
    $fullPath = Join-Path `
        $repositoryRoot `
        $relativePath

    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw (
            "Required Linux test payload source was not found: " +
            $relativePath
        )
    }
}

Write-Host "Building CareQFlow Linux production payload..."

& $productionBuilder `
    -Version $Version

if ($LASTEXITCODE -ne 0) {
    throw (
        "Linux production package builder failed with exit code " +
        $LASTEXITCODE
    )
}

if (-not (Test-Path -LiteralPath $productionPackagePath)) {
    throw (
        "Expected Linux production package was not created: " +
        $productionPackagePath
    )
}

Write-Host "Preparing Linux test staging directory..."

if (Test-Path -LiteralPath $testStagingDirectory) {
    Remove-Item `
        -LiteralPath $testStagingDirectory `
        -Recurse `
        -Force
}

New-Item `
    -ItemType Directory `
    -Path $testStagingDirectory `
    -Force |
Out-Null

Write-Host "Extracting production payload into test staging..."

& tar.exe `
    -xzf $productionPackagePath `
    -C $testStagingDirectory

if ($LASTEXITCODE -ne 0) {
    throw (
        "tar.exe failed while extracting the production package with exit code " +
        $LASTEXITCODE
    )
}

$backendDestination = Join-Path `
    $testStagingDirectory `
    "backend"

if (-not (Test-Path -LiteralPath $backendDestination)) {
    throw "Extracted Linux production payload does not contain backend."
}

Write-Host "Adding CareQFlow Linux test files..."

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "backend\tests"
) `
    -Destination $backendDestination `
    -Recurse `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $repositoryRoot "backend\requirements-dev.txt"
) `
    -Destination $backendDestination `
    -Force

    Write-Host "Removing local Python cache artifacts from test payload..."

    Get-ChildItem `
        -LiteralPath $testStagingDirectory `
        -Directory `
        -Recurse `
        -Force |
    Where-Object {
        $_.Name -eq "__pycache__"
    } |
    Remove-Item `
        -Recurse `
        -Force
    
    Get-ChildItem `
        -LiteralPath $testStagingDirectory `
        -File `
        -Recurse `
        -Force |
    Where-Object {
        $_.Extension -in @(".pyc", ".pyo")
    } |
    Remove-Item `
        -Force

Write-Host "Creating CareQFlow Linux test package..."

if (Test-Path -LiteralPath $testPackagePath) {
    Remove-Item `
        -LiteralPath $testPackagePath `
        -Force
}

& tar.exe `
    -czf $testPackagePath `
    -C $testStagingDirectory `
    .

if ($LASTEXITCODE -ne 0) {
    throw (
        "tar.exe failed while creating the test package with exit code " +
        $LASTEXITCODE
    )
}

if (-not (Test-Path -LiteralPath $testPackagePath)) {
    throw "Linux test package was not created."
}

$package = Get-Item `
    -LiteralPath $testPackagePath

$hash = Get-FileHash `
    -LiteralPath $testPackagePath `
    -Algorithm SHA256

$checksumPath = "$testPackagePath.sha256"

"{0}  {1}" -f `
    $hash.Hash.ToLowerInvariant(), `
    $package.Name |
Set-Content `
    -LiteralPath $checksumPath `
    -Encoding ascii

Write-Host ""
Write-Host "CareQFlow Linux test package created successfully."
Write-Host "Package:  $($package.FullName)"
Write-Host "Size:     $($package.Length) bytes"
Write-Host "SHA256:   $($hash.Hash)"
Write-Host "Checksum: $checksumPath"
Write-Host ""
Write-Host "This package includes development tests and is not a production release artifact."
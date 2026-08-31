[CmdletBinding()]
param(
    [string]$PythonExecutable = "python",

    [string]$OutputDirectory,

    [switch]$KeepExisting
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = (
    Resolve-Path `
        -LiteralPath (
            Join-Path `
                $PSScriptRoot `
                "..\..\.."
        )
).Path

$requirementsFile = Join-Path `
    $repositoryRoot `
    "backend\requirements.txt"

if (
    -not (
        Test-Path `
            -LiteralPath $requirementsFile `
            -PathType Leaf
    )
) {
    throw (
        "The backend requirements file was not found: " +
        $requirementsFile
    )
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path `
        $repositoryRoot `
        "build\windows\wheelhouse"
}

$resolvedPythonCommand = Get-Command `
    $PythonExecutable `
    -ErrorAction SilentlyContinue

if (-not $resolvedPythonCommand) {
    throw (
        "The requested Python executable was not found: " +
        $PythonExecutable
    )
}

if (
    (Test-Path -LiteralPath $OutputDirectory) `
        -and -not $KeepExisting
) {
    Write-Host "Removing the existing wheelhouse..."

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

Write-Host "Building the CareQFlow backend wheelhouse..."
Write-Host "Python:      $($resolvedPythonCommand.Source)"
Write-Host "Requirements: $requirementsFile"
Write-Host "Output:       $resolvedOutputDirectory"

& $resolvedPythonCommand.Source `
    -m `
    pip `
    download `
    --disable-pip-version-check `
    --no-input `
    --only-binary=:all: `
    --requirement $requirementsFile `
    --dest $resolvedOutputDirectory

if ($LASTEXITCODE -ne 0) {
    throw (
        "Backend dependency download failed with exit code " +
        "$LASTEXITCODE."
    )
}

$wheelFiles = @(
    Get-ChildItem `
        -LiteralPath $resolvedOutputDirectory `
        -Filter "*.whl" `
        -File
)

if ($wheelFiles.Count -eq 0) {
    throw (
        "The wheelhouse build completed without producing any " +
        "wheel files."
    )
}

$unexpectedFiles = @(
    Get-ChildItem `
        -LiteralPath $resolvedOutputDirectory `
        -File |
    Where-Object {
        $_.Extension -ne ".whl"
    }
)

if ($unexpectedFiles.Count -gt 0) {
    $unexpectedNames = (
        $unexpectedFiles.Name |
        Sort-Object
    ) -join ", "

    throw (
        "The wheelhouse contains non-wheel files: " +
        $unexpectedNames
    )
}

$manifestPath = Join-Path `
    $resolvedOutputDirectory `
    "SHA256SUMS.txt"

$manifestLines = foreach (
    $wheelFile in (
        $wheelFiles |
        Sort-Object Name
    )
) {
    $fileHash = Get-FileHash `
        -LiteralPath $wheelFile.FullName `
        -Algorithm SHA256

    "{0}  {1}" -f `
        $fileHash.Hash.ToLowerInvariant(), `
        $wheelFile.Name
}

$manifestLines |
Set-Content `
    -LiteralPath $manifestPath `
    -Encoding ascii

Write-Host ""
Write-Host "CareQFlow backend wheelhouse created successfully."
Write-Host "Wheel count: $($wheelFiles.Count)"
Write-Host "Manifest:    $manifestPath"
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$EmbeddedPythonArchive,

    [string]$BuildPythonExecutable = "python",

    [string]$WheelDirectory,

    [string]$OutputDirectory,

    [switch]$KeepExisting
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Executable,

        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    & $Executable @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw (
            $FailureMessage +
            " Exit code: $LASTEXITCODE"
        )
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

$resolvedArchive = (
    Resolve-Path `
        -LiteralPath $EmbeddedPythonArchive `
        -ErrorAction Stop
).Path

if (
    [System.IO.Path]::GetExtension($resolvedArchive) `
        -ne ".zip"
) {
    throw (
        "The embedded Python runtime must be supplied as a ZIP archive: " +
        $resolvedArchive
    )
}

$buildPythonCommand = Get-Command `
    $BuildPythonExecutable `
    -ErrorAction SilentlyContinue

if (-not $buildPythonCommand) {
    throw (
        "The build Python executable was not found: " +
        $BuildPythonExecutable
    )
}

$resolvedBuildPython = $buildPythonCommand.Source

if (-not $WheelDirectory) {
    $WheelDirectory = Join-Path `
        $repositoryRoot `
        "build\windows\wheelhouse"
}

$resolvedWheelDirectory = (
    Resolve-Path `
        -LiteralPath $WheelDirectory `
        -ErrorAction Stop
).Path

$wheelFiles = @(
    Get-ChildItem `
        -LiteralPath $resolvedWheelDirectory `
        -Filter "*.whl" `
        -File `
        -ErrorAction Stop
)

if ($wheelFiles.Count -eq 0) {
    throw (
        "The backend wheel directory does not contain any wheel files: " +
        $resolvedWheelDirectory
    )
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path `
        $repositoryRoot `
        "build\windows\python-runtime"
}

if (
    (Test-Path -LiteralPath $OutputDirectory) `
        -and -not $KeepExisting
) {
    Write-Host "Removing the existing private Python runtime..."

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

Write-Host "Extracting the embedded Python runtime..."

Expand-Archive `
    -LiteralPath $resolvedArchive `
    -DestinationPath $resolvedOutputDirectory `
    -Force

$runtimePython = Join-Path `
    $resolvedOutputDirectory `
    "python.exe"

if (
    -not (
        Test-Path `
            -LiteralPath $runtimePython `
            -PathType Leaf
    )
) {
    throw (
        "The extracted runtime does not contain python.exe: " +
        $resolvedOutputDirectory
    )
}

$buildVersion = (
    & $resolvedBuildPython `
        -c (
            "import platform, sys; " +
            "print(f'{sys.version_info.major}.{sys.version_info.minor}|" +
            "{platform.architecture()[0]}')"
        )
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw "Unable to determine the build Python version."
}

$runtimeVersion = (
    & $runtimePython `
        -c (
            "import platform, sys; " +
            "print(f'{sys.version_info.major}.{sys.version_info.minor}|" +
            "{platform.architecture()[0]}')"
        )
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw "Unable to determine the embedded Python version."
}

if ($buildVersion -ne $runtimeVersion) {
    throw (
        "The build Python and embedded Python runtime must have the " +
        "same major version, minor version, and architecture. " +
        "Build Python: $buildVersion. " +
        "Embedded runtime: $runtimeVersion."
    )
}

$pathConfigurationFiles = @(
    Get-ChildItem `
        -LiteralPath $resolvedOutputDirectory `
        -Filter "python*._pth" `
        -File
)

if ($pathConfigurationFiles.Count -ne 1) {
    throw (
        "Expected exactly one embedded Python path configuration file, " +
        "but found $($pathConfigurationFiles.Count)."
    )
}

$pathConfigurationFile = $pathConfigurationFiles[0].FullName

$standardLibraryArchive = @(
    Get-ChildItem `
        -LiteralPath $resolvedOutputDirectory `
        -Filter "python*.zip" `
        -File
)

if ($standardLibraryArchive.Count -ne 1) {
    throw (
        "Expected exactly one embedded Python standard-library archive, " +
        "but found $($standardLibraryArchive.Count)."
    )
}

$standardLibraryArchiveName = $standardLibraryArchive[0].Name

$sitePackagesDirectory = Join-Path `
    $resolvedOutputDirectory `
    "Lib\site-packages"

New-Item `
    -ItemType Directory `
    -Path $sitePackagesDirectory `
    -Force |
Out-Null

$pathConfiguration = @(
    $standardLibraryArchiveName
    "."
    "Lib"
    "Lib\site-packages"
    "..\..\backend"
    "import site"
)

$pathConfiguration |
Set-Content `
    -LiteralPath $pathConfigurationFile `
    -Encoding ascii

Write-Host "Installing backend dependencies into the private runtime..."

Invoke-CheckedCommand `
    -Executable $resolvedBuildPython `
    -Arguments @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--no-index",
        "--find-links",
        $resolvedWheelDirectory,
        "--requirement",
        $requirementsFile,
        "--target",
        $sitePackagesDirectory
    ) `
    -FailureMessage (
        "Private Python runtime dependency installation failed."
    )

Write-Host "Validating the private Python runtime..."

Invoke-CheckedCommand `
    -Executable $runtimePython `
    -Arguments @(
        "-c",
        (
            "import cryptography; " +
            "import fastapi; " +
            "import pydantic; " +
            "import uvicorn; " +
            "print('CareQueue private Python runtime validated.')"
        )
    ) `
    -FailureMessage (
        "The private Python runtime could not import required packages."
    )

$manifestPath = Join-Path `
    $resolvedOutputDirectory `
    "SHA256SUMS.txt"

$manifestFiles = @(
    Get-ChildItem `
        -LiteralPath $resolvedOutputDirectory `
        -File `
        -Recurse |
    Where-Object {
        $_.FullName -ne $manifestPath
    } |
    Sort-Object FullName
)

$manifestLines = foreach ($manifestFile in $manifestFiles) {
    $relativePath = (
        $manifestFile.FullName.Substring(
            $resolvedOutputDirectory.Length
        ).TrimStart(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
    )

    $fileHash = Get-FileHash `
        -LiteralPath $manifestFile.FullName `
        -Algorithm SHA256

    "{0}  {1}" -f `
        $fileHash.Hash.ToLowerInvariant(), `
        $relativePath.Replace("\", "/")
}

$manifestLines |
Set-Content `
    -LiteralPath $manifestPath `
    -Encoding ascii

Write-Host ""
Write-Host "CareQueue private Python runtime created successfully."
Write-Host "Runtime:  $resolvedOutputDirectory"
Write-Host "Python:   $runtimeVersion"
Write-Host "Manifest: $manifestPath"
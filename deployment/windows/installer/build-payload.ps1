[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$EmbeddedPythonArchive,

    [string]$BuildPythonExecutable = "python",

    [string]$OutputDirectory,

    [switch]$KeepExisting,

    [switch]$ForceVendorDownload
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

$resolvedEmbeddedPythonArchive = (
    Resolve-Path `
        -LiteralPath $EmbeddedPythonArchive `
        -ErrorAction Stop
).Path

if (
    -not (
        Test-Path `
            -LiteralPath $resolvedEmbeddedPythonArchive `
            -PathType Leaf
    )
) {
    throw (
        "The embedded Python archive was not found: " +
        $resolvedEmbeddedPythonArchive
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

$npmCommand = Get-Command `
    "npm" `
    -ErrorAction SilentlyContinue

if (-not $npmCommand) {
    throw "npm was not found on PATH."
}

$wheelhouseBuilder = Join-Path `
    $PSScriptRoot `
    "build-wheelhouse.ps1"

$pythonRuntimeBuilder = Join-Path `
    $PSScriptRoot `
    "build-python-runtime.ps1"

$vendorAssetBuilder = Join-Path `
    $PSScriptRoot `
    "build-vendor-assets.ps1"

$requiredBuilderPaths = @(
    $wheelhouseBuilder,
    $pythonRuntimeBuilder,
    $vendorAssetBuilder
)

foreach ($requiredBuilderPath in $requiredBuilderPaths) {
    if (
        -not (
            Test-Path `
                -LiteralPath $requiredBuilderPath `
                -PathType Leaf
        )
    ) {
        throw (
            "A required installer builder was not found: " +
            $requiredBuilderPath
        )
    }
}

$frontendSourceDirectory = Join-Path `
    $repositoryRoot `
    "frontend"

$backendSourceDirectory = Join-Path `
    $repositoryRoot `
    "backend"

$deploymentSourceDirectory = Join-Path `
    $repositoryRoot `
    "deployment\windows"

$licenseNoticePath = Join-Path `
    $repositoryRoot `
    "LICENSE"

$licenseTextsDirectory = Join-Path `
    $repositoryRoot `
    "LICENSES"

$requiredSourcePaths = @(
    (Join-Path $frontendSourceDirectory "package.json"),
    (Join-Path $frontendSourceDirectory "package-lock.json"),
    (Join-Path $backendSourceDirectory "authstatus_api"),
    (Join-Path $backendSourceDirectory "scripts"),
    (Join-Path $backendSourceDirectory "requirements.txt"),
    (Join-Path $deploymentSourceDirectory "install-production.ps1"),
    (Join-Path $deploymentSourceDirectory "run-api.ps1"),
    (Join-Path $deploymentSourceDirectory "CareQueueApi.xml"),
    (Join-Path $deploymentSourceDirectory "CareQueueCaddy.xml"),
    (Join-Path $deploymentSourceDirectory "Caddyfile"),
    $licenseNoticePath,
    (Join-Path $licenseTextsDirectory "BUSL-1.1.txt"),
    (Join-Path $licenseTextsDirectory "MIT.txt")
)

foreach ($requiredSourcePath in $requiredSourcePaths) {
    if (-not (Test-Path -LiteralPath $requiredSourcePath)) {
        throw (
            "A required payload source was not found: " +
            $requiredSourcePath
        )
    }
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path `
        $repositoryRoot `
        "build\windows\payload"
}

if (
    (Test-Path -LiteralPath $OutputDirectory) `
        -and -not $KeepExisting
) {
    Write-Status "Removing the existing Windows payload..."

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

$componentBuildRoot = Join-Path `
    $repositoryRoot `
    "build\windows\components"

$wheelhouseBuildDirectory = Join-Path `
    $componentBuildRoot `
    "wheelhouse"

$pythonRuntimeBuildDirectory = Join-Path `
    $componentBuildRoot `
    "python-runtime"

$vendorBuildDirectory = Join-Path `
    $componentBuildRoot `
    "vendor"

$payloadBackendDirectory = Join-Path `
    $resolvedOutputDirectory `
    "backend"

$payloadFrontendDirectory = Join-Path `
    $resolvedOutputDirectory `
    "frontend"

$payloadFrontendBuildDirectory = Join-Path `
    $payloadFrontendDirectory `
    "dist"

$payloadDeploymentDirectory = Join-Path `
    $resolvedOutputDirectory `
    "deployment"

$payloadWindowsDeploymentDirectory = Join-Path `
    $payloadDeploymentDirectory `
    "windows"

$payloadRuntimeDirectory = Join-Path `
    $resolvedOutputDirectory `
    "runtime"

$payloadPythonRuntimeDirectory = Join-Path `
    $payloadRuntimeDirectory `
    "python"

$payloadVendorDirectory = Join-Path `
    $resolvedOutputDirectory `
    "vendor"

$payloadLicenseTextsDirectory = Join-Path `
    $resolvedOutputDirectory `
    "LICENSES"

$payloadDependenciesDirectory = Join-Path `
    $resolvedOutputDirectory `
    "dependencies"

$payloadWheelhouseDirectory = Join-Path `
    $payloadDependenciesDirectory `
    "wheelhouse"

Write-Status "Building the offline backend wheelhouse..."

& $wheelhouseBuilder `
    -PythonExecutable $buildPythonCommand.Source `
    -OutputDirectory $wheelhouseBuildDirectory

if ($LASTEXITCODE -ne 0) {
    throw (
        "The wheelhouse builder failed with exit code " +
        "$LASTEXITCODE."
    )
}

Write-Status "Building the private Python runtime..."

& $pythonRuntimeBuilder `
    -EmbeddedPythonArchive $resolvedEmbeddedPythonArchive `
    -BuildPythonExecutable $buildPythonCommand.Source `
    -WheelDirectory $wheelhouseBuildDirectory `
    -OutputDirectory $pythonRuntimeBuildDirectory

if ($LASTEXITCODE -ne 0) {
    throw (
        "The private Python runtime builder failed with exit code " +
        "$LASTEXITCODE."
    )
}

Write-Status "Staging the pinned vendor binaries..."

$vendorBuilderArguments = @{
    OutputDirectory = $vendorBuildDirectory
}

if ($ForceVendorDownload) {
    $vendorBuilderArguments.ForceDownload = $true
}

& $vendorAssetBuilder @vendorBuilderArguments

if ($LASTEXITCODE -ne 0) {
    throw (
        "The vendor asset builder failed with exit code " +
        "$LASTEXITCODE."
    )
}

Write-Status "Building the production frontend..."

$frontendEnvironmentFiles = @(
    ".env",
    ".env.local",
    ".env.production",
    ".env.production.local"
)

$temporarilyMovedEnvironmentFiles = @()
$previousApiBaseUrl = $env:VITE_AUTHSTATUS_API_BASE_URL
$previousLegacyApiBaseUrl = $env:VITE_API_BASE_URL

Push-Location $frontendSourceDirectory

try {
    foreach ($environmentFileName in $frontendEnvironmentFiles) {
        $environmentFilePath = Join-Path `
            $frontendSourceDirectory `
            $environmentFileName

        if (
            Test-Path `
                -LiteralPath $environmentFilePath `
                -PathType Leaf
        ) {
            $temporaryEnvironmentFilePath = (
                $environmentFilePath +
                ".carequeue-payload-backup"
            )

            Move-Item `
                -LiteralPath $environmentFilePath `
                -Destination $temporaryEnvironmentFilePath `
                -Force

            $temporarilyMovedEnvironmentFiles += (
                [PSCustomObject]@{
                    OriginalPath  = $environmentFilePath
                    TemporaryPath = $temporaryEnvironmentFilePath
                }
            )
        }
    }

    Remove-Item `
        Env:VITE_AUTHSTATUS_API_BASE_URL `
        -ErrorAction SilentlyContinue

    Remove-Item `
        Env:VITE_API_BASE_URL `
        -ErrorAction SilentlyContinue

    Invoke-CheckedCommand `
        -Executable $npmCommand.Source `
        -Arguments @("ci") `
        -FailureMessage (
        "Frontend dependency installation failed."
    )

    Invoke-CheckedCommand `
        -Executable $npmCommand.Source `
        -Arguments @("run", "build") `
        -FailureMessage "Frontend production build failed."
}
finally {
    foreach (
        $movedEnvironmentFile in
        $temporarilyMovedEnvironmentFiles
    ) {
        if (
            Test-Path `
                -LiteralPath $movedEnvironmentFile.TemporaryPath `
                -PathType Leaf
        ) {
            Move-Item `
                -LiteralPath $movedEnvironmentFile.TemporaryPath `
                -Destination $movedEnvironmentFile.OriginalPath `
                -Force
        }
    }

    if ($null -eq $previousApiBaseUrl) {
        Remove-Item `
            Env:VITE_AUTHSTATUS_API_BASE_URL `
            -ErrorAction SilentlyContinue
    }
    else {
        $env:VITE_AUTHSTATUS_API_BASE_URL = $previousApiBaseUrl
    }

    if ($null -eq $previousLegacyApiBaseUrl) {
        Remove-Item `
            Env:VITE_API_BASE_URL `
            -ErrorAction SilentlyContinue
    }
    else {
        $env:VITE_API_BASE_URL = $previousLegacyApiBaseUrl
    }

    Pop-Location
}

$frontendBuildDirectory = Join-Path `
    $frontendSourceDirectory `
    "dist"

$frontendIndexPath = Join-Path `
    $frontendBuildDirectory `
    "index.html"

if (
    -not (
        Test-Path `
            -LiteralPath $frontendIndexPath `
            -PathType Leaf
    )
) {
    throw (
        "The frontend production build does not contain index.html: " +
        $frontendBuildDirectory
    )
}

Write-Status "Assembling CareQFlow application files..."

$payloadDirectories = @(
    $payloadBackendDirectory,
    $payloadFrontendBuildDirectory,
    $payloadWindowsDeploymentDirectory,
    $payloadPythonRuntimeDirectory,
    $payloadVendorDirectory,
    $payloadWheelhouseDirectory,
    $payloadLicenseTextsDirectory
)

foreach ($payloadDirectory in $payloadDirectories) {
    New-Item `
        -ItemType Directory `
        -Path $payloadDirectory `
        -Force |
    Out-Null
}

Copy-Item `
    -LiteralPath (
    Join-Path $backendSourceDirectory "authstatus_api"
) `
    -Destination $payloadBackendDirectory `
    -Recurse `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $backendSourceDirectory "scripts"
) `
    -Destination $payloadBackendDirectory `
    -Recurse `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $backendSourceDirectory "requirements.txt"
) `
    -Destination $payloadBackendDirectory `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $frontendSourceDirectory "package.json"
) `
    -Destination $payloadFrontendDirectory `
    -Force

Copy-Item `
    -LiteralPath (
    Join-Path $frontendSourceDirectory "package-lock.json"
) `
    -Destination $payloadFrontendDirectory `
    -Force

Copy-Item `
    -Path (
    Join-Path $frontendBuildDirectory "*"
) `
    -Destination $payloadFrontendBuildDirectory `
    -Recurse `
    -Force

Copy-Item `
    -Path (
    Join-Path $deploymentSourceDirectory "*"
) `
    -Destination $payloadWindowsDeploymentDirectory `
    -Recurse `
    -Force

Copy-Item `
    -LiteralPath $licenseNoticePath `
    -Destination (
    Join-Path `
        $resolvedOutputDirectory `
        "LICENSE"
) `
    -Force

Copy-Item `
    -Path (
    Join-Path $licenseTextsDirectory "*"
) `
    -Destination $payloadLicenseTextsDirectory `
    -Recurse `
    -Force

Copy-Item `
    -Path (
    Join-Path $pythonRuntimeBuildDirectory "*"
) `
    -Destination $payloadPythonRuntimeDirectory `
    -Recurse `
    -Force

Copy-Item `
    -Path (
    Join-Path $vendorBuildDirectory "*"
) `
    -Destination $payloadVendorDirectory `
    -Recurse `
    -Force

Copy-Item `
    -Path (
    Join-Path $wheelhouseBuildDirectory "*"
) `
    -Destination $payloadWheelhouseDirectory `
    -Recurse `
    -Force

Write-Status "Validating the assembled payload..."

$payloadRequiredPaths = @(
    (Join-Path $resolvedOutputDirectory "LICENSE"),
    (
        Join-Path `
            $payloadLicenseTextsDirectory `
            "BUSL-1.1.txt"
    ),
    (
        Join-Path `
            $payloadLicenseTextsDirectory `
            "MIT.txt"
    ),
    (Join-Path $payloadBackendDirectory "authstatus_api"),
    (Join-Path $payloadBackendDirectory "scripts"),
    (Join-Path $payloadBackendDirectory "requirements.txt"),
    (Join-Path $payloadFrontendBuildDirectory "index.html"),
    (
        Join-Path `
            $payloadWindowsDeploymentDirectory `
            "install-production.ps1"
    ),
    (
        Join-Path `
            $payloadWindowsDeploymentDirectory `
            "CareQueueApi.xml"
    ),
    (
        Join-Path `
            $payloadWindowsDeploymentDirectory `
            "CareQueueCaddy.xml"
    ),
    (
        Join-Path `
            $payloadPythonRuntimeDirectory `
            "python.exe"
    ),
    (
        Join-Path `
            $payloadVendorDirectory `
            "caddy\caddy.exe"
    ),
    (
        Join-Path `
            $payloadVendorDirectory `
            "winsw\WinSW-x64.exe"
    ),
    (
        Join-Path `
            $payloadVendorDirectory `
            "versions.json"
    )
)

foreach ($payloadRequiredPath in $payloadRequiredPaths) {
    if (-not (Test-Path -LiteralPath $payloadRequiredPath)) {
        throw (
            "A required payload file was not assembled: " +
            $payloadRequiredPath
        )
    }
}

$payloadPythonExecutable = Join-Path `
    $payloadPythonRuntimeDirectory `
    "python.exe"

Invoke-CheckedCommand `
    -Executable $payloadPythonExecutable `
    -Arguments @(
    "-c",
    (
        "import authstatus_api; " +
        "import cryptography; " +
        "import fastapi; " +
        "import uvicorn; " +
        "print('CareQFlow payload runtime validated.')"
    )
) `
    -FailureMessage (
    "The assembled private runtime could not load CareQFlow."
)

$payloadCaddyExecutable = Join-Path `
    $payloadVendorDirectory `
    "caddy\caddy.exe"

Invoke-CheckedCommand `
    -Executable $payloadCaddyExecutable `
    -Arguments @("version") `
    -FailureMessage (
    "The assembled Caddy executable failed validation."
)

$payloadMetadataPath = Join-Path `
    $resolvedOutputDirectory `
    "payload.json"

$vendorMetadata = Get-Content `
    -LiteralPath (
    Join-Path $payloadVendorDirectory "versions.json"
) `
    -Raw |
ConvertFrom-Json

$pythonVersion = (
    & $payloadPythonExecutable `
        -c (
        "import platform, sys; " +
        "print(f'{sys.version_info.major}." +
        "{sys.version_info.minor}." +
        "{sys.version_info.micro}|{platform.architecture()[0]}')"
    )
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw "Unable to determine the payload Python version."
}

$payloadMetadata = [ordered]@{
    schema_version = 1
    created_utc    = [DateTime]::UtcNow.ToString("o")
    application    = [ordered]@{
        name            = "CareQueue"
        backend_version = "0.5.0"
    }
    runtime        = [ordered]@{
        python = $pythonVersion
    }
    vendor         = [ordered]@{
        caddy = [string]$vendorMetadata.caddy.version
        winsw = [string]$vendorMetadata.winsw.version
    }
    paths          = [ordered]@{
        frontend       = "frontend/dist"
        backend        = "backend"
        deployment     = "deployment/windows"
        python_runtime = "runtime/python"
        vendor         = "vendor"
        wheelhouse     = "dependencies/wheelhouse"
        license_notice = "LICENSE"
        license_texts  = "LICENSES"
    }
}

$payloadMetadata |
ConvertTo-Json `
    -Depth 5 |
Set-Content `
    -LiteralPath $payloadMetadataPath `
    -Encoding utf8

$payloadManifestPath = Join-Path `
    $resolvedOutputDirectory `
    "SHA256SUMS.txt"

$payloadManifestFiles = @(
    Get-ChildItem `
        -LiteralPath $resolvedOutputDirectory `
        -File `
        -Recurse |
    Where-Object {
        $_.FullName -ne $payloadManifestPath
    } |
    Sort-Object FullName
)

$payloadManifestLines = foreach (
    $payloadManifestFile in $payloadManifestFiles
) {
    $relativePath = (
        $payloadManifestFile.FullName.Substring(
            $resolvedOutputDirectory.Length
        ).TrimStart(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
    ).Replace("\", "/")

    $fileHash = Get-FileHash `
        -LiteralPath $payloadManifestFile.FullName `
        -Algorithm SHA256

    "{0}  {1}" -f `
        $fileHash.Hash.ToLowerInvariant(), `
        $relativePath
}

$payloadManifestLines |
Set-Content `
    -LiteralPath $payloadManifestPath `
    -Encoding ascii

Write-Status ""
Write-Status "CareQFlow Windows payload created successfully."
Write-Status "Payload:   $resolvedOutputDirectory"
Write-Status "Python:    $pythonVersion"
Write-Status "Caddy:     $($vendorMetadata.caddy.version)"
Write-Status "WinSW:     $($vendorMetadata.winsw.version)"
Write-Status "Metadata:  $payloadMetadataPath"
Write-Status "Manifest:  $payloadManifestPath"
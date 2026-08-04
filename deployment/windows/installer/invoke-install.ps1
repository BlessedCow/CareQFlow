[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern("^https://")]
    [string]$ApplicationOrigin,

    [string]$PayloadDirectory,

    [string]$InstallDirectory = "C:\Program Files\CareQueue",

    [string]$DataDirectory = "C:\ProgramData\CareQueue",

    [string]$LogDirectory = (
        "C:\ProgramData\CareQueue\Logs\Installer"
    ),

    [switch]$Force,

    [switch]$SkipPermissionHardening
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$exitCodeSuccess = 0
$exitCodeInvalidPayload = 10
$exitCodeAdministratorRequired = 20
$exitCodeLoggingFailure = 25
$exitCodeInstallationFailure = 30

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

function Write-InstallerResult {
    param(
        [Parameter(Mandatory)]
        [string]$Status,

        [Parameter(Mandatory)]
        [int]$ExitCode,

        [Parameter(Mandatory)]
        [string]$Message,

        [string]$LogPath
    )

    $result = [ordered]@{
        schema_version = 1
        status         = $Status
        exit_code      = $ExitCode
        message        = $Message
        log_path       = $LogPath
        completed_utc  = [DateTime]::UtcNow.ToString("o")
    }

    $result |
    ConvertTo-Json `
        -Depth 3 `
        -Compress |
    Write-Output
}

function Assert-PayloadIntegrity {
    param(
        [Parameter(Mandatory)]
        [string]$PayloadDirectory,

        [Parameter(Mandatory)]
        [string]$ManifestPath
    )

    $normalizedPayloadDirectory = (
        [System.IO.Path]::GetFullPath($PayloadDirectory)
    ).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )

    $manifestLines = @(
        Get-Content `
            -LiteralPath $ManifestPath `
            -ErrorAction Stop |
        Where-Object {
            -not [string]::IsNullOrWhiteSpace($_)
        }
    )

    if ($manifestLines.Count -eq 0) {
        throw "The CareQueue payload hash manifest is empty."
    }

    $manifestEntries = @{}

    foreach ($manifestLine in $manifestLines) {
        if (
            $manifestLine `
                -notmatch `
                "^(?<Hash>[0-9a-fA-F]{64})  (?<Path>.+)$"
        ) {
            throw (
                "The CareQueue payload hash manifest contains an " +
                "invalid entry: $manifestLine"
            )
        }

        $expectedHash = $Matches.Hash.ToLowerInvariant()
        $relativePath = $Matches.Path.Replace(
            "/",
            [System.IO.Path]::DirectorySeparatorChar
        )

        if (
            [System.IO.Path]::IsPathRooted($relativePath) `
                -or $relativePath.Split(
                [System.IO.Path]::DirectorySeparatorChar
            ) -contains ".."
        ) {
            throw (
                "The CareQueue payload hash manifest contains an " +
                "unsafe path: $relativePath"
            )
        }

        $fullPath = [System.IO.Path]::GetFullPath(
            (
                Join-Path `
                    $normalizedPayloadDirectory `
                    $relativePath
            )
        )

        $payloadPrefix = (
            $normalizedPayloadDirectory +
            [System.IO.Path]::DirectorySeparatorChar
        )

        if (
            -not $fullPath.StartsWith(
                $payloadPrefix,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw (
                "The CareQueue payload hash manifest path escapes " +
                "the payload directory: $relativePath"
            )
        }

        $normalizedRelativePath = (
            $fullPath.Substring(
                $payloadPrefix.Length
            )
        ).Replace(
            [System.IO.Path]::DirectorySeparatorChar,
            "/"
        )

        if ($manifestEntries.ContainsKey($normalizedRelativePath)) {
            throw (
                "The CareQueue payload hash manifest contains a " +
                "duplicate path: $normalizedRelativePath"
            )
        }

        $manifestEntries[$normalizedRelativePath] = $expectedHash
    }

    foreach ($manifestEntry in $manifestEntries.GetEnumerator()) {
        $manifestFilePath = Join-Path `
            $normalizedPayloadDirectory `
            $manifestEntry.Key.Replace(
            "/",
            [System.IO.Path]::DirectorySeparatorChar
        )

        if (
            -not (
                Test-Path `
                    -LiteralPath $manifestFilePath `
                    -PathType Leaf
            )
        ) {
            throw (
                "A file listed in the CareQueue payload hash " +
                "manifest is missing: $($manifestEntry.Key)"
            )
        }

        $actualHash = (
            Get-FileHash `
                -LiteralPath $manifestFilePath `
                -Algorithm SHA256
        ).Hash.ToLowerInvariant()

        if ($actualHash -ne $manifestEntry.Value) {
            throw (
                "CareQueue payload hash validation failed for " +
                "$($manifestEntry.Key). " +
                "Expected: $($manifestEntry.Value). " +
                "Actual: $actualHash"
            )
        }
    }

    $actualPayloadFiles = @(
        Get-ChildItem `
            -LiteralPath $normalizedPayloadDirectory `
            -File `
            -Recurse `
            -ErrorAction Stop |
        Where-Object {
            $_.FullName -ne $ManifestPath
        }
    )

    foreach ($actualPayloadFile in $actualPayloadFiles) {
        $actualRelativePath = (
            $actualPayloadFile.FullName.Substring(
                $normalizedPayloadDirectory.Length
            ).TrimStart(
                [System.IO.Path]::DirectorySeparatorChar,
                [System.IO.Path]::AltDirectorySeparatorChar
            )
        ).Replace(
            [System.IO.Path]::DirectorySeparatorChar,
            "/"
        )

        if (-not $manifestEntries.ContainsKey($actualRelativePath)) {
            throw (
                "The CareQueue payload contains a file that is not " +
                "listed in the hash manifest: $actualRelativePath"
            )
        }
    }

    if ($actualPayloadFiles.Count -ne $manifestEntries.Count) {
        throw (
            "The CareQueue payload file count does not match the " +
            "hash manifest. Manifest entries: " +
            "$($manifestEntries.Count). Payload files: " +
            "$($actualPayloadFiles.Count)."
        )
    }
}

if (-not (Test-Administrator)) {
    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeAdministratorRequired `
        -Message (
        "CareQueue installation requires Administrator privileges."
    )

    exit $exitCodeAdministratorRequired
}

try {
    if (-not $PayloadDirectory) {
        $PayloadDirectory = (
            Resolve-Path `
                -LiteralPath (
                Join-Path `
                    $PSScriptRoot `
                    "..\..\.."
            )
        ).Path
    }
    else {
        $PayloadDirectory = (
            Resolve-Path `
                -LiteralPath $PayloadDirectory `
                -ErrorAction Stop
        ).Path
    }

    $payloadMetadataPath = Join-Path `
        $PayloadDirectory `
        "payload.json"

    $payloadManifestPath = Join-Path `
        $PayloadDirectory `
        "SHA256SUMS.txt"

    $productionInstallerPath = Join-Path `
        $PayloadDirectory `
        "deployment\windows\install-production.ps1"

    $frontendBuildDirectory = Join-Path `
        $PayloadDirectory `
        "frontend\dist"

    $privatePythonRuntimeDirectory = Join-Path `
        $PayloadDirectory `
        "runtime\python"

    $vendorAssetDirectory = Join-Path `
        $PayloadDirectory `
        "vendor"

    $backendWheelDirectory = Join-Path `
        $PayloadDirectory `
        "dependencies\wheelhouse"

    $requiredPayloadPaths = @(
        $payloadMetadataPath,
        $payloadManifestPath,
        $productionInstallerPath,
        (Join-Path $frontendBuildDirectory "index.html"),
        (
            Join-Path `
                $privatePythonRuntimeDirectory `
                "python.exe"
        ),
        (
            Join-Path `
                $vendorAssetDirectory `
                "caddy\caddy.exe"
        ),
        (
            Join-Path `
                $vendorAssetDirectory `
                "winsw\WinSW-x64.exe"
        ),
        (
            Join-Path `
                $backendWheelDirectory `
                "SHA256SUMS.txt"
        )
    )

    foreach ($requiredPayloadPath in $requiredPayloadPaths) {
        if (
            -not (
                Test-Path `
                    -LiteralPath $requiredPayloadPath
            )
        ) {
            throw (
                "A required CareQueue payload path was not found: " +
                $requiredPayloadPath
            )
        }
    }

    Assert-PayloadIntegrity `
    -PayloadDirectory $PayloadDirectory `
    -ManifestPath $payloadManifestPath

    $payloadMetadata = Get-Content `
        -LiteralPath $payloadMetadataPath `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json

    if ($payloadMetadata.schema_version -ne 1) {
        throw (
            "Unsupported CareQueue payload schema version: " +
            $payloadMetadata.schema_version
        )
    }

    if (
        [string]$payloadMetadata.application.name `
            -ne "CareQueue"
    ) {
        throw (
            "The supplied payload is not a CareQueue installer payload."
        )
    }
}
catch {
    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeInvalidPayload `
        -Message $_.Exception.Message

    exit $exitCodeInvalidPayload
}

try {
    New-Item `
        -ItemType Directory `
        -Path $LogDirectory `
        -Force |
    Out-Null

    $resolvedLogDirectory = (
        Resolve-Path `
            -LiteralPath $LogDirectory `
            -ErrorAction Stop
    ).Path

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

    $logPath = Join-Path `
        $resolvedLogDirectory `
        "CareQueue-Install-$timestamp.log"
}
catch {
    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeLoggingFailure `
        -Message (
        "Unable to prepare the CareQueue installer log: " +
        $_.Exception.Message
    )

    exit $exitCodeLoggingFailure
}

$installerArguments = @(
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $productionInstallerPath,
    "-ApplicationOrigin",
    $ApplicationOrigin,
    "-SourceDirectory",
    $PayloadDirectory,
    "-InstallDirectory",
    $InstallDirectory,
    "-DataDirectory",
    $DataDirectory,
    "-FrontendBuildDirectory",
    $frontendBuildDirectory,
    "-PrivatePythonRuntimeDirectory",
    $privatePythonRuntimeDirectory,
    "-VendorAssetDirectory",
    $vendorAssetDirectory,
    "-BackendWheelDirectory",
    $backendWheelDirectory
)

if ($Force) {
    $installerArguments += "-Force"
}

if ($SkipPermissionHardening) {
    $installerArguments += "-SkipPermissionHardening"
}

$logHeader = @(
    "CareQueue Windows Installer"
    "Started UTC: $([DateTime]::UtcNow.ToString('o'))"
    "Payload: $PayloadDirectory"
    "Install directory: $InstallDirectory"
    "Data directory: $DataDirectory"
    "Application origin: $ApplicationOrigin"
    ""
)

$logHeader |
Set-Content `
    -LiteralPath $logPath `
    -Encoding utf8

try {
    & powershell.exe @installerArguments 2>&1 |
    Tee-Object `
        -FilePath $logPath `
        -Append

    $productionInstallerExitCode = $LASTEXITCODE

    if ($productionInstallerExitCode -ne 0) {
        throw (
            "The CareQueue production installer failed with exit code " +
            "$productionInstallerExitCode."
        )
    }
}
catch {
    $failureMessage = $_.Exception.Message

    @(
        ""
        "Installation failed."
        "Completed UTC: $([DateTime]::UtcNow.ToString('o'))"
        "Message: $failureMessage"
    ) |
    Add-Content `
        -LiteralPath $logPath `
        -Encoding utf8

    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeInstallationFailure `
        -Message $failureMessage `
        -LogPath $logPath

    exit $exitCodeInstallationFailure
}

@(
    ""
    "Installation completed successfully."
    "Completed UTC: $([DateTime]::UtcNow.ToString('o'))"
) |
Add-Content `
    -LiteralPath $logPath `
    -Encoding utf8

Write-InstallerResult `
    -Status "succeeded" `
    -ExitCode $exitCodeSuccess `
    -Message "CareQueue installation completed successfully." `
    -LogPath $logPath

exit $exitCodeSuccess
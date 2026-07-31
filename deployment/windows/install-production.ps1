[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern("^https://")]
    [string]$ApplicationOrigin,

    [string]$SourceDirectory = (
        Resolve-Path (
            Join-Path $PSScriptRoot "..\.."
        )
    ).Path,

    [string]$InstallDirectory = "C:\Program Files\CareQueue",

    [string]$DataDirectory = "C:\ProgramData\CareQueue",

    [string]$PythonExecutable = "python",

    [switch]$Force,

    [switch]$SkipPermissionHardening
)

$ErrorActionPreference = "Stop"

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

function New-FernetKey {
    $keyBytes = New-Object byte[] 32
    $randomGenerator = (
        [Security.Cryptography.RandomNumberGenerator]::Create()
    )

    try {
        $randomGenerator.GetBytes($keyBytes)
    }
    finally {
        $randomGenerator.Dispose()
    }

    $encodedKey = [Convert]::ToBase64String($keyBytes)
    $encodedKey = $encodedKey.Replace("+", "-")
    $encodedKey = $encodedKey.Replace("/", "_")

    return $encodedKey
}

function New-RandomSecret {
    param(
        [ValidateRange(32, 256)]
        [int]$ByteCount = 48
    )

    $secretBytes = New-Object byte[] $ByteCount
    $randomGenerator = (
        [Security.Cryptography.RandomNumberGenerator]::Create()
    )

    try {
        $randomGenerator.GetBytes($secretBytes)
    }
    finally {
        $randomGenerator.Dispose()
    }

    $encodedSecret = [Convert]::ToBase64String(
        $secretBytes
    )

    $encodedSecret = $encodedSecret.Replace("+", "-")
    $encodedSecret = $encodedSecret.Replace("/", "_")
    $encodedSecret = $encodedSecret.TrimEnd("=")

    return $encodedSecret
}

function Invoke-ExternalCommand {
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
        throw "$FailureMessage Exit code: $LASTEXITCODE"
    }
}

if (-not (Test-Administrator)) {
    throw "This script must be run from PowerShell as Administrator."
}

try {
    $applicationUri = [Uri]$ApplicationOrigin
}
catch {
    throw "ApplicationOrigin must be a valid absolute HTTPS origin."
}

if (
    -not $applicationUri.IsAbsoluteUri `
        -or $applicationUri.Scheme -ne "https" `
        -or -not $applicationUri.Host `
        -or $applicationUri.UserInfo `
        -or $applicationUri.AbsolutePath -ne "/" `
        -or $applicationUri.Query `
        -or $applicationUri.Fragment
) {
    throw (
        "ApplicationOrigin must contain only an HTTPS scheme, hostname, " +
        "and optional port. Paths, credentials, queries, and fragments " +
        "are not allowed."
    )
}

$normalizedApplicationOrigin = (
    $applicationUri.GetLeftPart(
        [System.UriPartial]::Authority
    )
).TrimEnd("/")

$resolvedSourceDirectory = (
    Resolve-Path -LiteralPath $SourceDirectory
).Path

$requiredSourcePaths = @(
    "backend\authstatus_api",
    "backend\scripts",
    "backend\requirements.txt",
    "frontend\package.json",
    "frontend\package-lock.json",
    "deployment\windows\run-api.ps1",
    "deployment\windows\CareQueueApi.xml",
    "deployment\windows\Caddyfile",
    "deployment\windows\install-api-service.ps1",
    "deployment\windows\remove-api-service.ps1"
)

foreach ($relativePath in $requiredSourcePaths) {
    $requiredPath = Join-Path `
        $resolvedSourceDirectory `
        $relativePath

    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required production source was not found: $requiredPath"
    }
}

$pythonCommand = Get-Command `
    $PythonExecutable `
    -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    throw "Python executable was not found: $PythonExecutable"
}

$npmCommand = Get-Command `
    "npm" `
    -ErrorAction SilentlyContinue

if (-not $npmCommand) {
    throw "npm was not found on PATH."
}

if (
    (Test-Path -LiteralPath $InstallDirectory) `
        -and -not $Force
) {
    $existingItems = Get-ChildItem `
        -LiteralPath $InstallDirectory `
        -Force `
        -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -ne "Service"
    }

    if ($existingItems) {
        throw (
            "The production install directory contains application files. " +
            "Use -Force only after confirming it is safe to replace."
        )
    }
}

$stagingRoot = Join-Path `
([System.IO.Path]::GetTempPath()) `
("CareQueue-Install-" + [guid]::NewGuid().ToString("N"))

$stagingInstallDirectory = Join-Path `
    $stagingRoot `
    "CareQueue"

$stagingBackendDirectory = Join-Path `
    $stagingInstallDirectory `
    "backend"

$stagingFrontendDirectory = Join-Path `
    $stagingInstallDirectory `
    "frontend"

$stagingFrontendBuildDirectory = Join-Path `
    $stagingFrontendDirectory `
    "dist"

$stagingDeploymentDirectory = Join-Path `
    $stagingInstallDirectory `
    "deployment"

$sourceFrontendDirectory = Join-Path `
    $resolvedSourceDirectory `
    "frontend"

$sourceBackendDirectory = Join-Path `
    $resolvedSourceDirectory `
    "backend"

$previousApiBaseUrl = $env:VITE_AUTHSTATUS_API_BASE_URL
$previousLegacyApiBaseUrl = $env:VITE_API_BASE_URL

try {
    New-Item `
        -ItemType Directory `
        -Path $stagingBackendDirectory `
        -Force | Out-Null

    New-Item `
        -ItemType Directory `
        -Path $stagingFrontendBuildDirectory `
        -Force | Out-Null

    New-Item `
        -ItemType Directory `
        -Path $stagingDeploymentDirectory `
        -Force | Out-Null

    Write-Host "Building the production frontend..."

    Push-Location $sourceFrontendDirectory

    try {
        Remove-Item `
            Env:VITE_AUTHSTATUS_API_BASE_URL `
            -ErrorAction SilentlyContinue

        Remove-Item `
            Env:VITE_API_BASE_URL `
            -ErrorAction SilentlyContinue

        Invoke-ExternalCommand `
            -Executable "npm" `
            -Arguments @("ci") `
            -FailureMessage "Frontend dependency installation failed."

        Invoke-ExternalCommand `
            -Executable "npm" `
            -Arguments @("run", "build") `
            -FailureMessage "Frontend production build failed."
    }
    finally {
        Pop-Location
    }

    $frontendBuildDirectory = Join-Path `
        $sourceFrontendDirectory `
        "dist"

    if (
        -not (
            Test-Path `
                -LiteralPath $frontendBuildDirectory `
                -PathType Container
        )
    ) {
        throw "The frontend production build directory was not created."
    }

    if (
        -not (
            Test-Path `
                -LiteralPath (
                Join-Path $frontendBuildDirectory "index.html"
            ) `
                -PathType Leaf
        )
    ) {
        throw "The frontend production build does not contain index.html."
    }

    Copy-Item `
        -Path (Join-Path $frontendBuildDirectory "*") `
        -Destination $stagingFrontendBuildDirectory `
        -Recurse `
        -Force

    Write-Host "Copying backend production files..."

    Copy-Item `
        -LiteralPath (
        Join-Path $sourceBackendDirectory "authstatus_api"
    ) `
        -Destination $stagingBackendDirectory `
        -Recurse `
        -Force

    Copy-Item `
        -LiteralPath (
        Join-Path $sourceBackendDirectory "scripts"
    ) `
        -Destination $stagingBackendDirectory `
        -Recurse `
        -Force

    Copy-Item `
        -LiteralPath (
        Join-Path $sourceBackendDirectory "requirements.txt"
    ) `
        -Destination $stagingBackendDirectory `
        -Force

    Copy-Item `
        -LiteralPath (
        Join-Path $resolvedSourceDirectory "deployment\windows"
    ) `
        -Destination $stagingDeploymentDirectory `
        -Recurse `
        -Force

    Write-Host "Preparing the production Caddy configuration..."

    $stagedCaddyfile = Join-Path `
        $stagingDeploymentDirectory `
        "windows\Caddyfile"

    if (
        -not (
            Test-Path `
                -LiteralPath $stagedCaddyfile `
                -PathType Leaf
        )
    ) {
        throw "The staged Windows Caddyfile was not found."
    }

    $caddyConfiguration = Get-Content `
        -LiteralPath $stagedCaddyfile `
        -Raw

    if (
        -not $caddyConfiguration.Contains(
            "carequeue.example.com"
        )
    ) {
        throw (
            "The staged Caddyfile does not contain the expected " +
            "hostname placeholder."
        )
    }

    $caddyHostname = $applicationUri.Authority

    $caddyConfiguration = $caddyConfiguration.Replace(
        "carequeue.example.com",
        $caddyHostname
    )

    Set-Content `
        -LiteralPath $stagedCaddyfile `
        -Value $caddyConfiguration `
        -Encoding UTF8

    Write-Host "Preparing production runtime directories..."

    $configDirectory = Join-Path `
        $DataDirectory `
        "Config"

    $databaseDirectory = Join-Path `
        $DataDirectory `
        "Data"

    $backupDirectory = Join-Path `
        $DataDirectory `
        "Backups"

    $restoreDirectory = Join-Path `
        $DataDirectory `
        "Restores"

    $logDirectory = Join-Path `
        $DataDirectory `
        "Logs"

    $apiLogDirectory = Join-Path `
        $logDirectory `
        "Api"

    $recoveryDirectory = Join-Path `
        $DataDirectory `
        "Recovery"

    $runtimeDirectories = @(
        $DataDirectory,
        $configDirectory,
        $databaseDirectory,
        $backupDirectory,
        $restoreDirectory,
        $logDirectory,
        $apiLogDirectory,
        $recoveryDirectory
    )

    foreach ($runtimeDirectory in $runtimeDirectories) {
        New-Item `
            -ItemType Directory `
            -Path $runtimeDirectory `
            -Force | Out-Null
    }

    $environmentFile = Join-Path `
        $configDirectory `
        "carequeue.env"

    $databasePath = Join-Path `
        $databaseDirectory `
        "auth_tracker.sqlcipher.db"

    if (
        Test-Path `
            -LiteralPath $environmentFile `
            -PathType Leaf
    ) {
        Write-Host (
            "An existing production environment file was found. " +
            "Its secrets and settings will be preserved."
        )
    }
    else {
        Write-Host "Generating independent production encryption keys..."

        $fieldEncryptionKey = New-FernetKey
        $backupEncryptionKey = New-FernetKey
        $sqlCipherKey = New-RandomSecret -ByteCount 48

        if ($fieldEncryptionKey -eq $backupEncryptionKey) {
            throw "Generated encryption keys must be independent."
        }

        $corsOrigins = ConvertTo-Json `
            -InputObject @($normalizedApplicationOrigin) `
            -Compress

        $environmentContent = @"
AUTHSTATUS_APP_ENVIRONMENT=production
AUTHSTATUS_ENCRYPTION_KEY=$fieldEncryptionKey
AUTHSTATUS_SQLCIPHER_KEY=$sqlCipherKey
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=$backupEncryptionKey
AUTHSTATUS_DATABASE_PATH=$databasePath
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=true
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true
AUTHSTATUS_BACKUP_DIRECTORY=$backupDirectory
AUTHSTATUS_BACKUP_RETENTION_DAYS=90
AUTHSTATUS_BACKUP_MINIMUM_COUNT=5
AUTHSTATUS_RESTORE_DIRECTORY=$restoreDirectory
AUTHSTATUS_CORS_ORIGINS=$corsOrigins
AUTHSTATUS_SESSION_COOKIE_SECURE=true
AUTHSTATUS_SESSION_COOKIE_NAME=carequeue_session
AUTHSTATUS_CSRF_COOKIE_NAME=carequeue_csrf
AUTHSTATUS_CSRF_HEADER_NAME=X-CSRF-Token
"@

        Set-Content `
            -LiteralPath $environmentFile `
            -Value $environmentContent `
            -Encoding UTF8
    }


    Write-Host "Installing staged application files..."

    New-Item `
        -ItemType Directory `
        -Path $InstallDirectory `
        -Force | Out-Null

    $installedServiceDirectory = Join-Path `
        $InstallDirectory `
        "Service"

    $installedBackendDirectory = Join-Path `
        $InstallDirectory `
        "backend"

    $installedFrontendDirectory = Join-Path `
        $InstallDirectory `
        "frontend"

    $installedDeploymentDirectory = Join-Path `
        $InstallDirectory `
        "deployment"

    $replaceableDirectories = @(
        $installedBackendDirectory,
        $installedFrontendDirectory,
        $installedDeploymentDirectory
    )

    foreach ($replaceableDirectory in $replaceableDirectories) {
        if (Test-Path -LiteralPath $replaceableDirectory) {
            if (-not $Force) {
                throw (
                    "Existing application directory cannot be replaced " +
                    "without -Force: $replaceableDirectory"
                )
            }

            Remove-Item `
                -LiteralPath $replaceableDirectory `
                -Recurse `
                -Force
        }
    }

    Copy-Item `
        -LiteralPath $stagingBackendDirectory `
        -Destination $InstallDirectory `
        -Recurse `
        -Force

    Copy-Item `
        -LiteralPath $stagingFrontendDirectory `
        -Destination $InstallDirectory `
        -Recurse `
        -Force

    Copy-Item `
        -LiteralPath $stagingDeploymentDirectory `
        -Destination $InstallDirectory `
        -Recurse `
        -Force

    Write-Host "Creating the production Python environment..."

    $installedVirtualEnvironment = Join-Path `
        $installedBackendDirectory `
        ".venv"

    Invoke-ExternalCommand `
        -Executable $PythonExecutable `
        -Arguments @(
        "-m",
        "venv",
        $installedVirtualEnvironment
    ) `
        -FailureMessage (
        "Production virtual environment creation failed."
    )

    $installedPythonExecutable = Join-Path `
        $installedVirtualEnvironment `
        "Scripts\python.exe"

    if (
        -not (
            Test-Path `
                -LiteralPath $installedPythonExecutable `
                -PathType Leaf
        )
    ) {
        throw (
            "The production Python executable was not created at: " +
            $installedPythonExecutable
        )
    }

    $installedRequirementsFile = Join-Path `
        $installedBackendDirectory `
        "requirements.txt"

    Write-Host "Installing production backend dependencies..."

    Invoke-ExternalCommand `
        -Executable $installedPythonExecutable `
        -Arguments @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--upgrade",
        "pip"
    ) `
        -FailureMessage "Production pip upgrade failed."

    Invoke-ExternalCommand `
        -Executable $installedPythonExecutable `
        -Arguments @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--requirement",
        $installedRequirementsFile
    ) `
        -FailureMessage (
        "Production backend dependency installation failed."
    )

    Write-Host "Validating the installed backend..."

    $environmentLines = Get-Content `
        -LiteralPath $environmentFile

    foreach ($environmentLine in $environmentLines) {
        $line = $environmentLine.Trim()

        if (
            -not $line `
                -or $line.StartsWith("#") `
                -or -not $line.Contains("=")
        ) {
            continue
        }

        $name, $value = $line.Split("=", 2)

        $name = $name.Trim()
        $value = $value.Trim()

        if ($name) {
            [Environment]::SetEnvironmentVariable(
                $name,
                $value,
                [EnvironmentVariableTarget]::Process
            )
        }
    }

    Push-Location $installedBackendDirectory

    try {
        Invoke-ExternalCommand `
            -Executable $installedPythonExecutable `
            -Arguments @(
            "-c",
            (
                "import authstatus_api.main; " +
                "import uvicorn; " +
                "print('CareQueue production backend validated.')"
            )
        ) `
            -FailureMessage (
            "The installed CareQueue backend could not be imported."
        )
    }
    finally {
        Pop-Location
    }

    if (-not $SkipPermissionHardening) {
        Write-Host "Restricting runtime directory permissions..."
    
        $installerAccount = (
            [Security.Principal.WindowsIdentity]::GetCurrent()
        ).Name
    
        & icacls.exe `
            $DataDirectory `
            /reset `
            /T `
            /C | Out-Null
    
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to reset production runtime permissions."
        }
    
        & icacls.exe `
            $DataDirectory `
            /inheritance:r | Out-Null
    
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to disable inherited runtime permissions."
        }
    
        $systemGrant = "SYSTEM:(OI)(CI)F"
        $administratorsGrant = "BUILTIN\Administrators:(OI)(CI)F"
        $installerGrant = "${installerAccount}:(OI)(CI)F"
    
        & icacls.exe `
            $DataDirectory `
            /grant:r `
            $systemGrant `
            $administratorsGrant `
            $installerGrant | Out-Null
    
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to apply production runtime permissions."
        }
    
        $childPath = Join-Path $DataDirectory "*"
    
        & icacls.exe `
            $childPath `
            /reset `
            /T `
            /C | Out-Null
    
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to propagate production runtime permissions."
        }
    
        try {
            Get-Content `
                -LiteralPath $environmentFile `
                -TotalCount 1 `
                -ErrorAction Stop | Out-Null
        }
        catch {
            throw (
                "Permission hardening prevented the installing " +
                "administrator from reading the environment file."
            )
        }
    }

    Write-Host ""
    Write-Host "CareQueue production files installed successfully."
    Write-Host "Application directory: $InstallDirectory"
    Write-Host "Runtime data directory: $DataDirectory"
    Write-Host "Environment file: $environmentFile"
    Write-Host "Application origin: $normalizedApplicationOrigin"
    Write-Host ""
    Write-Host "The API and Caddy services were not started automatically."
    Write-Host (
        "Review the generated configuration before installing " +
        "or starting services."
    )
}
finally {
    if ($null -ne $previousApiBaseUrl) {
        $env:VITE_AUTHSTATUS_API_BASE_URL = $previousApiBaseUrl
    }
    else {
        Remove-Item `
            Env:VITE_AUTHSTATUS_API_BASE_URL `
            -ErrorAction SilentlyContinue
    }

    if ($null -ne $previousLegacyApiBaseUrl) {
        $env:VITE_API_BASE_URL = $previousLegacyApiBaseUrl
    }
    else {
        Remove-Item `
            Env:VITE_API_BASE_URL `
            -ErrorAction SilentlyContinue
    }

    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item `
            -LiteralPath $stagingRoot `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }
}
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet(
        "Install",
        "Upgrade",
        "Repair",
        "Rollback",
        "Uninstall"
    )]
    [string]$Mode,

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
$exitCodeInvalidInstallState = 15
$exitCodeAdministratorRequired = 20
$exitCodeLoggingFailure = 25
$exitCodeInstallationFailure = 30
$exitCodePostInstallValidationFailure = 35
$installStatePath = Join-Path `
    $DataDirectory `
    "Config\install-state.json"

$incomingVersion = $null
$installedVersion = $null
$preUpgradeBackupPath = $null
$backupDirectory = Join-Path `
    $DataDirectory `
    "Backups"
$preUpgradeApplicationArchive = $null
$preUpgradeApplicationSha256 = $null

$applicationRecoveryDirectory = Join-Path `
    $DataDirectory `
    "Recovery\Applications"

$upgradeRecoveryDirectory = Join-Path `
    $DataDirectory `
    "Recovery\Upgrades"

$upgradeRecoveryRecord = $null
$rollbackRecoveryRecord = $null
$rollbackPreviousVersion = $null
$rollbackIncomingVersion = $null
$rollbackBackupPath = $null
$rollbackApplicationArchive = $null
$rollbackApplicationSha256 = $null
$rollbackApplicationStagingDirectory = Join-Path `
    $DataDirectory `
    "Recovery\Staging\Application"
$failedApplicationRecoveryDirectory = Join-Path `
    $DataDirectory `
    "Recovery\FailedApplications"

$failedApplicationArchive = $null
$failedApplicationSha256 = $null
$failedApplicationStagingDirectory = Join-Path `
    $DataDirectory `
    "Recovery\Staging\FailedApplication"

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

function Set-CareQueueLocalHostname {
    param(
        [Parameter(Mandatory)]
        [string]$ApplicationOrigin
    )

    try {
        $applicationUri = [Uri]$ApplicationOrigin
    }
    catch {
        throw (
            "The CareQFlow application origin is not a valid URI: " +
            $ApplicationOrigin
        )
    }

    $hostname = $applicationUri.DnsSafeHost

    if ($hostname -ne "careqflow.local") {
        return
    }

    $hostsPath = Join-Path `
        $env:SystemRoot `
        "System32\drivers\etc\hosts"

    if (
        -not (
            Test-Path `
                -LiteralPath $hostsPath `
                -PathType Leaf
        )
    ) {
        throw "The Windows hosts file was not found: $hostsPath"
    }

    $existingLines = @(
        Get-Content `
            -LiteralPath $hostsPath `
            -ErrorAction Stop
    )

    $legacyManagedPattern = (
        '^\s*127\.0\.0\.1\s+carequeue\.local' +
        '\s+#\s*CareQueue\s*$'
    )

    $updatedLines = @(
        $existingLines |
        Where-Object {
            $_ -notmatch $legacyManagedPattern
        }
    )

    if ($updatedLines.Count -ne $existingLines.Count) {
        Write-Output (
            "Removing the legacy CareQFlow local hostname entry..."
        )

        Set-Content `
            -LiteralPath $hostsPath `
            -Value $updatedLines `
            -Encoding ASCII `
            -ErrorAction Stop

        $existingLines = $updatedLines

        Clear-DnsClientCache `
            -ErrorAction Stop
    }

    foreach ($line in $existingLines) {
        $content = (
            $line.Split("#", 2)[0]
        ).Trim()

        if ([string]::IsNullOrWhiteSpace($content)) {
            continue
        }

        $parts = @(
            $content -split "\s+" |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            }
        )

        if ($parts.Count -lt 2) {
            continue
        }

        $address = $parts[0]
        $hostnames = @($parts[1..($parts.Count - 1)])

        if (
            -not (
                $hostnames |
                Where-Object {
                    $_ -ieq $hostname
                }
            )
        ) {
            continue
        }

        if (
            $address -eq "127.0.0.1" `
                -or $address -eq "::1"
        ) {
            return
        }

        throw (
            "The Windows hosts file already maps $hostname to " +
            "$address. CareQFlow will not overwrite an existing " +
            "non-loopback hostname mapping."
        )
    }

    Write-Output (
        "Registering $hostname as a local CareQFlow hostname..."
    )

    Add-Content `
        -LiteralPath $hostsPath `
        -Value "127.0.0.1`t$hostname # CareQFlow" `
        -Encoding ASCII `
        -ErrorAction Stop

    Clear-DnsClientCache `
        -ErrorAction Stop
}

function Test-CareQueueInstallation {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory
    )

    $requiredInstalledPaths = @(
        (
            Join-Path `
                $InstallDirectory `
                "backend\authstatus_api"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "frontend\dist\index.html"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "runtime\python\python.exe"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "vendor\caddy\caddy.exe"
        )
    )

    foreach ($requiredInstalledPath in $requiredInstalledPaths) {
        if (
            -not (
                Test-Path `
                    -LiteralPath $requiredInstalledPath
            )
        ) {
            return $false
        }
    }

    return $true
}

function Test-CareQueueVersion {
    param(
        [Parameter(Mandatory)]
        [string]$Version
    )

    return $Version -match '^\d+\.\d+\.\d+$'
}

function Compare-CareQueueVersions {
    param(
        [Parameter(Mandatory)]
        [string]$LeftVersion,

        [Parameter(Mandatory)]
        [string]$RightVersion
    )

    if (-not (Test-CareQueueVersion -Version $LeftVersion)) {
        throw "Invalid CareQFlow version: $LeftVersion"
    }

    if (-not (Test-CareQueueVersion -Version $RightVersion)) {
        throw "Invalid CareQFlow version: $RightVersion"
    }

    $leftParts = @(
        $LeftVersion.Split(".") |
        ForEach-Object {
            [int]$_
        }
    )

    $rightParts = @(
        $RightVersion.Split(".") |
        ForEach-Object {
            [int]$_
        }
    )

    for ($index = 0; $index -lt 3; $index++) {
        if ($leftParts[$index] -gt $rightParts[$index]) {
            return 1
        }

        if ($leftParts[$index] -lt $rightParts[$index]) {
            return -1
        }
    }

    return 0
}

function Get-CareQueueInstalledVersion {
    param(
        [Parameter(Mandatory)]
        [string]$InstallStatePath
    )

    if (
        -not (
            Test-Path `
                -LiteralPath $InstallStatePath `
                -PathType Leaf
        )
    ) {
        return $null
    }

    try {
        $installState = Get-Content `
            -LiteralPath $InstallStatePath `
            -Raw `
            -ErrorAction Stop |
        ConvertFrom-Json `
            -ErrorAction Stop
    }
    catch {
        throw (
            "The CareQFlow installation state could not be read: " +
            $_.Exception.Message
        )
    }

    if (
        $null -eq $installState.installed_version `
            -or [string]::IsNullOrWhiteSpace(
            [string]$installState.installed_version
        )
    ) {
        return $null
    }

    $version = [string]$installState.installed_version

    if (-not (Test-CareQueueVersion -Version $version)) {
        throw (
            "The installed CareQFlow version metadata is invalid: " +
            $version
        )
    }

    return $version
}

function Assert-CareQueueUpgradeVersion {
    param(
        [Parameter(Mandatory)]
        [string]$IncomingVersion,

        [AllowNull()]
        [string]$InstalledVersion
    )

    if (-not (Test-CareQueueVersion -Version $IncomingVersion)) {
        throw (
            "The incoming CareQFlow payload has an invalid " +
            "application version: $IncomingVersion"
        )
    }

    if ([string]::IsNullOrWhiteSpace($InstalledVersion)) {
        Write-Output (
            "Installed CareQFlow version metadata is unavailable. " +
            "Continuing legacy upgrade validation."
        )

        return
    }

    $comparison = Compare-CareQueueVersions `
        -LeftVersion $IncomingVersion `
        -RightVersion $InstalledVersion

    if ($comparison -eq 0) {
        throw (
            "CareQFlow $IncomingVersion is already installed. " +
            "Use Repair instead of Upgrade."
        )
    }

    if ($comparison -lt 0) {
        throw (
            "CareQFlow downgrade refused: installed version " +
            "$InstalledVersion, incoming version $IncomingVersion."
        )
    }

    Write-Output (
        "Validated CareQFlow upgrade path: " +
        "$InstalledVersion -> $IncomingVersion"
    )
}

function New-VerifiedPreUpgradeBackup {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$DataDirectory,

        [Parameter(Mandatory)]
        [string]$BackupDirectory
    )

    if ($Mode -ne "Upgrade") {
        return $null
    }

    $backupRunner = Join-Path `
        $InstallDirectory `
        "deployment\windows\run-backup.ps1"

    $environmentFile = Join-Path `
        $DataDirectory `
        "Config\carequeue.env"

    if (
        -not (
            Test-Path `
                -LiteralPath $backupRunner `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow upgrade requires the installed backup runner: " +
            $backupRunner
        )
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $environmentFile `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow upgrade requires the production configuration: " +
            $environmentFile
        )
    }

    New-Item `
        -ItemType Directory `
        -Path $BackupDirectory `
        -Force |
    Out-Null

    $backupMarker = Join-Path `
        $BackupDirectory `
    (
        ".carequeue-pre-upgrade-marker-" +
        [Guid]::NewGuid().ToString("N")
    )

    Set-Content `
        -LiteralPath $backupMarker `
        -Value "" `
        -Encoding ASCII `
        -ErrorAction Stop

    try {
        Write-Host (
            "Creating and verifying pre-upgrade encrypted backup..."
        )

        & powershell.exe `
            -NoProfile `
            -NonInteractive `
            -ExecutionPolicy Bypass `
            -File $backupRunner `
            -InstallDirectory $InstallDirectory `
            -BackupDirectory $BackupDirectory `
            -EnvironmentFile $environmentFile

        if ($LASTEXITCODE -ne 0) {
            throw (
                "Pre-upgrade backup creation or verification failed. " +
                "The CareQFlow application has not been replaced."
            )
        }

        $markerTimestamp = (
            Get-Item `
                -LiteralPath $backupMarker `
                -ErrorAction Stop
        ).LastWriteTimeUtc

        $newBackups = @(
            Get-ChildItem `
                -LiteralPath $BackupDirectory `
                -Filter "*.db.enc" `
                -File `
                -ErrorAction Stop |
            Where-Object {
                $_.LastWriteTimeUtc -gt $markerTimestamp
            } |
            Sort-Object `
                -Property LastWriteTimeUtc `
                -Descending
        )

        if ($newBackups.Count -eq 0) {
            throw (
                "The CareQFlow backup runner completed but no new " +
                "pre-upgrade backup could be identified. " +
                "The CareQFlow application has not been replaced."
            )
        }

        $backupPath = $newBackups[0].FullName

        if ($newBackups[0].Length -le 0) {
            throw (
                "The pre-upgrade backup is missing or empty: " +
                $backupPath
            )
        }

        Write-Host (
            "Verified pre-upgrade backup: " +
            $backupPath
        )

        return $backupPath
    }
    finally {
        Remove-Item `
            -LiteralPath $backupMarker `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

function New-VerifiedPreUpgradeApplicationArchive {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$InstalledVersion,

        [Parameter(Mandatory)]
        [string]$RecoveryDirectory
    )

    if ($Mode -ne "Upgrade") {
        return $null
    }

    if (-not (Test-CareQueueVersion -Version $InstalledVersion)) {
        throw (
            "Cannot preserve the installed CareQFlow application " +
            "because its version metadata is invalid: $InstalledVersion"
        )
    }

    $requiredApplicationDirectories = @(
        "backend",
        "frontend",
        "deployment",
        "runtime",
        "vendor",
        "Service"
    )

    foreach ($relativeDirectory in $requiredApplicationDirectories) {
        $applicationDirectory = Join-Path `
            $InstallDirectory `
            $relativeDirectory

        if (
            -not (
                Test-Path `
                    -LiteralPath $applicationDirectory `
                    -PathType Container
            )
        ) {
            throw (
                "Cannot preserve the installed CareQFlow application " +
                "because a required directory is missing: " +
                $applicationDirectory
            )
        }
    }

    New-Item `
        -ItemType Directory `
        -Path $RecoveryDirectory `
        -Force |
    Out-Null

    $archivePath = Join-Path `
        $RecoveryDirectory `
    (
        "carequeue-application-" +
        $InstalledVersion +
        ".zip"
    )

    $checksumPath = "$archivePath.sha256"

    Remove-Item `
        -LiteralPath $archivePath `
        -Force `
        -ErrorAction SilentlyContinue

    Remove-Item `
        -LiteralPath $checksumPath `
        -Force `
        -ErrorAction SilentlyContinue

    Write-Host (
        "Preserving installed CareQFlow $InstalledVersion " +
        "application payload..."
    )

    $applicationPaths = @(
        $requiredApplicationDirectories |
        ForEach-Object {
            Join-Path `
                $InstallDirectory `
                $_
        }
    )

    Compress-Archive `
        -LiteralPath $applicationPaths `
        -DestinationPath $archivePath `
        -CompressionLevel Optimal `
        -Force `
        -ErrorAction Stop

    if (
        -not (
            Test-Path `
                -LiteralPath $archivePath `
                -PathType Leaf
        )
    ) {
        throw (
            "The pre-upgrade application archive was not created."
        )
    }

    $archiveItem = Get-Item `
        -LiteralPath $archivePath `
        -ErrorAction Stop

    if ($archiveItem.Length -le 0) {
        throw (
            "The pre-upgrade application archive is empty: " +
            $archivePath
        )
    }

    $archiveSha256 = (
        Get-FileHash `
            -LiteralPath $archivePath `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()

    if ($archiveSha256 -notmatch '^[0-9a-f]{64}$') {
        throw (
            "Unable to calculate the pre-upgrade application " +
            "archive SHA256 checksum."
        )
    }

    Set-Content `
        -LiteralPath $checksumPath `
        -Value (
        "$archiveSha256  " +
        [System.IO.Path]::GetFileName($archivePath)
    ) `
        -Encoding ASCII `
        -ErrorAction Stop

    $verificationSha256 = (
        Get-FileHash `
            -LiteralPath $archivePath `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()

    if ($verificationSha256 -ne $archiveSha256) {
        throw (
            "Pre-upgrade application archive checksum " +
            "verification failed."
        )
    }

    Write-Host (
        "Verified pre-upgrade application payload: " +
        $archivePath
    )

    Write-Host (
        "Pre-upgrade application SHA256: " +
        $archiveSha256
    )

    return [PSCustomObject]@{
        ArchivePath = $archivePath
        Sha256      = $archiveSha256
    }
}

function New-CareQueueUpgradeRecoveryRecord {
    param(
        [Parameter(Mandatory)]
        [string]$RecoveryDirectory,

        [Parameter(Mandatory)]
        [string]$PreviousVersion,

        [Parameter(Mandatory)]
        [string]$IncomingVersion,

        [Parameter(Mandatory)]
        [string]$BackupPath,

        [Parameter(Mandatory)]
        [string]$ApplicationArchive,

        [Parameter(Mandatory)]
        [string]$ApplicationSha256,

        [Parameter(Mandatory)]
        [string]$InstallerLog
    )

    if ($Mode -ne "Upgrade") {
        return $null
    }

    if (-not (Test-CareQueueVersion -Version $PreviousVersion)) {
        throw (
            "Cannot create upgrade recovery state because the " +
            "previous CareQFlow version is invalid: $PreviousVersion"
        )
    }

    if (-not (Test-CareQueueVersion -Version $IncomingVersion)) {
        throw (
            "Cannot create upgrade recovery state because the " +
            "incoming CareQFlow version is invalid: $IncomingVersion"
        )
    }

    if (
        [string]::IsNullOrWhiteSpace($BackupPath) `
            -or -not (
            Test-Path `
                -LiteralPath $BackupPath `
                -PathType Leaf
        )
    ) {
        throw (
            "Cannot create upgrade recovery state because the " +
            "verified pre-upgrade backup is unavailable."
        )
    }

    if (
        [string]::IsNullOrWhiteSpace($ApplicationArchive) `
            -or -not (
            Test-Path `
                -LiteralPath $ApplicationArchive `
                -PathType Leaf
        )
    ) {
        throw (
            "Cannot create upgrade recovery state because the " +
            "verified pre-upgrade application archive is unavailable."
        )
    }

    if ($ApplicationSha256 -notmatch '^[0-9a-f]{64}$') {
        throw (
            "Cannot create upgrade recovery state because the " +
            "pre-upgrade application checksum is invalid."
        )
    }

    New-Item `
        -ItemType Directory `
        -Path $RecoveryDirectory `
        -Force |
    Out-Null

    $recordPath = Join-Path `
        $RecoveryDirectory `
    (
        "upgrade-" +
        $PreviousVersion +
        "-to-" +
        $IncomingVersion +
        ".json"
    )

    $temporaryRecordPath = "$recordPath.tmp"

    $recoveryState = [ordered]@{
        schema_version                 = 1
        previous_version               = $PreviousVersion
        incoming_version               = $IncomingVersion
        pre_upgrade_backup             = $BackupPath
        pre_upgrade_application        = $ApplicationArchive
        pre_upgrade_application_sha256 = $ApplicationSha256
        installer_log                  = $InstallerLog
        upgrade_attempted_at_utc       = [DateTime]::UtcNow.ToString("o")
        status                         = "pending"
    }

    $recoveryState |
    ConvertTo-Json `
        -Depth 4 |
    Set-Content `
        -LiteralPath $temporaryRecordPath `
        -Encoding UTF8 `
        -ErrorAction Stop

    Move-Item `
        -LiteralPath $temporaryRecordPath `
        -Destination $recordPath `
        -Force `
        -ErrorAction Stop

    Write-Host (
        "Upgrade recovery record created: " +
        $recordPath
    )

    return $recordPath
}

function Set-CareQueueUpgradeRecoveryStatus {
    param(
        [Parameter(Mandatory)]
        [string]$RecoveryRecord,

        [Parameter(Mandatory)]
        [ValidateSet(
            "pending",
            "completed",
            "failed"
        )]
        [string]$Status
    )

    if ($Mode -ne "Upgrade") {
        return
    }

    if (
        [string]::IsNullOrWhiteSpace($RecoveryRecord) `
            -or -not (
            Test-Path `
                -LiteralPath $RecoveryRecord `
                -PathType Leaf
        )
    ) {
        return
    }

    $state = Get-Content `
        -LiteralPath $RecoveryRecord `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop

    $state.status = $Status

    $temporaryRecordPath = "$RecoveryRecord.tmp"

    $state |
    ConvertTo-Json `
        -Depth 4 |
    Set-Content `
        -LiteralPath $temporaryRecordPath `
        -Encoding UTF8 `
        -ErrorAction Stop

    Move-Item `
        -LiteralPath $temporaryRecordPath `
        -Destination $RecoveryRecord `
        -Force `
        -ErrorAction Stop
}

function Set-CareQueueRollbackRecoveryStatus {
    param(
        [Parameter(Mandatory)]
        [string]$RecoveryRecord,

        [Parameter(Mandatory)]
        [ValidateSet(
            "failed",
            "rollback_staged",
            "rollback_activated",
            "rollback_completed"
        )]
        [string]$Status
    )

    if ($Mode -ne "Rollback") {
        return
    }

    if (
        [string]::IsNullOrWhiteSpace($RecoveryRecord) `
            -or -not (
            Test-Path `
                -LiteralPath $RecoveryRecord `
                -PathType Leaf
        )
    ) {
        return
    }

    $state = Get-Content `
        -LiteralPath $RecoveryRecord `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop

    $state.status = $Status

    $temporaryRecordPath = "$RecoveryRecord.tmp"

    $state |
    ConvertTo-Json `
        -Depth 4 |
    Set-Content `
        -LiteralPath $temporaryRecordPath `
        -Encoding UTF8 `
        -ErrorAction Stop

    Move-Item `
        -LiteralPath $temporaryRecordPath `
        -Destination $RecoveryRecord `
        -Force `
        -ErrorAction Stop
}

function Get-CareQueueFailedUpgradeRecovery {
    param(
        [Parameter(Mandatory)]
        [string]$RecoveryDirectory
    )

    if ($Mode -ne "Rollback") {
        return $null
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $RecoveryDirectory `
                -PathType Container
        )
    ) {
        throw "No CareQFlow upgrade recovery records are available."
    }

    $recoveryRecords = @(
        Get-ChildItem `
            -LiteralPath $RecoveryDirectory `
            -Filter "upgrade-*.json" `
            -File `
            -ErrorAction Stop |
        Sort-Object `
            -Property LastWriteTimeUtc `
            -Descending
    )

    $failedRecord = $null
    $failedState = $null

    foreach ($record in $recoveryRecords) {
        try {
            $state = Get-Content `
                -LiteralPath $record.FullName `
                -Raw `
                -ErrorAction Stop |
            ConvertFrom-Json `
                -ErrorAction Stop
        }
        catch {
            continue
        }

        if ([string]$state.status -eq "failed") {
            $failedRecord = $record
            $failedState = $state
            break
        }
    }

    if ($null -eq $failedRecord -or $null -eq $failedState) {
        throw "No failed CareQFlow upgrade recovery record was found."
    }

    if ([int]$failedState.schema_version -ne 1) {
        throw (
            "The failed CareQFlow upgrade recovery record has an " +
            "unsupported schema version."
        )
    }

    $previousVersion = [string]$failedState.previous_version
    $incomingVersion = [string]$failedState.incoming_version
    $backupPath = [string]$failedState.pre_upgrade_backup
    $applicationArchive = [string]$failedState.pre_upgrade_application
    $applicationSha256 = (
        [string]$failedState.pre_upgrade_application_sha256
    ).ToLowerInvariant()

    if (-not (Test-CareQueueVersion -Version $previousVersion)) {
        throw (
            "The failed upgrade recovery record contains an invalid " +
            "previous CareQFlow version: $previousVersion"
        )
    }

    if (-not (Test-CareQueueVersion -Version $incomingVersion)) {
        throw (
            "The failed upgrade recovery record contains an invalid " +
            "incoming CareQFlow version: $incomingVersion"
        )
    }

    if (
        [string]::IsNullOrWhiteSpace($backupPath) `
            -or -not (
            Test-Path `
                -LiteralPath $backupPath `
                -PathType Leaf
        )
    ) {
        throw (
            "The pre-upgrade rollback backup does not exist: " +
            $backupPath
        )
    }

    $backupItem = Get-Item `
        -LiteralPath $backupPath `
        -ErrorAction Stop

    if ($backupItem.Length -le 0) {
        throw (
            "The pre-upgrade rollback backup is empty: " +
            $backupPath
        )
    }

    if (
        [string]::IsNullOrWhiteSpace($applicationArchive) `
            -or -not (
            Test-Path `
                -LiteralPath $applicationArchive `
                -PathType Leaf
        )
    ) {
        throw (
            "The pre-upgrade application archive does not exist: " +
            $applicationArchive
        )
    }

    $applicationItem = Get-Item `
        -LiteralPath $applicationArchive `
        -ErrorAction Stop

    if ($applicationItem.Length -le 0) {
        throw (
            "The pre-upgrade application archive is empty: " +
            $applicationArchive
        )
    }

    if ($applicationSha256 -notmatch '^[0-9a-f]{64}$') {
        throw (
            "The failed upgrade recovery record contains an invalid " +
            "application archive checksum."
        )
    }

    $calculatedApplicationSha256 = (
        Get-FileHash `
            -LiteralPath $applicationArchive `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()

    if ($calculatedApplicationSha256 -ne $applicationSha256) {
        throw (
            "Pre-upgrade application archive checksum " +
            "verification failed."
        )
    }

    return [PSCustomObject]@{
        RecoveryRecord     = $failedRecord.FullName
        PreviousVersion    = $previousVersion
        IncomingVersion    = $incomingVersion
        BackupPath         = $backupPath
        ApplicationArchive = $applicationArchive
        ApplicationSha256  = $applicationSha256
    }
}

function New-CareQueueRollbackApplicationStage {
    param(
        [Parameter(Mandatory)]
        [string]$ArchivePath,

        [Parameter(Mandatory)]
        [string]$ExpectedSha256,

        [Parameter(Mandatory)]
        [string]$StagingDirectory
    )

    if ($Mode -ne "Rollback") {
        return $null
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $ArchivePath `
                -PathType Leaf
        )
    ) {
        throw (
            "The rollback application archive does not exist: " +
            $ArchivePath
        )
    }

    $archiveItem = Get-Item `
        -LiteralPath $ArchivePath `
        -ErrorAction Stop

    if ($archiveItem.Length -le 0) {
        throw (
            "The rollback application archive is empty: " +
            $ArchivePath
        )
    }

    if ($ExpectedSha256 -notmatch '^[0-9a-fA-F]{64}$') {
        throw (
            "The rollback application archive has an invalid " +
            "expected SHA256 checksum."
        )
    }

    $normalizedExpectedSha256 = `
        $ExpectedSha256.ToLowerInvariant()

    $calculatedSha256 = (
        Get-FileHash `
            -LiteralPath $ArchivePath `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()

    if ($calculatedSha256 -ne $normalizedExpectedSha256) {
        throw (
            "Rollback application archive checksum verification failed."
        )
    }

    Add-Type `
        -AssemblyName System.IO.Compression.FileSystem `
        -ErrorAction Stop

    $archive = $null

    try {
        $archive = [System.IO.Compression.ZipFile]::OpenRead(
            $ArchivePath
        )

        foreach ($entry in $archive.Entries) {
            $entryPath = [string]$entry.FullName

            if ([string]::IsNullOrWhiteSpace($entryPath)) {
                continue
            }

            $normalizedEntryPath = $entryPath.Replace(
                "\",
                "/"
            )

            if (
                [System.IO.Path]::IsPathRooted($entryPath) `
                    -or $normalizedEntryPath.StartsWith("/") `
                    -or $normalizedEntryPath -match (
                    '(^|/)\.\.(/|$)'
                )
            ) {
                throw (
                    "The rollback application archive contains an " +
                    "unsafe path: " +
                    $entryPath
                )
            }
        }
    }
    finally {
        if ($null -ne $archive) {
            $archive.Dispose()
        }
    }

    Remove-Item `
        -LiteralPath $StagingDirectory `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

    New-Item `
        -ItemType Directory `
        -Path $StagingDirectory `
        -Force `
        -ErrorAction Stop |
    Out-Null

    try {
        Write-Host (
            "Staging verified rollback application payload..."
        )

        Expand-Archive `
            -LiteralPath $ArchivePath `
            -DestinationPath $StagingDirectory `
            -Force `
            -ErrorAction Stop

        $requiredDirectories = @(
            "backend",
            "frontend",
            "deployment",
            "runtime",
            "vendor",
            "Service"
        )

        foreach ($relativeDirectory in $requiredDirectories) {
            $stagedDirectory = Join-Path `
                $StagingDirectory `
                $relativeDirectory

            if (
                -not (
                    Test-Path `
                        -LiteralPath $stagedDirectory `
                        -PathType Container
                )
            ) {
                throw (
                    "The staged rollback application is missing a " +
                    "required directory: " +
                    $relativeDirectory
                )
            }
        }

        Write-Host (
            "Rollback application payload staged and validated: " +
            $StagingDirectory
        )

        return $StagingDirectory
    }
    catch {
        Remove-Item `
            -LiteralPath $StagingDirectory `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue

        throw
    }
}

function New-CareQueueFailedApplicationArchive {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$IncomingVersion,

        [Parameter(Mandatory)]
        [string]$RecoveryDirectory
    )

    if ($Mode -ne "Rollback") {
        return $null
    }

    if (-not (Test-CareQueueVersion -Version $IncomingVersion)) {
        throw (
            "Cannot preserve the failed CareQFlow application " +
            "because the incoming version is invalid: " +
            $IncomingVersion
        )
    }

    $applicationDirectories = @(
        "backend",
        "frontend",
        "deployment",
        "runtime",
        "vendor",
        "Service"
    )

    $existingApplicationPaths = @(
        foreach ($relativeDirectory in $applicationDirectories) {
            $candidatePath = Join-Path `
                $InstallDirectory `
                $relativeDirectory

            if (
                Test-Path `
                    -LiteralPath $candidatePath `
                    -PathType Container
            ) {
                $candidatePath
            }
        }
    )

    if ($existingApplicationPaths.Count -eq 0) {
        throw (
            "No failed CareQFlow application directories are " +
            "available to preserve before rollback."
        )
    }

    New-Item `
        -ItemType Directory `
        -Path $RecoveryDirectory `
        -Force `
        -ErrorAction Stop |
    Out-Null

    $timestamp = [DateTime]::UtcNow.ToString(
        "yyyyMMdd-HHmmss"
    )

    $archivePath = Join-Path `
        $RecoveryDirectory `
    (
        "failed-application-" +
        $IncomingVersion +
        "-" +
        $timestamp +
        ".zip"
    )

    $checksumPath = "$archivePath.sha256"

    Write-Host (
        "Preserving failed CareQFlow application before rollback..."
    )

    Compress-Archive `
        -LiteralPath $existingApplicationPaths `
        -DestinationPath $archivePath `
        -CompressionLevel Optimal `
        -Force `
        -ErrorAction Stop

    if (
        -not (
            Test-Path `
                -LiteralPath $archivePath `
                -PathType Leaf
        )
    ) {
        throw (
            "The failed CareQFlow application archive was not created."
        )
    }

    $archiveItem = Get-Item `
        -LiteralPath $archivePath `
        -ErrorAction Stop

    if ($archiveItem.Length -le 0) {
        throw (
            "The failed CareQFlow application archive is empty: " +
            $archivePath
        )
    }

    $archiveSha256 = (
        Get-FileHash `
            -LiteralPath $archivePath `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()

    if ($archiveSha256 -notmatch '^[0-9a-f]{64}$') {
        throw (
            "Unable to calculate the failed CareQFlow application " +
            "archive SHA256 checksum."
        )
    }

    Set-Content `
        -LiteralPath $checksumPath `
        -Value (
        "$archiveSha256  " +
        [System.IO.Path]::GetFileName($archivePath)
    ) `
        -Encoding ASCII `
        -ErrorAction Stop

    $verificationSha256 = (
        Get-FileHash `
            -LiteralPath $archivePath `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()

    if ($verificationSha256 -ne $archiveSha256) {
        throw (
            "Failed CareQFlow application archive checksum " +
            "verification failed."
        )
    }

    Write-Host (
        "Failed CareQFlow application preserved: " +
        $archivePath
    )

    return [PSCustomObject]@{
        ArchivePath = $archivePath
        Sha256      = $archiveSha256
    }
}

function Stop-CareQueueServicesForRollback {
    if ($Mode -ne "Rollback") {
        return $null
    }

    $serviceNames = @(
        "CareQueueApi",
        "CareQueueCaddy"
    )

    $serviceStates = @()

    foreach ($serviceName in $serviceNames) {
        $service = Get-Service `
            -Name $serviceName `
            -ErrorAction Stop

        $wasRunning = $service.Status -eq "Running"

        $serviceStates += [PSCustomObject]@{
            Name       = $serviceName
            WasRunning = $wasRunning
        }

        if ($service.Status -ne "Stopped") {
            Write-Host (
                "Stopping Windows service for rollback: " +
                $serviceName
            )

            Stop-Service `
                -Name $serviceName `
                -Force `
                -ErrorAction Stop

            $service = Get-Service `
                -Name $serviceName `
                -ErrorAction Stop

            $service.WaitForStatus(
                "Stopped",
                [TimeSpan]::FromSeconds(30)
            )
        }

        $service = Get-Service `
            -Name $serviceName `
            -ErrorAction Stop

        if ($service.Status -ne "Stopped") {
            throw (
                "CareQFlow rollback could not stop Windows service: " +
                $serviceName
            )
        }
    }

    return $serviceStates
}

function Restore-CareQueueFailedApplicationAfterSwapFailure {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$FailedApplicationDirectory,

        [Parameter(Mandatory)]
        [object[]]$ServiceStates
    )

    $applicationDirectories = @(
        "backend",
        "frontend",
        "deployment",
        "runtime",
        "vendor",
        "Service"
    )

    Write-Host (
        "Restoring the failed CareQFlow application after " +
        "rollback swap failure..."
    )

    foreach ($relativeDirectory in $applicationDirectories) {
        $activePath = Join-Path `
            $InstallDirectory `
            $relativeDirectory

        if (Test-Path -LiteralPath $activePath) {
            Remove-Item `
                -LiteralPath $activePath `
                -Recurse `
                -Force `
                -ErrorAction Stop
        }
    }

    foreach ($relativeDirectory in $applicationDirectories) {
        $preservedPath = Join-Path `
            $FailedApplicationDirectory `
            $relativeDirectory

        if (
            Test-Path `
                -LiteralPath $preservedPath `
                -PathType Container
        ) {
            Move-Item `
                -LiteralPath $preservedPath `
                -Destination $InstallDirectory `
                -Force `
                -ErrorAction Stop
        }
    }

    foreach ($serviceState in $ServiceStates) {
        if (-not $serviceState.WasRunning) {
            continue
        }

        Write-Host (
            "Restarting restored Windows service: " +
            $serviceState.Name
        )

        Start-Service `
            -Name $serviceState.Name `
            -ErrorAction Stop

        $service = Get-Service `
            -Name $serviceState.Name `
            -ErrorAction Stop

        $service.WaitForStatus(
            "Running",
            [TimeSpan]::FromSeconds(30)
        )
    }

    Write-Host (
        "Failed CareQFlow application restored after swap failure."
    )
}

function Set-CareQueueRollbackApplication {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$StagedApplicationDirectory,

        [Parameter(Mandatory)]
        [string]$FailedApplicationDirectory
    )

    if ($Mode -ne "Rollback") {
        return $null
    }

    $applicationDirectories = @(
        "backend",
        "frontend",
        "deployment",
        "runtime",
        "vendor",
        "Service"
    )

    foreach ($relativeDirectory in $applicationDirectories) {
        $stagedPath = Join-Path `
            $StagedApplicationDirectory `
            $relativeDirectory

        if (
            -not (
                Test-Path `
                    -LiteralPath $stagedPath `
                    -PathType Container
            )
        ) {
            throw (
                "Cannot activate the rollback application because " +
                "the staged payload is missing: " +
                $relativeDirectory
            )
        }
    }

    Remove-Item `
        -LiteralPath $FailedApplicationDirectory `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

    New-Item `
        -ItemType Directory `
        -Path $FailedApplicationDirectory `
        -Force `
        -ErrorAction Stop |
    Out-Null

    $serviceStates = $null
    $activeApplicationMoved = $false

    try {
        $serviceStates = @(
            Stop-CareQueueServicesForRollback
        )

        foreach ($relativeDirectory in $applicationDirectories) {
            $activePath = Join-Path `
                $InstallDirectory `
                $relativeDirectory

            if (
                Test-Path `
                    -LiteralPath $activePath `
                    -PathType Container
            ) {
                Move-Item `
                    -LiteralPath $activePath `
                    -Destination $FailedApplicationDirectory `
                    -Force `
                    -ErrorAction Stop
            }
        }

        $activeApplicationMoved = $true

        foreach ($relativeDirectory in $applicationDirectories) {
            $stagedPath = Join-Path `
                $StagedApplicationDirectory `
                $relativeDirectory

            Move-Item `
                -LiteralPath $stagedPath `
                -Destination $InstallDirectory `
                -Force `
                -ErrorAction Stop
        }

        foreach ($relativeDirectory in $applicationDirectories) {
            $activatedPath = Join-Path `
                $InstallDirectory `
                $relativeDirectory

            if (
                -not (
                    Test-Path `
                        -LiteralPath $activatedPath `
                        -PathType Container
                )
            ) {
                throw (
                    "Rollback application activation failed because " +
                    "a required directory is missing: " +
                    $relativeDirectory
                )
            }
        }

        Write-Host (
            "Previous CareQFlow application payload activated."
        )

        return [PSCustomObject]@{
            FailedApplicationDirectory = $FailedApplicationDirectory
            Services                   = $serviceStates
        }
    }
    catch {
        $swapFailure = $_

        if ($activeApplicationMoved) {
            try {
                Restore-CareQueueFailedApplicationAfterSwapFailure `
                    -InstallDirectory $InstallDirectory `
                    -FailedApplicationDirectory `
                    $FailedApplicationDirectory `
                    -ServiceStates $serviceStates
            }
            catch {
                throw (
                    "CareQFlow rollback application activation failed, " +
                    "and restoration of the failed application also " +
                    "failed. Activation error: " +
                    $swapFailure.Exception.Message +
                    " Restoration error: " +
                    $_.Exception.Message
                )
            }
        }
        elseif ($null -ne $serviceStates) {
            foreach ($serviceState in $serviceStates) {
                if (-not $serviceState.WasRunning) {
                    continue
                }

                try {
                    Start-Service `
                        -Name $serviceState.Name `
                        -ErrorAction Stop
                }
                catch {
                    Write-Host (
                        "Unable to restart service after rollback " +
                        "preparation failure: " +
                        $serviceState.Name
                    )
                }
            }
        }

        throw $swapFailure
    }
}

function Invoke-CareQueueRollbackDatabaseStaging {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$DataDirectory,

        [Parameter(Mandatory)]
        [string]$BackupPath
    )

    if ($Mode -ne "Rollback") {
        return
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $BackupPath `
                -PathType Leaf
        )
    ) {
        throw (
            "The pre-upgrade rollback backup does not exist: " +
            $BackupPath
        )
    }

    $backupItem = Get-Item `
        -LiteralPath $BackupPath `
        -ErrorAction Stop

    if ($backupItem.Length -le 0) {
        throw (
            "The pre-upgrade rollback backup is empty: " +
            $BackupPath
        )
    }

    $restoreScript = Join-Path `
        $InstallDirectory `
        "backend\scripts\restore_encrypted_backup.py"

    if (
        -not (
            Test-Path `
                -LiteralPath $restoreScript `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow rollback requires the installed restore script: " +
            $restoreScript
        )
    }

    $pythonExecutable = Join-Path `
        $InstallDirectory `
        "backend\.venv\Scripts\python.exe"

    if (
        -not (
            Test-Path `
                -LiteralPath $pythonExecutable `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow rollback requires the installed Python " +
            "environment: " +
            $pythonExecutable
        )
    }

    $environmentFile = Join-Path `
        $DataDirectory `
        "Config\carequeue.env"

    if (
        -not (
            Test-Path `
                -LiteralPath $environmentFile `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow rollback requires the production " +
            "configuration: " +
            $environmentFile
        )
    }

    Get-Content `
        -LiteralPath $environmentFile `
        -ErrorAction Stop |
    ForEach-Object {
        $line = $_.Trim()

        if (
            [string]::IsNullOrWhiteSpace($line) `
                -or $line.StartsWith("#") `
                -or -not $line.Contains("=")
        ) {
            return
        }

        $name, $value = $line.Split("=", 2)

        [Environment]::SetEnvironmentVariable(
            $name.Trim(),
            $value.Trim(),
            "Process"
        )
    }

    Write-Host (
        "Staging the verified pre-upgrade database backup " +
        "for rollback..."
    )

    & $pythonExecutable `
        $restoreScript `
        $BackupPath

    if ($LASTEXITCODE -ne 0) {
        throw (
            "CareQFlow rollback database staging failed with " +
            "exit code " +
            $LASTEXITCODE +
            "."
        )
    }

    Write-Host (
        "Rollback database preparation completed successfully."
    )
}

function Invoke-CareQueueRollbackDatabaseActivation {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$DataDirectory
    )

    if ($Mode -ne "Rollback") {
        return
    }

    $activationScript = Join-Path `
        $InstallDirectory `
        "backend\scripts\activate_staged_recovery.py"

    if (
        -not (
            Test-Path `
                -LiteralPath $activationScript `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow rollback requires the installed recovery " +
            "activation script: " +
            $activationScript
        )
    }

    $pythonExecutable = Join-Path `
        $InstallDirectory `
        "backend\.venv\Scripts\python.exe"

    if (
        -not (
            Test-Path `
                -LiteralPath $pythonExecutable `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow rollback requires the installed Python " +
            "environment: " +
            $pythonExecutable
        )
    }

    $environmentFile = Join-Path `
        $DataDirectory `
        "Config\carequeue.env"

    if (
        -not (
            Test-Path `
                -LiteralPath $environmentFile `
                -PathType Leaf
        )
    ) {
        throw (
            "CareQFlow rollback requires the production " +
            "configuration: " +
            $environmentFile
        )
    }

    Get-Content `
        -LiteralPath $environmentFile `
        -ErrorAction Stop |
    ForEach-Object {
        $line = $_.Trim()

        if (
            [string]::IsNullOrWhiteSpace($line) `
                -or $line.StartsWith("#") `
                -or -not $line.Contains("=")
        ) {
            return
        }

        $name, $value = $line.Split("=", 2)

        [Environment]::SetEnvironmentVariable(
            $name.Trim(),
            $value.Trim(),
            "Process"
        )
    }

    $databasePath = Join-Path `
        $DataDirectory `
        "Data\auth_tracker.sqlcipher.db"

    $backupDirectory = Join-Path `
        $DataDirectory `
        "Backups"

    $restoreDirectory = Join-Path `
        $DataDirectory `
        "Restores"

    Write-Host (
        "Activating the staged pre-upgrade database for rollback..."
    )

    & $pythonExecutable `
        $activationScript `
        --service-name "CareQueueApi" `
        --database-path $databasePath `
        --backup-directory $backupDirectory `
        --restore-directory $restoreDirectory

    if ($LASTEXITCODE -ne 0) {
        throw (
            "CareQFlow rollback database activation failed with " +
            "exit code " +
            $LASTEXITCODE +
            ". CareQFlow services remain stopped."
        )
    }

    Write-Host (
        "Rollback database activation completed successfully."
    )
}

function Start-CareQueueServicesAfterRollback {
    if ($Mode -ne "Rollback") {
        return
    }

    foreach ($serviceName in @(
            "CareQueueApi",
            "CareQueueCaddy"
        )) {
        $service = Get-Service `
            -Name $serviceName `
            -ErrorAction Stop

        if ($service.Status -ne "Running") {
            Write-Host (
                "Starting restored Windows service: " +
                $serviceName
            )

            Start-Service `
                -Name $serviceName `
                -ErrorAction Stop
        }

        $service = Get-Service `
            -Name $serviceName `
            -ErrorAction Stop

        $service.WaitForStatus(
            "Running",
            [TimeSpan]::FromSeconds(30)
        )
    }

    Write-Host (
        "CareQFlow services started after rollback activation."
    )
}

function Stop-CareQueueServicesAfterRollbackFailure {
    if ($Mode -ne "Rollback") {
        return
    }

    foreach ($serviceName in @(
            "CareQueueApi",
            "CareQueueCaddy"
        )) {
        $service = Get-Service `
            -Name $serviceName `
            -ErrorAction Stop

        if ($service.Status -ne "Stopped") {
            Write-Host (
                "Stopping Windows service after rollback failure: " +
                $serviceName
            )

            Stop-Service `
                -Name $serviceName `
                -Force `
                -ErrorAction Stop

            $service = Get-Service `
                -Name $serviceName `
                -ErrorAction Stop

            $service.WaitForStatus(
                "Stopped",
                [TimeSpan]::FromSeconds(30)
            )
        }

        $service = Get-Service `
            -Name $serviceName `
            -ErrorAction Stop

        if ($service.Status -ne "Stopped") {
            throw (
                "CareQFlow could not stop Windows service after " +
                "rollback failure: " +
                $serviceName
            )
        }
    }

    Write-Host (
        "CareQFlow services stopped after rollback failure."
    )
}

function Restore-CareQueueRollbackInstallStateVersion {
    param(
        [Parameter(Mandatory)]
        [string]$InstallStatePath,

        [Parameter(Mandatory)]
        [string]$PreviousVersion
    )

    if ($Mode -ne "Rollback") {
        return
    }

    if (-not (Test-CareQueueVersion -Version $PreviousVersion)) {
        throw (
            "Cannot restore installed version metadata because the " +
            "previous CareQFlow version is invalid: " +
            $PreviousVersion
        )
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $InstallStatePath `
                -PathType Leaf
        )
    ) {
        throw (
            "Cannot restore installed version metadata because the " +
            "installation state file is missing: " +
            $InstallStatePath
        )
    }

    $installState = Get-Content `
        -LiteralPath $InstallStatePath `
        -Raw `
        -ErrorAction Stop |
    ConvertFrom-Json `
        -ErrorAction Stop

    $installState.installed_version = $PreviousVersion

    $temporaryInstallStatePath = "$InstallStatePath.tmp"

    $installState |
    ConvertTo-Json `
        -Depth 4 |
    Set-Content `
        -LiteralPath $temporaryInstallStatePath `
        -Encoding UTF8 `
        -ErrorAction Stop

    Move-Item `
        -LiteralPath $temporaryInstallStatePath `
        -Destination $InstallStatePath `
        -Force `
        -ErrorAction Stop

    Write-Host (
        "Installed CareQFlow version metadata restored to " +
        $PreviousVersion
    )
}

function Remove-CareQueueSuccessfulRollbackStaging {
    if ($Mode -ne "Rollback") {
        return
    }

    foreach ($stagingDirectory in @(
            $rollbackApplicationStagingDirectory,
            $failedApplicationStagingDirectory
        )) {
        if (
            -not [string]::IsNullOrWhiteSpace($stagingDirectory) `
                -and (
                Test-Path `
                    -LiteralPath $stagingDirectory `
                    -PathType Container
            )
        ) {
            Remove-Item `
                -LiteralPath $stagingDirectory `
                -Recurse `
                -Force `
                -ErrorAction Stop
        }
    }

    Write-Host (
        "Temporary rollback application staging directories removed."
    )
}

function Set-CareQueueCaddyRootCertificate {
    param(
        [Parameter(Mandatory)]
        [string]$DataDirectory,

        [ValidateRange(1, 60)]
        [int]$MaximumAttempts = 30,

        [ValidateRange(1, 10)]
        [int]$RetryDelaySeconds = 1
    )

    $rootCertificatePath = Join-Path `
        $DataDirectory `
        "Caddy\Data\caddy\pki\authorities\local\root.crt"

    Write-Output (
        "Waiting for the CareQFlow HTTPS root certificate: " +
        $rootCertificatePath
    )

    $certificateAvailable = $false

    for (
        $attempt = 1
        $attempt -le $MaximumAttempts
        $attempt++
    ) {
        if (
            Test-Path `
                -LiteralPath $rootCertificatePath `
                -PathType Leaf
        ) {
            $certificateAvailable = $true
            break
        }

        if ($attempt -lt $MaximumAttempts) {
            Start-Sleep `
                -Seconds $RetryDelaySeconds
        }
    }

    if (-not $certificateAvailable) {
        throw (
            "CareQFlow HTTPS certificate trust could not be configured " +
            "because Caddy did not create its root certificate after " +
            "$MaximumAttempts attempts. Expected certificate: " +
            $rootCertificatePath
        )
    }

    try {
        $rootCertificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
            $rootCertificatePath
        )
    }
    catch {
        throw (
            "CareQFlow HTTPS certificate trust could not be configured " +
            "because the generated Caddy root certificate could not be " +
            "read. Certificate: $rootCertificatePath. Error: " +
            $_.Exception.Message
        )
    }

    $certificateThumbprint = $rootCertificate.Thumbprint

    if ([string]::IsNullOrWhiteSpace($certificateThumbprint)) {
        throw (
            "CareQFlow HTTPS certificate trust could not be configured " +
            "because the generated root certificate has no thumbprint."
        )
    }

    $existingCertificate = Get-ChildItem `
        -Path "Cert:\LocalMachine\Root" `
        -ErrorAction Stop |
    Where-Object {
        $_.Thumbprint -eq $certificateThumbprint
    } |
    Select-Object -First 1

    if ($existingCertificate) {
        Write-Output (
            "CareQFlow HTTPS root certificate is already trusted. " +
            "Thumbprint: $certificateThumbprint"
        )

        return
    }

    Write-Output (
        "Trusting the CareQFlow HTTPS root certificate. " +
        "Thumbprint: $certificateThumbprint"
    )

    try {
        $importedCertificate = Import-Certificate `
            -FilePath $rootCertificatePath `
            -CertStoreLocation "Cert:\LocalMachine\Root" `
            -ErrorAction Stop

        if (-not $importedCertificate) {
            throw "Import-Certificate returned no certificate."
        }
    }
    catch {
        throw (
            "CareQFlow HTTPS root certificate could not be imported " +
            "into the Windows Local Machine trusted root store. " +
            "Error: $($_.Exception.Message)"
        )
    }

    $trustedCertificate = Get-ChildItem `
        -Path "Cert:\LocalMachine\Root" `
        -ErrorAction Stop |
    Where-Object {
        $_.Thumbprint -eq $certificateThumbprint
    } |
    Select-Object -First 1

    if (-not $trustedCertificate) {
        throw (
            "CareQFlow imported the HTTPS root certificate, but " +
            "verification of the Windows trusted root store failed. " +
            "Thumbprint: $certificateThumbprint"
        )
    }

    Write-Output (
        "CareQFlow HTTPS root certificate trusted successfully. " +
        "Thumbprint: $certificateThumbprint"
    )
}

function Assert-PostInstallationHealth {
    param(
        [Parameter(Mandatory)]
        [string]$InstallDirectory,

        [Parameter(Mandatory)]
        [string]$DataDirectory,

        [Parameter(Mandatory)]
        [string]$ApplicationOrigin,

        [ValidateRange(1, 60)]
        [int]$MaximumAttempts = 30,

        [ValidateRange(1, 30)]
        [int]$RetryDelaySeconds = 2
    )

    $requiredInstalledFiles = @(
        (
            Join-Path `
                $InstallDirectory `
                "frontend\dist\index.html"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "runtime\python\python.exe"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "vendor\caddy\caddy.exe"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "Service\CareQueueApi.exe"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "Service\CareQueueCaddy.exe"
        ),
        (
            Join-Path `
                $InstallDirectory `
                "deployment\windows\run-api.ps1"
        )
    )

    foreach ($requiredInstalledFile in $requiredInstalledFiles) {
        if (
            -not (
                Test-Path `
                    -LiteralPath $requiredInstalledFile `
                    -PathType Leaf
            )
        ) {
            throw (
                "Post-installation validation failed because a " +
                "required installed file is missing: " +
                $requiredInstalledFile
            )
        }
    }

    $backendPackageDirectory = Join-Path `
        $InstallDirectory `
        "backend\authstatus_api"

    if (
        -not (
            Test-Path `
                -LiteralPath $backendPackageDirectory `
                -PathType Container
        )
    ) {
        throw (
            "Post-installation validation failed because the " +
            "installed backend package directory is missing: " +
            $backendPackageDirectory
        )
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $DataDirectory `
                -PathType Container
        )
    ) {
        throw (
            "Post-installation validation failed because the " +
            "CareQFlow data directory is missing: $DataDirectory"
        )
    }

    $requiredServices = @(
        "CareQueueApi",
        "CareQueueCaddy"
    )

    foreach ($requiredServiceName in $requiredServices) {
        $lastServiceStatus = $null
        $serviceRunning = $false

        for (
            $attempt = 1
            $attempt -le $MaximumAttempts
            $attempt++
        ) {
            $service = Get-Service `
                -Name $requiredServiceName `
                -ErrorAction SilentlyContinue

            if (-not $service) {
                throw (
                    "Post-installation validation failed because the " +
                    "Windows service was not found: $requiredServiceName"
                )
            }

            $lastServiceStatus = $service.Status

            if ($service.Status -eq "Running") {
                $serviceRunning = $true
                break
            }

            if ($attempt -lt $MaximumAttempts) {
                Start-Sleep `
                    -Seconds $RetryDelaySeconds
            }
        }

        if (-not $serviceRunning) {
            throw (
                "Post-installation validation failed because the " +
                "Windows service is not running: " +
                "$requiredServiceName. Current status: " +
                "$lastServiceStatus."
            )
        }
    }

    Set-CareQueueCaddyRootCertificate `
        -DataDirectory $DataDirectory

    $normalizedApplicationOrigin = $ApplicationOrigin.TrimEnd("/")

    try {
        $applicationUri = [Uri]$normalizedApplicationOrigin
        $applicationHostname = $applicationUri.Host
    }
    catch {
        throw (
            "Post-installation validation could not parse the " +
            "CareQFlow application origin: $normalizedApplicationOrigin. " +
            "Error: $($_.Exception.Message)"
        )
    }
    
    try {
        $resolvedAddresses = @(
            [System.Net.Dns]::GetHostAddresses($applicationHostname)
        )
    }
    catch {
        throw (
            "Post-installation validation failed because the CareQFlow " +
            "hostname '$applicationHostname' could not be resolved. " +
            "Expected a local loopback mapping for CareQFlow. " +
            "Error: $($_.Exception.Message)"
        )
    }
    
    if ($resolvedAddresses.Count -eq 0) {
        throw (
            "Post-installation validation failed because the CareQFlow " +
            "hostname '$applicationHostname' resolved to no addresses."
        )
    }
    
    $loopbackResolved = $false
    
    foreach ($resolvedAddress in $resolvedAddresses) {
        if ([System.Net.IPAddress]::IsLoopback($resolvedAddress)) {
            $loopbackResolved = $true
            break
        }
    }
    
    if (-not $loopbackResolved) {
        $resolvedAddressText = (
            $resolvedAddresses |
            ForEach-Object {
                $_.IPAddressToString
            }
        ) -join ", "
    
        throw (
            "Post-installation validation failed because the CareQFlow " +
            "hostname '$applicationHostname' did not resolve to a local " +
            "loopback address. Resolved addresses: $resolvedAddressText"
        )
    }

    $validationEndpoints = @(
        [ordered]@{
            Name = "HTTPS frontend"
            Uri  = "$normalizedApplicationOrigin/"
        },
        [ordered]@{
            Name = "API liveness"
            Uri  = "$normalizedApplicationOrigin/api/health/live"
        },
        [ordered]@{
            Name = "API readiness"
            Uri  = "$normalizedApplicationOrigin/api/health/ready"
        }
    )

    foreach ($validationEndpoint in $validationEndpoints) {
        $lastFailureMessage = $null
        $validationSucceeded = $false

        for (
            $attempt = 1
            $attempt -le $MaximumAttempts
            $attempt++
        ) {
            try {
                $response = Invoke-WebRequest `
                    -Uri $validationEndpoint.Uri `
                    -UseBasicParsing `
                    -TimeoutSec 5 `
                    -ErrorAction Stop

                if (
                    $response.StatusCode -ge 200 `
                        -and $response.StatusCode -lt 400
                ) {
                    $validationSucceeded = $true
                    break
                }

                $lastFailureMessage = (
                    "HTTP status code $($response.StatusCode)"
                )
            }
            catch {
                $lastFailureMessage = $_.Exception.Message
            }
            
            Write-Output (
                "Post-installation health check failed for " +
                "$($validationEndpoint.Name) at " +
                "$($validationEndpoint.Uri) " +
                "(attempt $attempt of $MaximumAttempts): " +
                $lastFailureMessage
            )
            
            if ($attempt -lt $MaximumAttempts) {
                Start-Sleep `
                    -Seconds $RetryDelaySeconds
            }
        }

        if (-not $validationSucceeded) {
            throw (
                "Post-installation validation failed for " +
                "$($validationEndpoint.Name) at " +
                "$($validationEndpoint.Uri) after " +
                "$MaximumAttempts attempts. Last failure: " +
                $lastFailureMessage
            )
        }
    }
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
        throw "The CareQFlow payload hash manifest is empty."
    }

    $manifestEntries = @{}

    foreach ($manifestLine in $manifestLines) {
        if (
            $manifestLine `
                -notmatch `
                "^(?<Hash>[0-9a-fA-F]{64})  (?<Path>.+)$"
        ) {
            throw (
                "The CareQFlow payload hash manifest contains an " +
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
                "The CareQFlow payload hash manifest contains an " +
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
                "The CareQFlow payload hash manifest path escapes " +
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
                "The CareQFlow payload hash manifest contains a " +
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
                "A file listed in the CareQFlow payload hash " +
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
                "CareQFlow payload hash validation failed for " +
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
                "The CareQFlow payload contains a file that is not " +
                "listed in the hash manifest: $actualRelativePath"
            )
        }
    }

    if ($actualPayloadFiles.Count -ne $manifestEntries.Count) {
        throw (
            "The CareQFlow payload file count does not match the " +
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
        "CareQFlow installation requires Administrator privileges."
    )

    exit $exitCodeAdministratorRequired
}

if (
    $Mode -ne "Uninstall" `
        -and [string]::IsNullOrWhiteSpace($ApplicationOrigin)
) {
    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeInvalidInstallState `
        -Message (
        "ApplicationOrigin is required for Install, Upgrade, Repair, " +
        "and Rollback operations."
    )

    exit $exitCodeInvalidInstallState
}

try {
    Set-CareQueueLocalHostname `
        -ApplicationOrigin $ApplicationOrigin
}
catch {
    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeInvalidInstallState `
        -Message (
        "Unable to configure the CareQFlow local hostname: " +
        $_.Exception.Message
    )

    exit $exitCodeInvalidInstallState
}

$careQueueIsInstalled = Test-CareQueueInstallation `
    -InstallDirectory $InstallDirectory

$modeValidationMessage = $null

switch ($Mode) {
    "Install" {
        if ($careQueueIsInstalled) {
            $modeValidationMessage = (
                "CareQFlow is already installed. Use -Mode Upgrade " +
                "or -Mode Repair."
            )
        }
    }

    "Upgrade" {
        if (-not $careQueueIsInstalled) {
            $modeValidationMessage = (
                "CareQFlow is not installed. Use -Mode Install."
            )
        }
    }

    "Repair" {
        if (-not $careQueueIsInstalled) {
            $modeValidationMessage = (
                "CareQFlow is not installed. Use -Mode Install."
            )
        }
    }

    "Rollback" {
        if (-not $careQueueIsInstalled) {
            $modeValidationMessage = (
                "CareQFlow is not installed, so there is no " +
                "installation to roll back."
            )
        }
    }

    "Uninstall" {
        if (-not $careQueueIsInstalled) {
            $modeValidationMessage = (
                "CareQFlow is not installed, so there is nothing " +
                "to uninstall."
            )
        }
    }
}

if ($modeValidationMessage) {
    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodeInvalidInstallState `
        -Message $modeValidationMessage

    exit $exitCodeInvalidInstallState
}

if ($Mode -eq "Uninstall") {
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
            "CareQueue-Uninstall-$timestamp.log"
    }
    catch {
        Write-InstallerResult `
            -Status "failed" `
            -ExitCode $exitCodeLoggingFailure `
            -Message (
            "Unable to prepare the CareQFlow uninstaller log: " +
            $_.Exception.Message
        )

        exit $exitCodeLoggingFailure
    }

    $uninstallScriptPath = Join-Path `
        $InstallDirectory `
        "deployment\windows\uninstall-production.ps1"

    if (
        -not (
            Test-Path `
                -LiteralPath $uninstallScriptPath `
                -PathType Leaf
        )
    ) {
        Write-InstallerResult `
            -Status "failed" `
            -ExitCode $exitCodeInstallationFailure `
            -Message (
            "The installed CareQFlow uninstall engine was not " +
            "found: $uninstallScriptPath"
        ) `
            -LogPath $logPath

        exit $exitCodeInstallationFailure
    }

    $uninstallArguments = @(
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $uninstallScriptPath,
        "-InstallDirectory",
        $InstallDirectory,
        "-DataDirectory",
        $DataDirectory,
        "-DeploymentDirectory",
        (
            Join-Path `
                $InstallDirectory `
                "deployment\windows"
        )
    )

    @(
        "CareQFlow Windows Installer"
        "Mode: Uninstall"
        "Started UTC: $([DateTime]::UtcNow.ToString('o'))"
        "Install directory: $InstallDirectory"
        "Data directory: $DataDirectory"
        ""
    ) |
    Set-Content `
        -LiteralPath $logPath `
        -Encoding utf8

    try {
        & powershell.exe @uninstallArguments 2>&1 |
        Tee-Object `
            -FilePath $logPath `
            -Append

        $uninstallExitCode = $LASTEXITCODE

        if ($uninstallExitCode -ne 0) {
            throw (
                "The CareQFlow uninstall engine failed with exit " +
                "code $uninstallExitCode."
            )
        }
    }
    catch {
        $failureMessage = $_.Exception.Message

        @(
            ""
            "Uninstall operation failed."
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
        "Uninstall operation completed successfully."
        "Completed UTC: $([DateTime]::UtcNow.ToString('o'))"
    ) |
    Add-Content `
        -LiteralPath $logPath `
        -Encoding utf8

    Write-InstallerResult `
        -Status "succeeded" `
        -ExitCode $exitCodeSuccess `
        -Message (
        "CareQFlow Uninstall operation completed successfully."
    ) `
        -LogPath $logPath

    exit $exitCodeSuccess
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
                "A required CareQFlow payload path was not found: " +
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

    $incomingVersion = [string]$payloadMetadata.application.backend_version

    if (-not (Test-CareQueueVersion -Version $incomingVersion)) {
        throw (
            "The CareQFlow payload contains an invalid application " +
            "version: $incomingVersion"
        )
    }

    if ($payloadMetadata.schema_version -ne 1) {
        throw (
            "Unsupported CareQFlow payload schema version: " +
            $payloadMetadata.schema_version
        )
    }

    if (
        [string]$payloadMetadata.application.name `
            -ne "CareQueue"
    ) {
        throw (
            "The supplied payload is not a CareQFlow installer payload."
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

if ($Mode -eq "Upgrade") {
    try {
        $installedVersion = Get-CareQueueInstalledVersion `
            -InstallStatePath $installStatePath

        Assert-CareQueueUpgradeVersion `
            -IncomingVersion $incomingVersion `
            -InstalledVersion $installedVersion
    }
    catch {
        Write-InstallerResult `
            -Status "failed" `
            -ExitCode $exitCodeInvalidInstallState `
            -Message $_.Exception.Message

        exit $exitCodeInvalidInstallState
    }
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
        "Unable to prepare the CareQFlow installer log: " +
        $_.Exception.Message
    )

    exit $exitCodeLoggingFailure
}

if ($Mode -eq "Rollback") {
    $rollbackDatabaseActivated = $false

    try {
        $rollbackRecovery = Get-CareQueueFailedUpgradeRecovery `
            -RecoveryDirectory $upgradeRecoveryDirectory

        if ($null -eq $rollbackRecovery) {
            throw (
                "The CareQFlow rollback recovery state was not returned."
            )
        }

        $rollbackRecoveryRecord = `
            [string]$rollbackRecovery.RecoveryRecord

        $rollbackPreviousVersion = `
            [string]$rollbackRecovery.PreviousVersion

        $rollbackIncomingVersion = `
            [string]$rollbackRecovery.IncomingVersion

        $rollbackBackupPath = `
            [string]$rollbackRecovery.BackupPath

        $rollbackApplicationArchive = `
            [string]$rollbackRecovery.ApplicationArchive

        $rollbackApplicationSha256 = `
            [string]$rollbackRecovery.ApplicationSha256
        
        $stagedRollbackApplication = `
            New-CareQueueRollbackApplicationStage `
            -ArchivePath $rollbackApplicationArchive `
            -ExpectedSha256 $rollbackApplicationSha256 `
            -StagingDirectory $rollbackApplicationStagingDirectory
        
        if ([string]::IsNullOrWhiteSpace($stagedRollbackApplication)) {
            throw (
                "The staged CareQFlow rollback application path " +
                "was not returned."
            )
        }

        $failedApplication = New-CareQueueFailedApplicationArchive `
            -InstallDirectory $InstallDirectory `
            -IncomingVersion $rollbackIncomingVersion `
            -RecoveryDirectory $failedApplicationRecoveryDirectory

        if ($null -eq $failedApplication) {
            throw (
                "The failed CareQFlow application archive " +
                "was not returned."
            )
        }

        $failedApplicationArchive = `
            [string]$failedApplication.ArchivePath

        $failedApplicationSha256 = `
            [string]$failedApplication.Sha256

        if (
            [string]::IsNullOrWhiteSpace($failedApplicationArchive) `
                -or [string]::IsNullOrWhiteSpace(
                $failedApplicationSha256
            )
        ) {
            throw (
                "The failed CareQFlow application archive metadata " +
                "is incomplete."
            )
        }

        $rollbackApplicationActivation = `
            Set-CareQueueRollbackApplication `
            -InstallDirectory $InstallDirectory `
            -StagedApplicationDirectory $stagedRollbackApplication `
            -FailedApplicationDirectory `
            $failedApplicationStagingDirectory

        if ($null -eq $rollbackApplicationActivation) {
            throw (
                "The CareQFlow rollback application was not activated."
            )
        }

        Invoke-CareQueueRollbackDatabaseStaging `
            -InstallDirectory $InstallDirectory `
            -DataDirectory $DataDirectory `
            -BackupPath $rollbackBackupPath

        Set-CareQueueRollbackRecoveryStatus `
            -RecoveryRecord $rollbackRecoveryRecord `
            -Status "rollback_staged"

        Invoke-CareQueueRollbackDatabaseActivation `
            -InstallDirectory $InstallDirectory `
            -DataDirectory $DataDirectory

        $rollbackDatabaseActivated = $true

        Set-CareQueueRollbackRecoveryStatus `
            -RecoveryRecord $rollbackRecoveryRecord `
            -Status "rollback_activated"

        Start-CareQueueServicesAfterRollback

        Assert-PostInstallationHealth `
            -InstallDirectory $InstallDirectory `
            -DataDirectory $DataDirectory `
            -ApplicationOrigin $ApplicationOrigin

        Restore-CareQueueRollbackInstallStateVersion `
            -InstallStatePath $installStatePath `
            -PreviousVersion $rollbackPreviousVersion

        Set-CareQueueRollbackRecoveryStatus `
            -RecoveryRecord $rollbackRecoveryRecord `
            -Status "rollback_completed"

        try {
            Remove-CareQueueSuccessfulRollbackStaging
        }
        catch {
            Add-Content `
                -LiteralPath $logPath `
                -Value (
                "Rollback completed successfully, but temporary " +
                "staging cleanup failed: " +
                $_.Exception.Message
            ) `
                -Encoding utf8
        }

        @(
            "CareQFlow Windows Rollback Recovery"
            "Recovery record: $rollbackRecoveryRecord"
            "Previous version: $rollbackPreviousVersion"
            "Failed incoming version: $rollbackIncomingVersion"
            "Pre-upgrade backup: $rollbackBackupPath"
            "Pre-upgrade application: $rollbackApplicationArchive"
            "Application SHA256: $rollbackApplicationSha256"
            "Staged application: $stagedRollbackApplication"
            "Failed application archive: $failedApplicationArchive"
            "Failed application SHA256: $failedApplicationSha256"
            ""
            "Rollback recovery assets validated successfully."
            "Previous application payload activated successfully."
            "Pre-upgrade database staged successfully."
            "Pre-upgrade database activated successfully."
            "CareQFlow services started and validated successfully."
            "Installed version metadata restored successfully."
            "Upgrade recovery status: rollback_completed"
        ) |
        Add-Content `
            -LiteralPath $logPath `
            -Encoding utf8

        Write-InstallerResult `
            -Status "success" `
            -ExitCode $exitCodeSuccess `
            -Message (
            "Previous CareQFlow application payload and pre-upgrade " +
            "database were activated successfully. CareQFlow services " +
            "passed post-rollback validation."
        ) `
            -LogPath $logPath

        exit $exitCodeSuccess
    }
    catch {
        $failureMessage = $_.Exception.Message

        if ($rollbackDatabaseActivated) {
            try {
                Stop-CareQueueServicesAfterRollbackFailure
            }
            catch {
                Add-Content `
                    -LiteralPath $logPath `
                    -Value (
                    "Rollback failed after database activation, and " +
                    "CareQFlow services could not be fully stopped: " +
                    $_.Exception.Message
                ) `
                    -Encoding utf8
            }

            Add-Content `
                -LiteralPath $logPath `
                -Value (
                "Rollback failed after pre-upgrade database " +
                "activation. The recovery record retains its " +
                "last durable rollback state."
            ) `
                -Encoding utf8
        }

        Write-InstallerResult `
            -Status "failed" `
            -ExitCode $exitCodeInvalidInstallState `
            -Message $failureMessage `
            -LogPath $logPath

        exit $exitCodeInvalidInstallState
    }
}

if ($Mode -eq "Upgrade") {
    try {
        $preUpgradeBackupPath = New-VerifiedPreUpgradeBackup `
            -InstallDirectory $InstallDirectory `
            -DataDirectory $DataDirectory `
            -BackupDirectory $backupDirectory

        if ([string]::IsNullOrWhiteSpace($preUpgradeBackupPath)) {
            throw (
                "The verified pre-upgrade backup path was not returned. " +
                "The CareQFlow application has not been replaced."
            )
        }

        Add-Content `
            -LiteralPath $logPath `
            -Value (
            "Verified pre-upgrade backup: " +
            $preUpgradeBackupPath
        ) `
            -Encoding utf8

        if ([string]::IsNullOrWhiteSpace($installedVersion)) {
            throw (
                "The installed CareQFlow version metadata is required " +
                "to create an application rollback payload."
            )
        }
            
        $preUpgradeApplication = `
            New-VerifiedPreUpgradeApplicationArchive `
            -InstallDirectory $InstallDirectory `
            -InstalledVersion $installedVersion `
            -RecoveryDirectory $applicationRecoveryDirectory
            
        if ($null -eq $preUpgradeApplication) {
            throw (
                "The verified pre-upgrade application archive " +
                "was not returned."
            )
        }
            
        $preUpgradeApplicationArchive = `
            [string]$preUpgradeApplication.ArchivePath
            
        $preUpgradeApplicationSha256 = `
            [string]$preUpgradeApplication.Sha256
            
        if (
            [string]::IsNullOrWhiteSpace(
                $preUpgradeApplicationArchive
            ) `
                -or [string]::IsNullOrWhiteSpace(
                $preUpgradeApplicationSha256
            )
        ) {
            throw (
                "The verified pre-upgrade application archive " +
                "metadata is incomplete."
            )
        }
            
        Add-Content `
            -LiteralPath $logPath `
            -Value (
            "Verified pre-upgrade application: " +
            $preUpgradeApplicationArchive
        ) `
            -Encoding utf8
            
        Add-Content `
            -LiteralPath $logPath `
            -Value (
            "Pre-upgrade application SHA256: " +
            $preUpgradeApplicationSha256
        ) `
            -Encoding utf8
        
        $upgradeRecoveryRecord = New-CareQueueUpgradeRecoveryRecord `
            -RecoveryDirectory $upgradeRecoveryDirectory `
            -PreviousVersion $installedVersion `
            -IncomingVersion $incomingVersion `
            -BackupPath $preUpgradeBackupPath `
            -ApplicationArchive $preUpgradeApplicationArchive `
            -ApplicationSha256 $preUpgradeApplicationSha256 `
            -InstallerLog $logPath
        
        if ([string]::IsNullOrWhiteSpace($upgradeRecoveryRecord)) {
            throw (
                "The Windows upgrade recovery record was not created. " +
                "The CareQFlow application has not been replaced."
            )
        }
        
        Add-Content `
            -LiteralPath $logPath `
            -Value (
            "Upgrade recovery record: " +
            $upgradeRecoveryRecord
        ) `
            -Encoding utf8
    }
    catch {
        $failureMessage = $_.Exception.Message

        @(
            ""
            "Upgrade pre-upgrade backup failed."
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
    "-ReleaseVersion",
    $incomingVersion,
    "-FrontendBuildDirectory",
    $frontendBuildDirectory,
    "-PrivatePythonRuntimeDirectory",
    $privatePythonRuntimeDirectory,
    "-VendorAssetDirectory",
    $vendorAssetDirectory,
    "-BackendWheelDirectory",
    $backendWheelDirectory
)

if (
    $Force `
        -or $Mode -eq "Upgrade" `
        -or $Mode -eq "Repair"
) {
    $installerArguments += "-Force"
}

if ($SkipPermissionHardening) {
    $installerArguments += "-SkipPermissionHardening"
}

$logHeader = @(
    "CareQFlow Windows Installer"
    "Mode: $Mode"
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
            "The CareQFlow production installer failed with exit code " +
            "$productionInstallerExitCode."
        )
    }

    if ($Mode -eq "Install") {
        $installedDeploymentDirectory = Join-Path `
            $InstallDirectory `
            "deployment\windows"

        $installApiServiceScript = Join-Path `
            $installedDeploymentDirectory `
            "install-api-service.ps1"

        $installCaddyServiceScript = Join-Path `
            $installedDeploymentDirectory `
            "install-caddy-service.ps1"

        $serviceDirectory = Join-Path `
            $InstallDirectory `
            "Service"

        Write-Output "Installing the CareQFlow API service..."

        & $installApiServiceScript `
            -InstallDirectory $InstallDirectory `
            -ServiceDirectory $serviceDirectory `
            -StartService

        Write-Output "Installing the CareQFlow Caddy service..."

        & $installCaddyServiceScript `
            -InstallDirectory $InstallDirectory `
            -ServiceDirectory $serviceDirectory `
            -DataDirectory $DataDirectory `
            -StartService
    }
    if (
        $Mode -eq "Upgrade" `
            -or $Mode -eq "Repair"
    ) {
        Write-Output "Ensuring CareQFlow services are running..."

        Start-Service `
            -Name "CareQueueApi" `
            -ErrorAction Stop

        Start-Service `
            -Name "CareQueueCaddy" `
            -ErrorAction Stop
    }
}
catch {
    $failureMessage = $_.Exception.Message

    if ($Mode -eq "Upgrade") {
        try {
            Set-CareQueueUpgradeRecoveryStatus `
                -RecoveryRecord $upgradeRecoveryRecord `
                -Status "failed"
        }
        catch {
            Add-Content `
                -LiteralPath $logPath `
                -Value (
                "Unable to mark the upgrade recovery record failed: " +
                $_.Exception.Message
            ) `
                -Encoding utf8
        }
    }

    @(
        ""
        "$Mode operation failed."
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

try {
    "Running post-installation validation..." |
    Tee-Object `
        -FilePath $logPath `
        -Append

    Assert-PostInstallationHealth `
        -InstallDirectory $InstallDirectory `
        -DataDirectory $DataDirectory `
        -ApplicationOrigin $ApplicationOrigin

    "Post-installation validation completed successfully." |
    Tee-Object `
        -FilePath $logPath `
        -Append

    if ($Mode -eq "Upgrade") {
        Set-CareQueueUpgradeRecoveryStatus `
            -RecoveryRecord $upgradeRecoveryRecord `
            -Status "completed"
    }
}
catch {
    $failureMessage = $_.Exception.Message

    if ($Mode -eq "Upgrade") {
        try {
            Set-CareQueueUpgradeRecoveryStatus `
                -RecoveryRecord $upgradeRecoveryRecord `
                -Status "failed"
        }
        catch {
            Add-Content `
                -LiteralPath $logPath `
                -Value (
                "Unable to mark the upgrade recovery record failed: " +
                $_.Exception.Message
            ) `
                -Encoding utf8
        }
    }

    @(
        ""
        "$Mode post-installation validation failed."
        "Completed UTC: $([DateTime]::UtcNow.ToString('o'))"
        "Message: $failureMessage"
    ) |
    Add-Content `
        -LiteralPath $logPath `
        -Encoding utf8

    Write-InstallerResult `
        -Status "failed" `
        -ExitCode $exitCodePostInstallValidationFailure `
        -Message $failureMessage `
        -LogPath $logPath

    exit $exitCodePostInstallValidationFailure
}

@(
    ""
    "$Mode operation completed successfully."
    "Completed UTC: $([DateTime]::UtcNow.ToString('o'))"
) |
Add-Content `
    -LiteralPath $logPath `
    -Encoding utf8

Write-InstallerResult `
    -Status "succeeded" `
    -ExitCode $exitCodeSuccess `
    -Message "CareQFlow $Mode operation completed successfully." `
    -LogPath $logPath

exit $exitCodeSuccess
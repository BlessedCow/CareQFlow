[CmdletBinding()]
param(
    [string]$TaskName = "CareQueue Encrypted Backup",
    [string]$InstallDirectory = "C:\Program Files\CareQueue",
    [string]$BackupDirectory = "C:\ProgramData\CareQueue\Backups",
    [string]$EnvironmentFile = "C:\ProgramData\CareQueue\Config\carequeue.env",
    [string]$RunAt = "02:00",
    [string]$ServiceAccount = "SYSTEM"
)

$ErrorActionPreference = "Stop"

$runnerScript = Join-Path `
    $InstallDirectory `
    "deployment\windows\run-backup.ps1"

if (-not (Test-Path -LiteralPath $runnerScript -PathType Leaf)) {
    throw "CareQueue backup runner was not found at: $runnerScript"
}

if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) {
    throw "CareQueue environment file was not found at: $EnvironmentFile"
}

if (-not (Test-Path -LiteralPath $BackupDirectory -PathType Container)) {
    New-Item `
        -ItemType Directory `
        -Path $BackupDirectory `
        -Force | Out-Null
}

try {
    $scheduledTime = [DateTime]::ParseExact(
        $RunAt,
        "HH:mm",
        [Globalization.CultureInfo]::InvariantCulture
    )
}
catch {
    throw "RunAt must use 24-hour HH:mm format, such as 02:00."
}

$escapedRunnerScript = $runnerScript.Replace('"', '\"')
$escapedInstallDirectory = $InstallDirectory.Replace('"', '\"')
$escapedBackupDirectory = $BackupDirectory.Replace('"', '\"')
$escapedEnvironmentFile = $EnvironmentFile.Replace('"', '\"')

$argument = @(
    "-NoLogo"
    "-NoProfile"
    "-NonInteractive"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    "`"$escapedRunnerScript`""
    "-InstallDirectory"
    "`"$escapedInstallDirectory`""
    "-BackupDirectory"
    "`"$escapedBackupDirectory`""
    "-EnvironmentFile"
    "`"$escapedEnvironmentFile`""
) -join " "

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $argument `
    -WorkingDirectory $InstallDirectory

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $scheduledTime

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

if ($ServiceAccount -eq "SYSTEM") {
    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest
}
else {
    $principal = New-ScheduledTaskPrincipal `
        -UserId $ServiceAccount `
        -LogonType Password `
        -RunLevel Highest
}

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Creates an encrypted CareQueue database backup."

$existingTask = Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

if ($existingTask) {
    Unregister-ScheduledTask `
        -TaskName $TaskName `
        -Confirm:$false
}

if ($ServiceAccount -eq "SYSTEM") {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -InputObject $task `
        -Force `
        -ErrorAction Stop | Out-Null
}
else {
    $credential = Get-Credential `
        -UserName $ServiceAccount `
        -Message "Enter the password for the CareQueue backup service account."

    Register-ScheduledTask `
        -TaskName $TaskName `
        -InputObject $task `
        -User $credential.UserName `
        -Password $credential.GetNetworkCredential().Password `
        -Force `
        -ErrorAction Stop | Out-Null
}

Write-Host "Scheduled task installed successfully."
Write-Host "Task name: $TaskName"
Write-Host "Daily run time: $RunAt"
Write-Host "Backup directory: $BackupDirectory"
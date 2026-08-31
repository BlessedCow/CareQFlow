[CmdletBinding()]
param(
    [string]$TaskName = "CareQFlow Encrypted Backup"
)

$legacyTaskName = "CareQueue Encrypted Backup"

$taskNames = @(
    $TaskName
)

if ($TaskName -ne $legacyTaskName) {
    $taskNames += $legacyTaskName
}

$removedAnyTask = $false

foreach ($candidateTaskName in $taskNames) {
    $existingTask = Get-ScheduledTask `
        -TaskName $candidateTaskName `
        -ErrorAction SilentlyContinue

    if (-not $existingTask) {
        continue
    }

    Unregister-ScheduledTask `
        -TaskName $candidateTaskName `
        -Confirm:$false `
        -ErrorAction Stop

    Write-Host "Scheduled task removed successfully."
    Write-Host "Task name: $candidateTaskName"

    $removedAnyTask = $true
}

if (-not $removedAnyTask) {
    Write-Host "Scheduled task was not found."
    Write-Host "Task name: $TaskName"
}
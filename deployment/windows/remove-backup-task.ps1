[CmdletBinding()]
param(
    [string]$TaskName = "CareQueue Encrypted Backup"
)

$ErrorActionPreference = "Stop"

$existingTask = Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

if (-not $existingTask) {
    Write-Host "Scheduled task was not found."
    Write-Host "Task name: $TaskName"
    exit 0
}

Unregister-ScheduledTask `
    -TaskName $TaskName `
    -Confirm:$false `
    -ErrorAction Stop

Write-Host "Scheduled task removed successfully."
Write-Host "Task name: $TaskName"
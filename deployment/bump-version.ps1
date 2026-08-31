param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot

$targets = @(
    @{
        Path = "backend\authstatus_api\settings.py"
        Pattern = 'app_version: str = "\d+\.\d+\.\d+"'
        Replacement = "app_version: str = `"$Version`""
    },
    @{
        Path = "deployment\windows\installer\build-payload.ps1"
        Pattern = 'backend_version = "\d+\.\d+\.\d+"'
        Replacement = "backend_version = `"$Version`""
    },
    @{
        Path = "deployment\windows\installer\validate-release-package.ps1"
        Pattern = 'CareQFlow-Setup-\d+\.\d+\.\d+\.exe'
        Replacement = "CareQFlow-Setup-$Version.exe"
    },
    @{
        Path = "deployment\windows\installer\CareQueue.iss"
        Pattern = '#define MyAppVersion "\d+\.\d+\.\d+"'
        Replacement = "#define MyAppVersion `"$Version`""
    },
    @{
        Path = "deployment\linux\installer\build-payload.ps1"
        Pattern = '\[string\]\$Version = "\d+\.\d+\.\d+"'
        Replacement = "[string]`$Version = `"$Version`""
    }
)

foreach ($target in $targets) {
    $path = Join-Path $repoRoot $target.Path

    if (-not (Test-Path -LiteralPath $path)) {
        throw "Version target does not exist: $($target.Path)"
    }

    $content = Get-Content -LiteralPath $path -Raw
    $matches = [regex]::Matches($content, $target.Pattern)

    if ($matches.Count -ne 1) {
        throw (
            "Expected exactly one version match in {0}, found {1}." -f
            $target.Path,
            $matches.Count
        )
    }

    $updated = [regex]::Replace(
        $content,
        $target.Pattern,
        $target.Replacement
    )

    Set-Content -LiteralPath $path -Value $updated -NoNewline

    Write-Host "Updated $($target.Path) -> $Version"
}

Write-Host ""
Write-Host "CareQFlow release version updated to $Version."
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ArchivePath
)

$ErrorActionPreference = "Stop"

$resolvedArchivePath = (
    Resolve-Path -LiteralPath $ArchivePath
).Path

Add-Type -AssemblyName System.IO.Compression.FileSystem

$archive = [System.IO.Compression.ZipFile]::OpenRead(
    $resolvedArchivePath
)

try {
    $forbiddenPatterns = @(
        '(^|/)\.env($|\.)'
        '(^|/)local_backups/'
        '(^|/)local_vobs/'
        '(^|/)backend/data/'
        '(^|/)backend/backups/'
        '(^|/)backend/restores/'
        '(^|/)\.venv/'
        '(^|/)venv/'
        '(^|/)env/'
        '(^|/)__pycache__/'
        '(^|/)\.pytest_cache/'
        '(^|/)\.ruff_cache/'
        '(^|/)node_modules/'
        '(^|/)local_installer_assets/'
        '\.db$'
        '\.sqlite$'
        '\.sqlite3$'
        '\.db\.enc$'
        '\.restored\.db$'
        '\.py[co]$'
    )

    $forbiddenEntries = @(
        foreach ($entry in $archive.Entries) {
            $normalizedName = (
                $entry.FullName -replace '\\', '/'
            )

            $isEnvironmentTemplate = (
                $normalizedName -match
                    '(^|/)\.env\.(example|sample|template)($|\.)'
            )

            if ($isEnvironmentTemplate) {
                continue
            }

            foreach ($pattern in $forbiddenPatterns) {
                if ($normalizedName -match $pattern) {
                    $normalizedName
                    break
                }
            }
        }
    )

    if ($forbiddenEntries.Count -gt 0) {
        $preview = (
            $forbiddenEntries |
            Sort-Object -Unique |
            Select-Object -First 25
        ) -join [Environment]::NewLine

        throw (
            "Archive contains forbidden local, runtime, or sensitive files:" +
            [Environment]::NewLine +
            $preview
        )
    }
}
finally {
    $archive.Dispose()
}

Write-Host (
    "Archive validation passed: no forbidden local, runtime, " +
    "or sensitive files were found."
)
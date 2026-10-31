# Stops the server started by the portable ELP Studio launcher.
$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$stateFile = Join-Path $root ".elp_studio_runtime\server.json"
if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host "No launcher-managed ELP Studio server is recorded."
    exit 0
}
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
$process = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
if ($null -ne $process -and $process.ProcessName -match "^python(w)?$") {
    Stop-Process -Id ([int]$state.pid) -Force
    Write-Host "Stopped ELP Studio (PID $($state.pid))."
} else {
    Write-Host "ELP Studio is not running, or the saved PID is no longer a Python process."
}
Remove-Item -LiteralPath $stateFile -Force

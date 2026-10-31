# Portable installer for the Windows desktop launcher (PowerShell 5.1+).
# Run from an activated ELP Studio Conda environment whenever possible.
param(
    [string]$PythonPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$scriptPath = Join-Path $PSScriptRoot "start_elp_studio.vbs"
$iconPath = Join-Path $root "assets\elp_studio.ico"
$settingsPath = Join-Path $root ".elp_studio_launcher.json"

if (-not (Test-Path -LiteralPath (Join-Path $root "app.py"))) {
    throw "Could not find ELP Studio app.py next to the installer."
}
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing launcher: $scriptPath"
}
if (-not (Test-Path -LiteralPath $iconPath)) {
    Write-Host "Generating local ELP Studio icon..."
    & (Join-Path $PSScriptRoot "create_icon.ps1") -OutputPath $iconPath
}
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Unable to create the desktop icon: $iconPath"
}

function Test-StudioPython {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try {
        # Check the actual interpreter, not merely the presence of python.exe.
        & $Path -c "import streamlit; import calvados_library_builder" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch { return $false }
}

$candidates = New-Object 'System.Collections.Generic.List[string]'
function Add-PythonCandidate {
    param([string]$Path)
    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        if (-not $candidates.Contains($Path)) { $candidates.Add($Path) }
    }
}

# Priority: explicit selection; currently activated Conda/venv; checkout-local venv.
if ($PythonPath) { Add-PythonCandidate $PythonPath }
if ($env:CONDA_PREFIX) { Add-PythonCandidate (Join-Path $env:CONDA_PREFIX "python.exe") }
if ($env:VIRTUAL_ENV) { Add-PythonCandidate (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe") }
Add-PythonCandidate (Join-Path $root ".venv\Scripts\python.exe")
Add-PythonCandidate (Join-Path $root ".conda\python.exe")
Add-PythonCandidate (Join-Path $root "venv\Scripts\python.exe")

# Existing launcher settings are useful when reinstalling the shortcut.
if (Test-Path -LiteralPath $settingsPath) {
    try {
        $old = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
        if ($old.python) { Add-PythonCandidate ([string]$old.python) }
    }
    catch { Write-Warning "Could not read old launcher settings. Rediscovering Python." }
}

# Look at registered Conda environments, independent of install directory.
# No hard-coded drive letters or Conda base locations are necessary.
try {
    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if ($null -ne $conda) {
        $envsJson = (& conda env list --json 2>$null | Out-String) | ConvertFrom-Json
        $allEnvs = @($envsJson.envs)
        foreach ($envDir in $allEnvs) {
            if ($envDir -match '(?i)calvados|elp|idp') {
                Add-PythonCandidate (Join-Path $envDir "python.exe")
            }
        }
        foreach ($envDir in $allEnvs) {
            Add-PythonCandidate (Join-Path $envDir "python.exe")
        }
    }
}
catch {
    Write-Host "Conda environment discovery unavailable; checking other Python paths."
}

$python = $null
foreach ($candidate in $candidates) {
    if (Test-StudioPython $candidate) {
        $python = (Resolve-Path -LiteralPath $candidate).Path
        break
    }
}

if (-not $python) {
    Write-Host ""
    Write-Warning "Could not automatically locate a Python environment with Streamlit and ELP Studio installed."
    Write-Host "Activate the correct Conda environment and rerun install_elp_studio.cmd,"
    Write-Host "or paste the full path of that environment's python.exe below."
    $manual = Read-Host "Full path to python.exe (Enter to cancel)"
    $manual = $manual.Trim('"')
    if (-not (Test-StudioPython $manual)) {
        throw "No compatible Python selected; no shortcut has been created."
    }
    $python = (Resolve-Path -LiteralPath $manual).Path
}

# Store only machine-specific data in a gitignored local file.
@{ python = $python; schema_version = 1 } |
    ConvertTo-Json |
    Set-Content -LiteralPath $settingsPath -Encoding UTF8

$desktop = [Environment]::GetFolderPath("DesktopDirectory")
if ([string]::IsNullOrWhiteSpace($desktop) -or -not (Test-Path -LiteralPath $desktop)) {
    throw "Windows Desktop folder could not be located."
}
$lnk = Join-Path $desktop "ELP Studio.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnk)
$shortcut.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
$shortcut.Arguments = '"' + $scriptPath + '"'
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Start the local CALVADOS ELP Studio"
$shortcut.IconLocation = $iconPath + ",0"
$shortcut.Save()

Write-Host ""
Write-Host "ELP Studio desktop shortcut created successfully."
Write-Host "Shortcut: $lnk"
Write-Host "Project:  $root"
Write-Host "Python:   $python"
Write-Host ""
Write-Host "Double-click ELP Studio on your Desktop to launch it."
Write-Host "If you move the repository or Conda environment, rerun the installer."

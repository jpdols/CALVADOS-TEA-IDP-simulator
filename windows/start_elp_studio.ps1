# Portable launcher. Logs are under .elp_studio_runtime (gitignored).
$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$settings = Join-Path $root ".elp_studio_launcher.json"
$rundir = Join-Path $root ".elp_studio_runtime"
New-Item -ItemType Directory -Path $rundir -Force | Out-Null
$launcherLog = Join-Path $rundir "launcher.log"
$stdoutLog = Join-Path $rundir "streamlit_stdout.log"
$stderrLog = Join-Path $rundir "streamlit_stderr.log"
$stateFile = Join-Path $rundir "server.json"

function Log([string]$message) {
    ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message) |
        Out-File -LiteralPath $launcherLog -Append -Encoding UTF8
}
function Server-Ready([int]$port) {
    try {
        $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:$port/_stcore/health")
        $request.Timeout = 1500
        $response = $request.GetResponse()
        $status = [int]$response.StatusCode
        $response.Close()
        return ($status -eq 200)
    } catch { return $false }
}
function Port-Free([int]$port) {
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
        $listener.Start()
        return $true
    } catch { return $false }
    finally { if ($null -ne $listener) { $listener.Stop() } }
}
try {
    if (-not (Test-Path -LiteralPath $settings)) {
        throw "ELP Studio is not configured. Run windows\install_elp_studio.cmd first."
    }
    $config = Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
    $python = [string]$config.python
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Configured Python no longer exists: $python. Run the installer again."
    }
    if (Test-Path -LiteralPath $stateFile) {
        try {
            $old = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
            $oldpid = [int]$old.pid
            $oldport = [int]$old.port
            $existing = Get-Process -Id $oldpid -ErrorAction SilentlyContinue
            if ($null -ne $existing -and (Server-Ready $oldport)) {
                Log "Existing ELP Studio process $oldpid on port $oldport; opening browser."
                Start-Process "http://127.0.0.1:$oldport" | Out-Null
                exit 0
            }
        } catch { Log "Ignoring obsolete runtime state: $_" }
    }
    $port = $null
    foreach ($candidate in 8501..8550) {
        if (Port-Free $candidate) { $port = $candidate; break }
    }
    if ($null -eq $port) { throw "No available local port in range 8501..8550." }

    $arguments = @(
        "-m", "streamlit", "run", "app.py",
        "--server.address", "127.0.0.1",
        "--server.port", "$port",
        "--server.headless", "true",
        "--server.fileWatcherType", "none"
    )
    Log "Starting $python with $($arguments -join ' ') in $root."
    $child = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    @{ pid = $child.Id; port = $port; python = $python; project = $root } |
        ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

    $ready = $false
    foreach ($attempt in 1..90) {
        if (Server-Ready $port) { $ready = $true; break }
        $child.Refresh()
        if ($child.HasExited) {
            throw "Streamlit exited with code $($child.ExitCode). See $stderrLog"
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "Streamlit did not become ready on port $port. Inspect $stderrLog" }
    Log "ELP Studio ready at http://127.0.0.1:$port (PID $($child.Id))."
    Start-Process "http://127.0.0.1:$port" | Out-Null
} catch {
    Log ("ERROR: " + ($_ | Out-String))
    try {
        $shell = New-Object -ComObject WScript.Shell
        $msg = "ELP Studio could not start." + [Environment]::NewLine + $_.Exception.Message + [Environment]::NewLine + "See: " + $launcherLog
        $shell.Popup($msg, 0, "ELP Studio", 16) | Out-Null
    } catch {}
    exit 1
}

# ==============================================================================
# J.A.R.V.I.S. Autonomous System Launcher & Process Supervisor
# Works without manual terminals, separate commands, or uv trampoline failures.
# ==============================================================================
param (
    [switch]$Background,
    [switch]$NoBrowser,
    [switch]$ForceRestart
)

$ErrorActionPreference = "SilentlyContinue"

# 1. Resolve Project Paths
$Root = $PSScriptRoot
if (Test-Path (Join-Path $Root "jarvis\backend")) {
    $JarvisDir   = Join-Path $Root "jarvis"
    $BackendDir  = Join-Path $JarvisDir "backend"
    $FrontendDir = Join-Path $JarvisDir "frontend"
} elseif (Test-Path (Join-Path $Root "backend")) {
    $JarvisDir   = $Root
    $BackendDir  = Join-Path $JarvisDir "backend"
    $FrontendDir = Join-Path $JarvisDir "frontend"
} else {
    Write-Error "[JARVIS Error] Could not locate jarvis directories."
    exit 1
}

# 2. Locate Direct Python Interpreter (NEVER use 'uv run' to avoid trampoline bugs)
$PythonExe = $null
$PyCandidates = @(
    "python3.10",
    (Join-Path $BackendDir ".venv\Scripts\python.exe"),
    (Join-Path (Split-Path $Root) ".venv\Scripts\python.exe"),
    "python.exe"
)
foreach ($cand in $PyCandidates) {
    $resolved = if (Test-Path $cand) { $cand } else { (Get-Command $cand -ErrorAction SilentlyContinue).Source }
    if ($resolved -and (Test-Path $resolved)) {
        & $resolved -c "import cadquery" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PythonExe = $resolved
            break
        } elseif (-not $PythonExe) {
            $PythonExe = $resolved
        }
    }
}

if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    Write-Host "[JARVIS] FATAL: Python executable not found." -ForegroundColor Red
    exit 1
}

if (-not $Background) {
    Write-Host ""
    Write-Host " ========================================================" -ForegroundColor Cyan
    Write-Host "         J.A.R.V.I.S. AUTOMATED SYSTEM LAUNCHER          " -ForegroundColor Cyan
    Write-Host " ========================================================" -ForegroundColor Cyan
    Write-Host " [*] Workspace:  $JarvisDir" -ForegroundColor Gray
    Write-Host " [*] Python:     $PythonExe" -ForegroundColor Gray
    Write-Host ""
}

function Stop-PortProcess([int]$port) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -gt 0) {
            try {
                Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            } catch {}
        }
    }
}

function Test-PortOpen([int]$port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(1000, $false)
        if (-not $wait) {
            $tcp.Close()
            return $false
        }
        $tcp.EndConnect($connect)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Test-BackendHealth {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        return ($resp.status -eq "ok")
    } catch {
        return $false
    }
}

function Test-FrontendHealth {
    return (Test-PortOpen 5173)
}

function Start-DetachedProcess([string]$commandLine, [string]$workingDirectory) {
    try {
        $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
            CommandLine      = $commandLine
            CurrentDirectory = $workingDirectory
        }
        return ($res.ReturnValue -eq 0)
    } catch {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c $commandLine" -WorkingDirectory $workingDirectory -WindowStyle Hidden
        return $true
    }
}

if ($ForceRestart) {
    if (-not $Background) { Write-Host " [!] Force restart requested. Terminating current instances..." -ForegroundColor Yellow }
    Stop-PortProcess 8000
    Stop-PortProcess 5173
    Start-Sleep -Milliseconds 800
}

# 3. Check & Launch Backend (FastAPI on Port 8000)
$BackendHealthy = Test-BackendHealth
if ($BackendHealthy) {
    if (-not $Background) { Write-Host " [OK] Backend already running and healthy (Port 8000)" -ForegroundColor Green }
} else {
    $zombie = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($zombie) {
        if (-not $Background) { Write-Host " [!] Port 8000 occupied by stale process. Recycling..." -ForegroundColor Yellow }
        Stop-PortProcess 8000
        Start-Sleep -Milliseconds 500
    }

    if (-not $Background) { Write-Host " [+] Starting Autonomous AI Backend (Uvicorn)..." -ForegroundColor Cyan }
    $backendCmd = "`"$PythonExe`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir `"$BackendDir`""
    Start-DetachedProcess $backendCmd $BackendDir | Out-Null
}

# 4. Check & Launch Frontend (Vite on Port 5173)
$FrontendHealthy = Test-FrontendHealth
if ($FrontendHealthy) {
    if (-not $Background) { Write-Host " [OK] Frontend already running and healthy (Port 5173)" -ForegroundColor Green }
} else {
    $zombieFe = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    if ($zombieFe) {
        if (-not $Background) { Write-Host " [!] Port 5173 occupied by stale process. Recycling..." -ForegroundColor Yellow }
        Stop-PortProcess 5173
        Start-Sleep -Milliseconds 500
    }

    if (-not $Background) { Write-Host " [+] Starting Holographic HUD (Vite)..." -ForegroundColor Cyan }
    $frontendCmd = "cmd.exe /c npm run dev -- --host 127.0.0.1 --port 5173"
    Start-DetachedProcess $frontendCmd $FrontendDir | Out-Null
}

# 5. Polling Verification Loop (Wait until both are responding)
if (-not $Background) {
    Write-Host " [*] Performing neural handshake..." -ForegroundColor Gray
}

$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    if (Test-BackendHealth) {
        $backendReady = $true
        break
    }
    Start-Sleep -Milliseconds 500
}

$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    if (Test-FrontendHealth) {
        $frontendReady = $true
        break
    }
    Start-Sleep -Milliseconds 500
}

if ($backendReady) {
    if (-not $Background) { Write-Host " [OK] Backend online at http://127.0.0.1:8000" -ForegroundColor Green }
} else {
    if (-not $Background) { Write-Host " [!] Backend startup taking longer than usual, proceeding..." -ForegroundColor Yellow }
}

if ($frontendReady) {
    if (-not $Background) { Write-Host " [OK] Frontend online at http://localhost:5173" -ForegroundColor Green }
} else {
    if (-not $Background) { Write-Host " [!] Frontend startup taking longer than usual, proceeding..." -ForegroundColor Yellow }
}

# 6. Launch HUD in Browser
if (-not $NoBrowser) {
    if (-not $Background) { Write-Host " [->] Launching Stark HUD in default browser..." -ForegroundColor Cyan }
    Start-Process "http://localhost:5173"
}

if (-not $Background) {
    Write-Host ""
    Write-Host " ========================================================" -ForegroundColor Cyan
    Write-Host "   JARVIS is fully active and running in the background. " -ForegroundColor Green
    Write-Host "   All systems nominal. Closing launcher window in 2s... " -ForegroundColor Gray
    Write-Host " ========================================================" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
}

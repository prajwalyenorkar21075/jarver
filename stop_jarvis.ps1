# ==============================================================================
# J.A.R.V.I.S. Clean Shutdown Script
# Terminates background Uvicorn and Vite processes cleanly.
# ==============================================================================
param (
    [switch]$Quiet
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $Quiet) {
    Write-Host ""
    Write-Host " [JARVIS] Initiating clean shutdown..." -ForegroundColor Yellow
}

function Stop-PortProcess([int]$port, [string]$label) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    $count = 0
    foreach ($c in $conns) {
        if ($c.OwningProcess -gt 0) {
            try {
                Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
                $count++
            } catch {}
        }
    }
    if (-not $Quiet) {
        if ($count -gt 0) {
            Write-Host " [OK] Terminated $label (Port $port, $count process)" -ForegroundColor Green
        } else {
            Write-Host " [i] No active process found on Port $port ($label)" -ForegroundColor Gray
        }
    }
}

Stop-PortProcess 8000 "AI Backend (Uvicorn)"
Stop-PortProcess 5173 "Holographic HUD (Vite)"

if (-not $Quiet) {
    Write-Host " [OK] JARVIS services terminated cleanly." -ForegroundColor Cyan
    Write-Host ""
    Start-Sleep -Seconds 1
}

# NexRemote Development Script
# Starts both the Windows Python app and the Flutter mobile app simultaneously.
# Usage: .\scripts\dev.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$windowsApp = Join-Path $root "windows_app\src"
$flutterApp = Join-Path $root "nexremote"

Write-Host "`n=== NexRemote Development Environment ===" -ForegroundColor Cyan
Write-Host "Root:        $root" -ForegroundColor DarkGray
Write-Host "Windows App: $windowsApp" -ForegroundColor DarkGray
Write-Host "Flutter App: $flutterApp" -ForegroundColor DarkGray
Write-Host ""

# ── Check prerequisites ──
if (-not (Test-Path (Join-Path $windowsApp ".venv"))) {
    Write-Host "[!] Python venv not found. Running 'uv sync'..." -ForegroundColor Yellow
    Push-Location $windowsApp
    uv sync
    Pop-Location
}

$flutterExe = Get-Command flutter -ErrorAction SilentlyContinue
if (-not $flutterExe) {
    Write-Host "[ERROR] Flutter not found in PATH. Please install Flutter first." -ForegroundColor Red
    exit 1
}

# ── Start Windows Python app ──
Write-Host "[1/2] Starting Windows app (Python)..." -ForegroundColor Green
$pythonJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    & ".venv\Scripts\python.exe" main.py
} -ArgumentList $windowsApp

# ── Start Flutter app ──
Write-Host "[2/2] Starting Flutter app..." -ForegroundColor Green
$flutterJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    flutter run
} -ArgumentList $flutterApp

Write-Host "`n=== Both apps started ===" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both apps.`n" -ForegroundColor DarkGray

# ── Wait and stream output ──
try {
    while ($true) {
        # Stream output from both jobs
        Receive-Job $pythonJob -ErrorAction SilentlyContinue | Write-Host
        Receive-Job $flutterJob -ErrorAction SilentlyContinue | Write-Host

        # Check if any job failed
        if ($pythonJob.State -eq "Failed") {
            Write-Host "[ERROR] Python app crashed:" -ForegroundColor Red
            Receive-Job $pythonJob
            break
        }
        if ($flutterJob.State -eq "Failed") {
            Write-Host "[ERROR] Flutter app crashed:" -ForegroundColor Red
            Receive-Job $flutterJob
            break
        }

        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host "`n=== Shutting down ===" -ForegroundColor Yellow
    Stop-Job $pythonJob -ErrorAction SilentlyContinue
    Stop-Job $flutterJob -ErrorAction SilentlyContinue
    Remove-Job $pythonJob -Force -ErrorAction SilentlyContinue
    Remove-Job $flutterJob -Force -ErrorAction SilentlyContinue
    Write-Host "Done." -ForegroundColor Green
}

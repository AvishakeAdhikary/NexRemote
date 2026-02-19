# NexRemote Production Build Script
# Builds Windows .exe (via PyInstaller) and Android .apk (via Flutter).
# Usage: .\scripts\build.ps1 [-SkipWindows] [-SkipAndroid]
#
# Prerequisites:
#   - Python venv with PyInstaller: cd windows_app\src && uv sync
#   - Flutter SDK in PATH
#   - Android SDK configured for Flutter

param(
    [switch]$SkipWindows,
    [switch]$SkipAndroid
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$windowsApp = Join-Path $root "windows_app\src"
$flutterApp = Join-Path $root "nexremote"
$distDir = Join-Path $root "dist"

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     NexRemote Production Build         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Ensure dist directory
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

$buildTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$success = @()
$failed = @()

# ── Windows Build ──
if (-not $SkipWindows) {
    Write-Host "━━━ [1] Building Windows Executable ━━━" -ForegroundColor Yellow
    
    if (-not (Test-Path (Join-Path $windowsApp ".venv"))) {
        Write-Host "  → Setting up Python venv..." -ForegroundColor DarkGray
        Push-Location $windowsApp
        uv sync
        Pop-Location
    }
    
    $specFile = Join-Path $root "windows_app\nexremote.spec"
    
    if (Test-Path $specFile) {
        Write-Host "  → Running PyInstaller with spec file..." -ForegroundColor DarkGray
        Push-Location $windowsApp
        & ".venv\Scripts\python.exe" -m PyInstaller $specFile --distpath (Join-Path $distDir "windows") --workpath (Join-Path $root "build\pyinstaller") --noconfirm
        Pop-Location
    } else {
        Write-Host "  → Running PyInstaller (auto-config)..." -ForegroundColor DarkGray
        Push-Location $windowsApp
        $icoPath = Join-Path $windowsApp "src\assets\images\logo.ico"
        & ".venv\Scripts\python.exe" -m PyInstaller `
            --name "NexRemote" `
            --icon $icoPath `
            --windowed `
            --onefile `
            --add-data "src\assets;assets" `
            --distpath (Join-Path $distDir "windows") `
            --workpath (Join-Path $root "build\pyinstaller") `
            --noconfirm `
            "src\main.py"
        Pop-Location
    }
    
    if ($LASTEXITCODE -eq 0) {
        $exePath = Join-Path $distDir "windows\NexRemote.exe"
        if (Test-Path $exePath) {
            $size = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
            Write-Host "  ✓ Windows build complete: $exePath ($($size) MB)" -ForegroundColor Green
            $success += "Windows EXE"
        } else {
            Write-Host "  ✗ Windows build output not found" -ForegroundColor Red
            $failed += "Windows EXE"
        }
    } else {
        Write-Host "  ✗ Windows build failed (exit code $LASTEXITCODE)" -ForegroundColor Red
        $failed += "Windows EXE"
    }
    Write-Host ""
}

# ── Android Build ──
if (-not $SkipAndroid) {
    Write-Host "━━━ [2] Building Android APK ━━━" -ForegroundColor Yellow
    
    $flutterExe = Get-Command flutter -ErrorAction SilentlyContinue
    if (-not $flutterExe) {
        Write-Host "  ✗ Flutter not found in PATH" -ForegroundColor Red
        $failed += "Android APK"
    } else {
        Push-Location $flutterApp
        
        Write-Host "  → Getting dependencies..." -ForegroundColor DarkGray
        flutter pub get | Out-Null
        
        Write-Host "  → Building release APK..." -ForegroundColor DarkGray
        flutter build apk --release
        
        if ($LASTEXITCODE -eq 0) {
            $apkSource = Join-Path $flutterApp "build\app\outputs\flutter-apk\app-release.apk"
            if (Test-Path $apkSource) {
                $apkDest = Join-Path $distDir "android\NexRemote.apk"
                New-Item -ItemType Directory -Path (Join-Path $distDir "android") -Force | Out-Null
                Copy-Item $apkSource $apkDest -Force
                $size = [math]::Round((Get-Item $apkDest).Length / 1MB, 1)
                Write-Host "  ✓ Android build complete: $apkDest ($($size) MB)" -ForegroundColor Green
                $success += "Android APK"
            } else {
                Write-Host "  ✗ APK output not found at $apkSource" -ForegroundColor Red
                $failed += "Android APK"
            }
        } else {
            Write-Host "  ✗ Android build failed (exit code $LASTEXITCODE)" -ForegroundColor Red
            $failed += "Android APK"
        }
        
        Pop-Location
    }
    Write-Host ""
}

# ── Summary ──
Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║            Build Summary               ║" -ForegroundColor Cyan
Write-Host "╠════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Time: $buildTime       ║" -ForegroundColor DarkGray

if ($success.Count -gt 0) {
    Write-Host "║  ✓ Success: $($success -join ', ')" -ForegroundColor Green
}
if ($failed.Count -gt 0) {
    Write-Host "║  ✗ Failed:  $($failed -join ', ')" -ForegroundColor Red
}
Write-Host "║  Output: $distDir" -ForegroundColor DarkGray
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

if ($failed.Count -gt 0) {
    exit 1
}

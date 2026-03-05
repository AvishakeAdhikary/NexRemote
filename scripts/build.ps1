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

# ── UTF-8 ──
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$windowsApp = Join-Path $root "windows_app\src"
$windowsAppRoot = Join-Path $root "windows_app"
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
    
    $specFile = Join-Path $windowsAppRoot "nexremote.spec"
    
    if (Test-Path $specFile) {
        Write-Host "  → Running PyInstaller with spec file..." -ForegroundColor DarkGray
        # IMPORTANT: Run from windows_app/ (not windows_app/src/) because
        # the spec file uses paths like 'src/main.py' relative to windows_app/.
        Push-Location $windowsAppRoot
        & "$windowsApp\.venv\Scripts\python.exe" -m PyInstaller $specFile `
            --distpath (Join-Path $distDir "windows") `
            --workpath (Join-Path $root "build\pyinstaller") `
            --noconfirm
        Pop-Location
    } else {
        Write-Host "  → Running PyInstaller (auto-config)..." -ForegroundColor DarkGray
        Push-Location $windowsAppRoot
        $icoPath = Join-Path $windowsApp "assets\images\logo.ico"
        & "$windowsApp\.venv\Scripts\python.exe" -m PyInstaller `
            --name "NexRemote" `
            --icon $icoPath `
            --console `
            --onefile `
            --add-data "src\assets;assets" `
            --add-data "src\utils\elevated_ops.py;utils" `
            --hidden-import "core.server" `
            --hidden-import "core.server_thread" `
            --hidden-import "core.discovery" `
            --hidden-import "core.connection_manager" `
            --hidden-import "core.certificate_manager" `
            --hidden-import "core.usb_detector" `
            --hidden-import "core.nat_traversal" `
            --hidden-import "ui.main_window" `
            --hidden-import "ui.settings_dialog" `
            --hidden-import "ui.connection_dialog" `
            --hidden-import "ui.terms_dialog" `
            --hidden-import "ui.tray_icon" `
            --hidden-import "ui.file_explorer" `
            --hidden-import "ui.task_manager" `
            --hidden-import "security.encryption" `
            --hidden-import "security.authentication" `
            --hidden-import "security.audit_logger" `
            --hidden-import "security.firewall_config" `
            --hidden-import "input.virtual_keyboard" `
            --hidden-import "input.virtual_mouse" `
            --hidden-import "input.virtual_gamepad" `
            --hidden-import "input.media_controller" `
            --hidden-import "input.input_validator" `
            --hidden-import "streaming.screen_capture" `
            --hidden-import "streaming.camera_streamer" `
            --hidden-import "streaming.audio_capture" `
            --hidden-import "streaming.virtual_camera" `
            --hidden-import "utils.paths" `
            --hidden-import "utils.config" `
            --hidden-import "utils.logger" `
            --hidden-import "utils.elevate" `
            --hidden-import "utils.elevated_ops" `
            --hidden-import "utils.protocol" `
            --hidden-import "PyQt6.sip" `
            --hidden-import "PyQt6.QtCore" `
            --hidden-import "PyQt6.QtGui" `
            --hidden-import "PyQt6.QtWidgets" `
            --hidden-import "websockets" `
            --hidden-import "websockets.legacy" `
            --hidden-import "websockets.legacy.server" `
            --hidden-import "mss" `
            --hidden-import "mss.windows" `
            --hidden-import "cv2" `
            --hidden-import "numpy" `
            --hidden-import "loguru" `
            --hidden-import "qrcode" `
            --hidden-import "PIL" `
            --hidden-import "PIL.Image" `
            --hidden-import "cryptography" `
            --hidden-import "psutil" `
            --hidden-import "pynput" `
            --hidden-import "pynput.keyboard._win32" `
            --hidden-import "pynput.mouse._win32" `
            --hidden-import "vgamepad" `
            --hidden-import "pycaw" `
            --hidden-import "pycaw.pycaw" `
            --hidden-import "comtypes" `
            --hidden-import "comtypes.client" `
            --hidden-import "pyperclip" `
            --exclude-module "evdev" `
            --exclude-module "Xlib" `
            --exclude-module "AppKit" `
            --exclude-module "Quartz" `
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

# NexRemote development script
# Starts the Windows host and, when available, installs/launches the Android debug build.

param(
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Debug',

    [switch]$WindowsOnly,
    [switch]$AndroidOnly,
    [switch]$SkipAndroidInstall,
    [switch]$SkipAndroidLaunch
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$windowsProject = Join-Path (Join-Path (Join-Path (Join-Path $root 'windows_app') 'NexRemote') 'NexRemote') 'NexRemote.csproj'
$androidProject = Join-Path (Join-Path $root 'client') 'NexRemote'

function Write-Section {
    param([string]$Text)
    Write-Host "`n==> $Text" -ForegroundColor Cyan
}

function Invoke-CommandChecked {
    param(
        [scriptblock]$ScriptBlock,
        [string]$Message
    )

    & $ScriptBlock
    if ($LASTEXITCODE -ne 0) {
        throw "$Message failed with exit code $LASTEXITCODE"
    }
}

function Resolve-AdbCommand {
    $adb = Get-Command adb -ErrorAction SilentlyContinue
    if ($adb) {
        return $adb.Source
    }

    $roots = @()
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_SDK_ROOT)) { $roots += $env:ANDROID_SDK_ROOT }
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_HOME)) { $roots += $env:ANDROID_HOME }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { $roots += (Join-Path (Join-Path $env:LOCALAPPDATA 'Android') 'Sdk') }
    $roots += 'C:\Android\Sdk'

    foreach ($rootPath in $roots) {
        $candidate = Join-Path $rootPath 'platform-tools\adb.exe'
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function Get-ConnectedAdbDevice {
    param([string]$AdbPath)

    $lines = & $AdbPath devices | Select-Object -Skip 1
    $devices = foreach ($line in $lines) {
        if ($line -match '^(?<serial>\S+)\s+device(?:\s|$)') {
            [pscustomobject]@{
                Serial = $Matches.serial
                Line   = $line.Trim()
            }
        }
    }

    return $devices | Select-Object -First 1
}

function Start-WindowsHost {
    Write-Section 'Windows host'
    Invoke-CommandChecked -Message 'dotnet build (Windows dev)' -ScriptBlock {
        & dotnet build $windowsProject --configuration $Configuration
    }

    $process = Start-Process -FilePath 'dotnet' -ArgumentList @(
        'run',
        '--project', $windowsProject,
        '--configuration', $Configuration,
        '--no-build'
    ) -WorkingDirectory (Split-Path -Parent $windowsProject) -PassThru

    Start-Sleep -Seconds 2
    if ($process.HasExited) {
        throw 'The Windows host exited immediately after launch. Check the console output from dotnet run.'
    }

    Write-Host "Windows host started. PID: $($process.Id)" -ForegroundColor Green
}

function Start-AndroidDebug {
    Write-Section 'Android debug'

    $java = Get-Command java -ErrorAction SilentlyContinue
    if (-not $java -and [string]::IsNullOrWhiteSpace($env:JAVA_HOME)) {
        Write-Warning 'Java was not found. Android debug build/install is being skipped.'
        return
    }

    $gradleWrapper = if ($IsWindows) { Join-Path $androidProject 'gradlew.bat' } else { Join-Path $androidProject 'gradlew' }
    if (-not (Test-Path $gradleWrapper)) {
        throw "Gradle wrapper not found: $gradleWrapper"
    }

    Invoke-CommandChecked -Message 'Gradle assembleDebug' -ScriptBlock {
        Push-Location $androidProject
        try {
            & $gradleWrapper assembleDebug
        }
        finally {
            Pop-Location
        }
    }

    $debugApk = Join-Path (Join-Path (Join-Path (Join-Path $androidProject 'app') 'build') 'outputs') 'apk'
    $debugApk = Join-Path (Join-Path $debugApk 'debug') 'app-debug.apk'
    if (-not (Test-Path $debugApk)) {
        Write-Warning "Debug APK not found at $debugApk"
        return
    }

    $adb = Resolve-AdbCommand
    if (-not $adb) {
        Write-Host "ADB was not found. Debug APK is ready at $debugApk" -ForegroundColor Yellow
        return
    }

    $device = Get-ConnectedAdbDevice -AdbPath $adb
    if (-not $device) {
        Write-Host "No connected Android device or emulator was found. Debug APK is ready at $debugApk" -ForegroundColor Yellow
        return
    }

    if (-not $SkipAndroidInstall) {
        Write-Host "Installing debug APK on $($device.Serial)..." -ForegroundColor DarkGray
        Invoke-CommandChecked -Message 'adb install (Android debug)' -ScriptBlock {
            & $adb @('-s', $device.Serial, 'install', '-r', $debugApk)
        }
    }

    if (-not $SkipAndroidLaunch) {
        $packageName = 'com.neuralnexusstudios.nexremote.debug'
        Write-Host "Launching $packageName on $($device.Serial)..." -ForegroundColor DarkGray
        Invoke-CommandChecked -Message 'adb launch (Android debug)' -ScriptBlock {
            & $adb @('-s', $device.Serial, 'shell', 'monkey', '-p', $packageName, '-c', 'android.intent.category.LAUNCHER', '1')
        }
    }

    Write-Host "Android debug build complete. APK: $debugApk" -ForegroundColor Green
}

Write-Host "`nNexRemote development environment" -ForegroundColor Cyan
Write-Host "Root: $root" -ForegroundColor DarkGray
Write-Host "Windows project: $windowsProject" -ForegroundColor DarkGray
Write-Host "Android project: $androidProject" -ForegroundColor DarkGray

if (-not $AndroidOnly) {
    Start-WindowsHost
}

if (-not $WindowsOnly) {
    Start-AndroidDebug
}

# NexRemote production build script
# Builds the Windows host (Electron + Python sidecar, MSIX) and the Android client into dist/.

param(
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Release',

    [switch]$SkipWindows,
    [switch]$SkipAndroid,
    [switch]$NoTests,
    [switch]$AndroidBundle,

    # Fail instead of producing an unsigned APK. Android refuses to install unsigned APKs,
    # so every build that gets published (CI on master and tags) must pass this.
    [switch]$RequireSigning
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
if ($IsWindows) {
    chcp 65001 | Out-Null
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$serverProject = Join-Path (Join-Path $root 'windows_app') 'server'
$desktopProject = Join-Path (Join-Path $root 'windows_app') 'desktop'
$androidProject = Join-Path (Join-Path $root 'client') 'NexRemote'
$distRoot = Join-Path $root 'dist'
$windowsDistRoot = Join-Path $distRoot 'windows'
$androidDistRoot = Join-Path $distRoot 'android'

function Write-Section {
    param([string]$Text)
    Write-Host "`n==> $Text" -ForegroundColor Cyan
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

function Invoke-CommandChecked {
    param(
        [scriptblock]$ScriptBlock,
        [string]$Message
    )

    $global:LASTEXITCODE = 0

    try {
        & $ScriptBlock
    }
    catch {
        throw "$Message failed: $_"
    }

    if ($LASTEXITCODE -ne 0) {
        throw "$Message failed with exit code $LASTEXITCODE"
    }
}

function Copy-ArtifactIfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        return $false
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item $Source $Destination -Force
    return $true
}

function Resolve-AndroidApkSigner {
    $roots = @()
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_SDK_ROOT)) { $roots += $env:ANDROID_SDK_ROOT }
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_HOME)) { $roots += $env:ANDROID_HOME }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { $roots += (Join-Path (Join-Path $env:LOCALAPPDATA 'Android') 'Sdk') }

    # Look for the launcher by exact name: a wildcard also matches lib/apksigner.jar, which can't be run.
    $launcher = if ($IsWindows) { 'apksigner.bat' } else { 'apksigner' }
    foreach ($rootPath in $roots) {
        $candidate = Get-ChildItem (Join-Path $rootPath 'build-tools') -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName $launcher } |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
        if ($candidate) {
            return $candidate
        }
    }

    return $null
}

function Sign-AndroidPublish {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ReleaseApk,

        [string]$ReleaseBundle
    )

    if ([string]::IsNullOrWhiteSpace($env:ANDROID_KEYSTORE_BASE64) -or
        [string]::IsNullOrWhiteSpace($env:ANDROID_KEYSTORE_PASSWORD) -or
        [string]::IsNullOrWhiteSpace($env:ANDROID_KEY_ALIAS)) {
        if ($RequireSigning) {
            throw 'Signing is required but ANDROID_KEYSTORE_BASE64, ANDROID_KEYSTORE_PASSWORD or ANDROID_KEY_ALIAS is not set. An unsigned APK cannot be installed.'
        }
        Write-Warning 'No signing key configured: the release APK is unsigned and Android will refuse to install it.'
        return
    }

    $storePassword = $env:ANDROID_KEYSTORE_PASSWORD
    $env:NEXREMOTE_APK_KEY_PASS = if ([string]::IsNullOrWhiteSpace($env:ANDROID_KEY_PASSWORD)) { $storePassword } else { $env:ANDROID_KEY_PASSWORD }
    $keystorePath = Join-Path ([IO.Path]::GetTempPath()) 'nexremote-android-release.jks'
    [IO.File]::WriteAllBytes($keystorePath, [Convert]::FromBase64String($env:ANDROID_KEYSTORE_BASE64))

    try {
        if (Test-Path $ReleaseApk) {
            # apksigner only: jarsigner writes a v1 signature, which Android 11+ rejects for apps targeting API 30+.
            $apksigner = Resolve-AndroidApkSigner
            if (-not $apksigner) {
                throw 'apksigner was not found in the Android SDK build-tools.'
            }
            $signedApk = Join-Path (Split-Path -Parent $ReleaseApk) 'NexRemote-android-release-signed.apk'
            & $apksigner sign --ks $keystorePath --ks-pass env:ANDROID_KEYSTORE_PASSWORD --key-pass env:NEXREMOTE_APK_KEY_PASS --ks-key-alias $env:ANDROID_KEY_ALIAS --out $signedApk $ReleaseApk
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to sign Android APK: $ReleaseApk"
            }
            Move-Item $signedApk $ReleaseApk -Force
            Remove-Item "$ReleaseApk.idsig" -Force -ErrorAction SilentlyContinue

            & $apksigner verify --verbose --print-certs $ReleaseApk
            if ($LASTEXITCODE -ne 0) {
                throw "The signed APK failed verification: $ReleaseApk"
            }
        }
        elseif ($RequireSigning) {
            throw "No release APK to sign at $ReleaseApk"
        }

        if ($ReleaseBundle -and (Test-Path $ReleaseBundle)) {
            & jarsigner -keystore $keystorePath -storepass:env ANDROID_KEYSTORE_PASSWORD -keypass:env NEXREMOTE_APK_KEY_PASS -sigalg SHA256withRSA -digestalg SHA-256 $ReleaseBundle $env:ANDROID_KEY_ALIAS | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to sign Android bundle: $ReleaseBundle"
            }
        }
    }
    finally {
        Remove-Item $keystorePath -Force -ErrorAction SilentlyContinue
        Remove-Item Env:\NEXREMOTE_APK_KEY_PASS -ErrorAction SilentlyContinue
    }
}

function Build-Windows {
    Write-Section 'Windows (Electron + Python sidecar)'
    New-Item -ItemType Directory -Path $windowsDistRoot -Force | Out-Null

    Invoke-CommandChecked -Message 'uv sync (server)' -ScriptBlock {
        Push-Location $serverProject
        try { & uv sync } finally { Pop-Location }
    }

    if (-not $NoTests) {
        Invoke-CommandChecked -Message 'Server tests' -ScriptBlock {
            Push-Location $serverProject
            try { & uv run pytest } finally { Pop-Location }
        }
    }

    Invoke-CommandChecked -Message 'npm ci (desktop)' -ScriptBlock {
        Push-Location $desktopProject
        try { & npm ci } finally { Pop-Location }
    }

    Invoke-CommandChecked -Message 'MSIX package' -ScriptBlock {
        Push-Location $desktopProject
        try { & npm run package:appx } finally { Pop-Location }
    }

    Get-ChildItem (Join-Path $desktopProject 'release') -Filter '*.appx' |
        ForEach-Object { Copy-Item $_.FullName $windowsDistRoot -Force }
    Write-Host "Windows packages: $windowsDistRoot" -ForegroundColor Green
}

function Find-AndroidArtifact {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Pattern
    )

    Get-ChildItem (Join-Path (Join-Path (Join-Path $androidProject 'app') 'build') 'outputs') -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like $Pattern } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Build-Android {
    Write-Section 'Android'
    New-Item -ItemType Directory -Path $androidDistRoot -Force | Out-Null

    $java = Get-Command java -ErrorAction SilentlyContinue
    if (-not $java -and [string]::IsNullOrWhiteSpace($env:JAVA_HOME)) {
        throw 'Java is required for the Android build. Install JDK 17 or set JAVA_HOME.'
    }

    $gradleWrapper = if ($IsWindows) { Join-Path $androidProject 'gradlew.bat' } else { Join-Path $androidProject 'gradlew' }
    if (-not (Test-Path $gradleWrapper)) {
        throw "Gradle wrapper not found: $gradleWrapper"
    }

    $gradleTasks = @('assembleDebug', 'assembleRelease')
    if (-not $NoTests) {
        $gradleTasks = @('testDebugUnitTest', 'lintDebug') + $gradleTasks
    }
    if ($AndroidBundle) {
        $gradleTasks += 'bundleRelease'
    }

    Invoke-CommandChecked -Message 'Gradle Android build' -ScriptBlock {
        Push-Location $androidProject
        try {
            if ($IsWindows) {
                & $gradleWrapper @gradleTasks
            } else {
                & bash $gradleWrapper @gradleTasks
            }
        }
        finally {
            Pop-Location
        }
    }

    $debugApk = Find-AndroidArtifact -Pattern 'app-debug.apk'
    if ($debugApk) {
        Copy-ArtifactIfExists -Source $debugApk.FullName -Destination (Join-Path $androidDistRoot 'NexRemote-android-debug.apk') | Out-Null
    }

    $releaseApk = Find-AndroidArtifact -Pattern 'app-release*.apk'

    $releaseBundle = $null
    if ($AndroidBundle) {
        $releaseBundle = Find-AndroidArtifact -Pattern 'app-release.aab'
    }

    $stagedApk = Join-Path $androidDistRoot 'NexRemote-android-release.apk'
    $stagedBundle = if ($AndroidBundle) { Join-Path $androidDistRoot 'NexRemote-android-release.aab' } else { $null }

    if ($releaseApk) {
        Copy-ArtifactIfExists -Source $releaseApk.FullName -Destination $stagedApk | Out-Null
    }
    if ($releaseBundle) {
        Copy-ArtifactIfExists -Source $releaseBundle.FullName -Destination $stagedBundle | Out-Null
    }

    if ((Test-Path $stagedApk) -or ($stagedBundle -and (Test-Path $stagedBundle))) {
        Sign-AndroidPublish -ReleaseApk $stagedApk -ReleaseBundle $stagedBundle
    }

    $mapping = Join-Path (Join-Path (Join-Path (Join-Path (Join-Path $androidProject 'app') 'build') 'outputs') 'mapping') 'release'
    $mapping = Join-Path $mapping 'mapping.txt'
    if (Test-Path $mapping) {
        Copy-ArtifactIfExists -Source $mapping -Destination (Join-Path $androidDistRoot 'mapping.txt') | Out-Null
    }

    Write-Host "Android artifacts: $androidDistRoot" -ForegroundColor Green
}

Write-Host "`nNexRemote production build`n" -ForegroundColor Cyan
Write-Host "Root: $root" -ForegroundColor DarkGray

if (-not $SkipWindows) {
    Build-Windows
}

if (-not $SkipAndroid) {
    Build-Android
}

Write-Host "`nBuild complete." -ForegroundColor Green

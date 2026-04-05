# NexRemote production build script
# Builds the current WinUI 3 server and native Android client into dist/.

param(
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Release',

    [switch]$SkipWindows,
    [switch]$SkipAndroid,
    [switch]$NoTests,
    [switch]$AndroidBundle,

    [ValidateSet('x64', 'arm64', 'x86', 'win-x64', 'win-arm64', 'win-x86')]
    [string]$WindowsRuntime = 'x64'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
if ($IsWindows) {
    chcp 65001 | Out-Null
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$windowsProject = Join-Path (Join-Path (Join-Path (Join-Path $root 'windows_app') 'NexRemote') 'NexRemote') 'NexRemote.csproj'
$androidProject = Join-Path (Join-Path $root 'client') 'NexRemote'
$distRoot = Join-Path $root 'dist'
$windowsDistRoot = Join-Path $distRoot 'windows'
$androidDistRoot = Join-Path $distRoot 'android'

function Write-Section {
    param([string]$Text)
    Write-Host "`n==> $Text" -ForegroundColor Cyan
}

function Resolve-WindowsRuntimeIdentifier {
    param([string]$Runtime)

    switch ($Runtime.ToLowerInvariant()) {
        'x64' { 'win-x64' }
        'arm64' { 'win-arm64' }
        'x86' { 'win-x86' }
        default { $Runtime }
    }
}

function Resolve-WindowsPublishProfile {
    param([string]$RuntimeIdentifier)

    switch ($RuntimeIdentifier) {
        'win-x64' { 'win-x64.pubxml' }
        'win-arm64' { 'win-arm64.pubxml' }
        'win-x86' { 'win-x86.pubxml' }
        default { throw "Unsupported Windows runtime identifier: $RuntimeIdentifier" }
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

function Sign-WindowsPublish {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PublishDir
    )

    if ([string]::IsNullOrWhiteSpace($env:WINDOWS_SIGN_CERT_BASE64) -or [string]::IsNullOrWhiteSpace($env:WINDOWS_SIGN_CERT_PASSWORD)) {
        return
    }

    $signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1

    if (-not $signtool) {
        Write-Warning 'Windows code-signing certificate was provided, but signtool.exe was not found. Leaving Windows binaries unsigned.'
        return
    }

    $certPath = Join-Path $env:TEMP 'nexremote-signing.pfx'
    [IO.File]::WriteAllBytes($certPath, [Convert]::FromBase64String($env:WINDOWS_SIGN_CERT_BASE64))
    $timestamp = if ([string]::IsNullOrWhiteSpace($env:WINDOWS_SIGN_TIMESTAMP_URL)) { 'http://timestamp.digicert.com' } else { $env:WINDOWS_SIGN_TIMESTAMP_URL }

    Get-ChildItem $PublishDir -Recurse -File |
        Where-Object { $_.Extension -in '.exe', '.dll', '.msix', '.appx' } |
        ForEach-Object {
            & $signtool.FullName sign /f $certPath /p $env:WINDOWS_SIGN_CERT_PASSWORD /fd SHA256 /tr $timestamp /td SHA256 $_.FullName | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to sign Windows artifact: $($_.FullName)"
            }
        }
}

function Resolve-AndroidApkSigner {
    $roots = @()
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_SDK_ROOT)) { $roots += $env:ANDROID_SDK_ROOT }
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_HOME)) { $roots += $env:ANDROID_HOME }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { $roots += (Join-Path (Join-Path $env:LOCALAPPDATA 'Android') 'Sdk') }

    foreach ($rootPath in $roots) {
        $candidate = Get-ChildItem (Join-Path $rootPath 'build-tools') -Recurse -File -Filter apksigner* -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
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
        return
    }

    $storePassword = $env:ANDROID_KEYSTORE_PASSWORD
    $keyPassword = if ([string]::IsNullOrWhiteSpace($env:ANDROID_KEY_PASSWORD)) { $storePassword } else { $env:ANDROID_KEY_PASSWORD }
    $keystorePath = Join-Path $env:TEMP 'nexremote-android-release.jks'
    [IO.File]::WriteAllBytes($keystorePath, [Convert]::FromBase64String($env:ANDROID_KEYSTORE_BASE64))

    $apksigner = Resolve-AndroidApkSigner
    if ($apksigner -and (Test-Path $ReleaseApk)) {
        $signedApk = Join-Path (Split-Path -Parent $ReleaseApk) 'NexRemote-android-release-signed.apk'
        & $apksigner sign --ks $keystorePath --ks-pass "pass:$storePassword" --key-pass "pass:$keyPassword" --ks-key-alias $env:ANDROID_KEY_ALIAS --out $signedApk $ReleaseApk | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to sign Android APK: $ReleaseApk"
        }
        Move-Item $signedApk $ReleaseApk -Force
    }
    elseif (Test-Path $ReleaseApk) {
        & jarsigner -keystore $keystorePath -storepass $storePassword -keypass $keyPassword -sigalg SHA256withRSA -digestalg SHA-256 $ReleaseApk $env:ANDROID_KEY_ALIAS | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to sign Android APK: $ReleaseApk"
        }
    }

    if ($ReleaseBundle -and (Test-Path $ReleaseBundle)) {
        & jarsigner -keystore $keystorePath -storepass $storePassword -keypass $keyPassword -sigalg SHA256withRSA -digestalg SHA-256 $ReleaseBundle $env:ANDROID_KEY_ALIAS | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to sign Android bundle: $ReleaseBundle"
        }
    }
}

function Build-Windows {
    param([string]$RuntimeIdentifier)

    Write-Section "Windows $RuntimeIdentifier"
    New-Item -ItemType Directory -Path $windowsDistRoot -Force | Out-Null

    $profile = Resolve-WindowsPublishProfile -RuntimeIdentifier $RuntimeIdentifier
    $publishDir = Join-Path (Join-Path $windowsDistRoot $RuntimeIdentifier) 'publish'
    $zipPath = Join-Path $windowsDistRoot "NexRemote-$RuntimeIdentifier.zip"

    Invoke-CommandChecked -Message 'dotnet restore (Windows)' -ScriptBlock {
        & dotnet restore $windowsProject --runtime $RuntimeIdentifier
    }

    Invoke-CommandChecked -Message 'dotnet build (Windows)' -ScriptBlock {
        & dotnet build $windowsProject `
            --configuration $Configuration `
            --runtime $RuntimeIdentifier `
            --no-restore `
            -p:PublishProfile=$profile `
            -p:PublishTrimmed=false `
            -p:PublishReadyToRun=false `
            -p:PublishSingleFile=false
    }

    Invoke-CommandChecked -Message 'dotnet publish (Windows)' -ScriptBlock {
        & dotnet publish $windowsProject `
            --configuration $Configuration `
            --runtime $RuntimeIdentifier `
            --self-contained true `
            --no-restore `
            -p:PublishProfile=$profile `
            -p:PublishDir=$publishDir `
            -p:PublishTrimmed=false `
            -p:PublishReadyToRun=false `
            -p:PublishSingleFile=false
    }

    Sign-WindowsPublish -PublishDir $publishDir

    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $publishDir '*') -DestinationPath $zipPath -Force
    Write-Host "Windows package: $zipPath" -ForegroundColor Green
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
            & $gradleWrapper @gradleTasks
        }
        finally {
            Pop-Location
        }
    }

    $debugApk = Find-AndroidArtifact -Pattern 'app-debug.apk'
    if ($debugApk) {
        Copy-ArtifactIfExists -Source $debugApk.FullName -Destination (Join-Path $androidDistRoot 'NexRemote-android-debug.apk') | Out-Null
    }

    $releaseApk = Find-AndroidArtifact -Pattern 'app-release-*.apk'
    if (-not $releaseApk) {
        $releaseApk = Find-AndroidArtifact -Pattern 'app-release.apk'
    }

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
    $runtimeIdentifier = Resolve-WindowsRuntimeIdentifier -Runtime $WindowsRuntime
    Build-Windows -RuntimeIdentifier $runtimeIdentifier
}

if (-not $SkipAndroid) {
    Build-Android
}

Write-Host "`nBuild complete." -ForegroundColor Green

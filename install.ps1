# Instagram Reel Counter 1-Line Installer for Windows
$ErrorActionPreference = "Stop"
$TargetDir = "$HOME\instagram-reel-counter"

Write-Host "`n⚡ Installing Instagram Reel Counter..." -ForegroundColor Cyan

# 1. Verify Python availability
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host "[!] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "    Download Python 3.10+ from https://python.org and tick 'Add to PATH'." -ForegroundColor Yellow
    exit 1
}

# 2. Clone repository or download archive
if (Test-Path "$TargetDir\.git") {
    Set-Location $TargetDir
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git pull --quiet
    }
} elseif (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "📥 Cloning repository..." -ForegroundColor Cyan
    git clone --quiet https://github.com/prashanth-karanam/instagram-reel-counter.git $TargetDir
    Set-Location $TargetDir
} else {
    Write-Host "📥 Fetching archive from GitHub..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    $ZipPath = "$env:TEMP\ig_counter_temp.zip"
    $ExtractPath = "$env:TEMP\ig_counter_temp_extract"
    Invoke-WebRequest -Uri "https://github.com/prashanth-karanam/instagram-reel-counter/archive/refs/heads/main.zip" -OutFile $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force
    Copy-Item -Path "$ExtractPath\instagram-reel-counter-main\*" -Destination $TargetDir -Recurse -Force
    Remove-Item -Path $ZipPath, $ExtractPath -Recurse -Force
    Set-Location $TargetDir
}

# 3. Install dependencies
Write-Host "📦 Ensuring dependencies (instagrapi, rich, requests)..." -ForegroundColor Yellow
& $PythonCmd -m pip install --quiet --upgrade pip
& $PythonCmd -m pip install --quiet -r requirements.txt

# 4. Launch Application
Write-Host "🚀 Launching toolkit...`n" -ForegroundColor Green
& $PythonCmd app.py

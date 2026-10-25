# Instagram Reel Counter 1-Line Installer for Windows
$ErrorActionPreference = "Continue"
$TargetDir = "$HOME\instagram-reel-counter"

Write-Host ""
Write-Host "[*] Installing Instagram Reel Counter..." -ForegroundColor Cyan

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

# 2. Resilient Repository Fetching
$NeedsFetch = $true

if (Test-Path "$TargetDir\.git") {
    if (Test-Path "$TargetDir\app.py") {
        Set-Location $TargetDir
        if (Get-Command git -ErrorAction SilentlyContinue) {
            git fetch origin main --quiet 2>$null
            git reset --hard origin/main --quiet 2>$null
        }
        $NeedsFetch = $false
    } else {
        Remove-Item -Path $TargetDir -Recurse -Force -ErrorAction SilentlyContinue
    }
} elseif (Test-Path $TargetDir) {
    if (-not (Test-Path "$TargetDir\app.py")) {
        Remove-Item -Path $TargetDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        $NeedsFetch = $false
    }
}

if ($NeedsFetch) {
    $Cloned = $false
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "[*] Cloning repository..." -ForegroundColor Cyan
        git clone --quiet https://github.com/prashanth-karanam/instagram-reel-counter.git $TargetDir 2>$null
        if ((Test-Path "$TargetDir\app.py") -and ($LASTEXITCODE -eq 0)) {
            $Cloned = $true
        }
    }

    # Fallback to direct GitHub zip if git failed or is not available
    if (-not $Cloned) {
        Write-Host "[*] Fetching archive from GitHub..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
        $ZipPath = "$env:TEMP\ig_counter_temp_$PID.zip"
        $ExtractPath = "$env:TEMP\ig_counter_temp_extract_$PID"
        Remove-Item -Path $ZipPath, $ExtractPath -Recurse -Force -ErrorAction SilentlyContinue
        Invoke-WebRequest -Uri "https://github.com/prashanth-karanam/instagram-reel-counter/archive/refs/heads/main.zip" -OutFile $ZipPath -UseBasicParsing
        Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force
        Copy-Item -Path "$ExtractPath\instagram-reel-counter-main\*" -Destination $TargetDir -Recurse -Force
        Remove-Item -Path $ZipPath, $ExtractPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Final existence check
if (-not (Test-Path "$TargetDir\app.py")) {
    Write-Host "[!] Error: Failed to setup application files in $TargetDir" -ForegroundColor Red
    exit 1
}

Set-Location $TargetDir

# 3. Install dependencies
Write-Host "[*] Ensuring dependencies (instagrapi, rich, requests)..." -ForegroundColor Yellow
& $PythonCmd -m pip install --quiet --upgrade pip 2>$null
& $PythonCmd -m pip install --quiet instagrapi rich requests

# 4. Launch Application
Write-Host "[+] Launching toolkit..." -ForegroundColor Green
Write-Host ""
& $PythonCmd "$TargetDir\app.py"

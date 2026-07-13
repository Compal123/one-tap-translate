# -*- coding: utf-8 -*-
# Installer thong minh cho One Tap Translate:
#   - Do may co Python 3.12 chua; chua co thi TU CAI (winget -> fallback python.org)
#   - Tao moi truong ao .venv, tu chon PaddlePaddle GPU/CPU theo may
#   - Cai thu vien, tao shortcut ngoai Desktop
# Chay qua install.bat (bam dup). Tham so -NoPrompt/-NoLaunch dung de test tu dong.
param([switch]$NoPrompt, [switch]$NoLaunch)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $root

function Step($m) { Write-Host "`n>> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function Fail($m) { Write-Host "[X] $m" -ForegroundColor Red }
function EndExit($code) { if (-not $NoPrompt) { Read-Host "`nNhan Enter de thoat" }; exit $code }

Write-Host "============================================"
Write-Host "   One Tap Translate - Cai dat tu dong"
Write-Host "============================================"

# ---------- 1. Tim Python 3.12 ----------
function Find-Py312 {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $exe = & py -3.12 -c "import sys;print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    $cands = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312-64\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "${env:ProgramFiles(x86)}\Python312\python.exe"
    )
    foreach ($c in $cands) {
        if (Test-Path $c) {
            $v = & $c -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($v -eq "3.12") { return $c }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $v = & python -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($v -eq "3.12") { return (Get-Command python).Source }
    }
    return $null
}

function Install-Py312 {
    Step "Chua co Python 3.12 tren may - dang tu cai..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "   Cai qua winget (khong can quyen admin)..."
        try {
            & winget install --id Python.Python.3.12 -e --scope user --silent `
                --accept-source-agreements --accept-package-agreements
        } catch {}
        $f = Find-Py312
        if ($f) { return $f }
    }
    Write-Host "   Tai bo cai chinh thuc tu python.org..."
    $url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
    $inst = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $inst
    Write-Host "   Dang cai (ngam, khong hien cua so)..."
    Start-Process -FilePath $inst -Wait -ArgumentList `
        "/quiet","InstallAllUsers=0","PrependPath=1","Include_launcher=1","Include_pip=1"
    Remove-Item $inst -ErrorAction SilentlyContinue
    return Find-Py312
}

Step "Kiem tra Python 3.12..."
$py = Find-Py312
if (-not $py) { $py = Install-Py312 }
if (-not $py) {
    Fail "Khong cai duoc Python 3.12 tu dong."
    Write-Host "    Hay tai thu cong tai https://www.python.org/downloads/release/python-31210/"
    Write-Host "    (nho tick 'Add python.exe to PATH') roi chay lai install.bat."
    EndExit 1
}
Ok "Python 3.12: $py"

# ---------- 2. Tao moi truong ao ----------
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Step "Tao moi truong ao .venv..."
    & $py -m venv (Join-Path $root ".venv")
}
if (-not (Test-Path $venvPy)) { Fail "Tao venv that bai"; EndExit 1 }
Ok "Moi truong ao san sang"

# ---------- 3. Cai PaddlePaddle (tu chon GPU/CPU) ----------
Step "Cap nhat pip..."
& $venvPy -m pip install --upgrade pip --quiet

$hasNvidia = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "NVIDIA" }).Count -gt 0

Step "Cai PaddlePaddle (nang ~vai tram MB - vui long doi)..."
$paddleOk = $false
if ($hasNvidia) {
    Write-Host "   Phat hien GPU NVIDIA -> thu ban GPU (OCR nhanh hon)..."
    & $venvPy -m pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
    if ($LASTEXITCODE -eq 0) { $paddleOk = $true }
    else { Write-Host "   Ban GPU loi (thieu CUDA?) -> chuyen sang CPU..." -ForegroundColor Yellow }
} else {
    Write-Host "   Khong co GPU NVIDIA -> dung ban CPU (van chay tot)."
}
if (-not $paddleOk) {
    & $venvPy -m pip install paddlepaddle
    if ($LASTEXITCODE -ne 0) { Fail "Cai PaddlePaddle that bai"; EndExit 1 }
}
Ok "PaddlePaddle da cai"

Step "Cai cac thu vien con lai..."
& $venvPy -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "Cai thu vien that bai (kiem tra mang)"; EndExit 1 }
Ok "Da cai xong thu vien"

# ---------- 4. Tao shortcut ngoai Desktop ----------
Step "Tao shortcut..."
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$mainPy  = Join-Path $root "main.py"
try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnk = Join-Path $desktop "One Tap Translate.lnk"
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($lnk)
    $sc.TargetPath = $pythonw
    $sc.Arguments = "`"$mainPy`""
    $sc.WorkingDirectory = $root
    $sc.Description = "One Tap Translate - dich chu tren man hinh"
    $sc.Save()
    Ok "Da tao shortcut 'One Tap Translate' ngoai Desktop"
} catch {
    Write-Host "   (Khong tao duoc shortcut - van co the mo bang run.bat)" -ForegroundColor Yellow
}

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "   XONG! Bam shortcut 'One Tap Translate' ngoai" -ForegroundColor Green
Write-Host "   Desktop de mo app (hoac chay run.bat)." -ForegroundColor Green
Write-Host "   Lan chay dau tu tai model PP-OCRv5 (~22MB)." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

if (-not $NoLaunch -and -not $NoPrompt) {
    $ans = Read-Host "`nMo app luon bay gio? (Y/N)"
    if ($ans -match "^[Yy]") { Start-Process -FilePath $pythonw -ArgumentList "`"$mainPy`"" -WorkingDirectory $root }
}
EndExit 0

<#
.SYNOPSIS
    Build Bangla Likho (Windows x64) and compile the Inno Setup installer.

.DESCRIPTION
    Creates an isolated Python 3.11 environment, installs the trimmed Qt
    runtime, runs the regression suite, produces a one-folder PyInstaller
    build, then compiles the installer with Inno Setup 6 or 7.

.PARAMETER SkipTests
    Skip the unit-test gate (not recommended for releases).

.PARAMETER NoInstaller
    Build the application folder but do not compile the installer.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build_windows.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$NoInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

$Version = (Select-String -Path "ui\context.py" -Pattern 'VERSION\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
Write-Host "Bangla Likho $Version - Windows x64 build" -ForegroundColor Cyan
Write-Host ("-" * 62)

# ---------------------------------------------------------------- toolchain
function New-BuildEnvironment {
    param([string]$Target)
    # Prefer the Python already on PATH (GitHub Actions, winget, Store), and
    # fall back to the py launcher when only that is configured.
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            & python -m venv $Target
            if ($LASTEXITCODE -eq 0) { return }
        }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 -m venv $Target
        if ($LASTEXITCODE -eq 0) { return }
    }
    throw "Python 3.9+ x64 is required. Install it from python.org or the Microsoft Store."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating the build environment ..." -ForegroundColor Yellow
    New-BuildEnvironment -Target ".venv"
}
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python -c "import sys; print('Python', sys.version.split()[0])"

Write-Host "Installing dependencies ..." -ForegroundColor Yellow
& $python -m pip install --upgrade pip wheel --quiet
& $python -m pip install -r requirements.txt "pyinstaller==6.11.1" --quiet
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

# ------------------------------------------------------------------- tests
if (-not $SkipTests) {
    Write-Host "Running regression tests ..." -ForegroundColor Yellow
    & $python -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "Automated regression tests failed." }
}

# ------------------------------------------------------------------- build
Write-Host "Building application ..." -ForegroundColor Yellow
foreach ($stale in @("build\BanglaLikho", "dist\BanglaLikho")) {
    if (Test-Path $stale) { Remove-Item $stale -Recurse -Force }
}
& $python -m PyInstaller --noconfirm --clean BanglaLikho.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

$appDir = Join-Path $PSScriptRoot "dist\BanglaLikho"
$exe = Join-Path $appDir "BanglaLikho.exe"
if (-not (Test-Path $exe)) { throw "Expected executable was not created: $exe" }

$bytes = (Get-ChildItem $appDir -Recurse -File | Measure-Object Length -Sum).Sum
Write-Host ("Application folder: {0:N1} MB" -f ($bytes / 1MB)) -ForegroundColor Green
Write-Host ("Executable:         {0:N1} MB" -f ((Get-Item $exe).Length / 1MB))

# --------------------------------------------------------------- installer
if (-not $NoInstaller) {
    $iscc = $null
    $candidates = @(
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { $iscc = $candidate; break }
    }
    if (-not $iscc) {
        $iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
    }
    if (-not $iscc) {
        Write-Host "Inno Setup was not found - skipping installer compilation." -ForegroundColor Yellow
        Write-Host "Install Inno Setup 6/7, then run: ISCC.exe installer\BanglaLikho.iss"
        return
    }

    Write-Host "Compiling installer with $iscc ..." -ForegroundColor Yellow
    $outDir = Join-Path $PSScriptRoot "dist-installer"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    & $iscc "/DMyAppVersion=$Version" "installer\BanglaLikho.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

    $setup = Join-Path $outDir "BanglaLikho-Setup-$Version-x64.exe"
    if (-not (Test-Path $setup)) { throw "Installer was not created: $setup" }
    $hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash
    $setupName = Split-Path -Leaf $setup
    Set-Content -LiteralPath (Join-Path $outDir "SHA256SUMS.txt") `
        -Value "$hash  $setupName" -Encoding ASCII
    Write-Host ("Installer: {0} ({1:N1} MB)" -f $setupName, ((Get-Item $setup).Length / 1MB)) -ForegroundColor Green
    Write-Host "SHA-256: $hash" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "BUILD SUCCEEDED" -ForegroundColor Green
Write-Host "Portable folder : $appDir"
Write-Host "Do not distribute the EXE alone - keep its _internal folder beside it."

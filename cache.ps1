# nuke_cache.ps1
Write-Host "Initiating System & Workspace Cache Obliteration..." -ForegroundColor Cyan

# ---------------------------------------------------------
# LAYER 1: PYTHON & DEVELOPMENT CACHES
# ---------------------------------------------------------
Write-Host "Wiping Python and Testing Caches..." -ForegroundColor Yellow

# Define target cache directories
$devCaches = @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "build", "dist")

# Destroy cache directories
Get-ChildItem -Path . -Include $devCaches -Recurse -Force -ErrorAction SilentlyContinue -Directory | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    Write-Host "  Deleted DIR:  $($_.FullName)" -ForegroundColor DarkGray
}

# Destroy compiled bytecode files
Get-ChildItem -Path . -Include *.pyc, *.pyo, *.pyd -Recurse -Force -ErrorAction SilentlyContinue -File | ForEach-Object {
    Remove-Item $_.FullName -Force
    Write-Host "  Deleted FILE: $($_.FullName)" -ForegroundColor DarkGray
}

# Purge global pip cache
Write-Host "Purging Global PIP Cache..." -ForegroundColor Yellow
pip cache purge

# ---------------------------------------------------------
# LAYER 2: OS TEMPORARY FILES & PREFETCH
# ---------------------------------------------------------
Write-Host "Wiping System Temp & Prefetch Data..." -ForegroundColor Yellow

$tempTargets = @(
    $env:TEMP,                     # Current User Temp
    "$env:SystemRoot\Temp",        # System Temp
    "$env:SystemRoot\Prefetch"     # Execution Prefetch
)

foreach ($target in $tempTargets) {
    if (Test-Path $target) {
        # Note: SilentlyContinue is required because active processes will lock specific temp files.
        Get-ChildItem -Path $target -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Sanitized OS Directory: $target" -ForegroundColor DarkGray
    }
}

# ---------------------------------------------------------
# LAYER 3: PAGEFILE KERNEL ENFORCEMENT
# ---------------------------------------------------------
Write-Host "Configuring Kernel to Wipe Pagefile on Shutdown..." -ForegroundColor Yellow
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
Set-ItemProperty -Path $regPath -Name "ClearPageFileAtShutdown" -Value 1 -Type DWord
Write-Host "  Registry Updated. Pagefile will be overwritten with zeroes on next restart." -ForegroundColor DarkGray

Write-Host "Cache Obliteration Complete." -ForegroundColor Green
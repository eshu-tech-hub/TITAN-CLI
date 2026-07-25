#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $ProjectDir ".titan.pid"
$LogDir = Join-Path $ProjectDir "logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

if (Test-Path $PidFile) {
    $Pid = Get-Content $PidFile
    $Process = Get-Process -Id ([int]$Pid) -ErrorAction SilentlyContinue
    if ($Process) {
        Write-Host "TITAN is already running (PID: $Pid)"
        exit 1
    }
    Remove-Item $PidFile -Force
}

Write-Host "Starting TITAN..."
Set-Location $ProjectDir
$Process = Start-Process -FilePath "python" -ArgumentList "-m", "titan", "status" `
    -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $LogDir "titan.log") `
    -RedirectStandardError (Join-Path $LogDir "titan-error.log")
$Process.Id | Out-File -FilePath $PidFile -Encoding ascii
Write-Host "TITAN started (PID: $($Process.Id))"

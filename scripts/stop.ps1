#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $ProjectDir ".titan.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "TITAN is not running (no PID file)"
    exit 0
}

$Pid = [int](Get-Content $PidFile)
$Process = Get-Process -Id $Pid -ErrorAction SilentlyContinue

if ($Process) {
    Write-Host "Stopping TITAN (PID: $Pid)..."
    $Process.CloseMainWindow() | Out-Null
    $Waited = 0
    while ($Waited -lt 10) {
        $Process = Get-Process -Id $Pid -ErrorAction SilentlyContinue
        if (-not $Process) { break }
        Start-Sleep -Seconds 1
        $Waited++
    }
    if ($Process) {
        Write-Host "Force killing TITAN (PID: $Pid)..."
        Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
    }
    Write-Host "TITAN stopped"
} else {
    Write-Host "TITAN process $Pid is not running"
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

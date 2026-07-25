#Requires -Version 5.1
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $ProjectDir ".titan.pid"

if (-not (Test-Path $PidFile)) {
    Write-Output "NOT_RUNNING"
    exit 1
}

$Pid = [int](Get-Content $PidFile)
$Process = Get-Process -Id $Pid -ErrorAction SilentlyContinue

if ($Process) {
    Write-Output "HEALTHY"
    Write-Output "PID: $Pid"
    Write-Output "CPU: $($Process.CPU)s"
    exit 0
} else {
    Write-Output "UNHEALTHY"
    Write-Output "PID file exists but process $Pid is not running"
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

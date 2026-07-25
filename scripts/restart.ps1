#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Restarting TITAN..."
& (Join-Path $ScriptDir "stop.ps1")
Start-Sleep -Seconds 2
& (Join-Path $ScriptDir "start.ps1")

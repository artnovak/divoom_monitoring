$ErrorActionPreference = "Stop"

$taskName = "DivoomDitooMicMonitor"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $root "start_monitor.ps1"

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`"" `
  -WorkingDirectory $root

$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive `
  -RunLevel Limited

Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description "Starts the Divoom DitooMic PC monitor at Windows logon." `
  -Force | Out-Null

Start-ScheduledTask -TaskName $taskName

Write-Host "Installed and started scheduled task: $taskName"

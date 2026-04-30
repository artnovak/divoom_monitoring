$ErrorActionPreference = "Stop"

$processes = Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -match "divoom_pc_monitor\.app run"
  }

foreach ($process in $processes) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
  Write-Host "Stopped Divoom monitor process $($process.ProcessId)"
}

if (-not $processes) {
  Write-Host "No Divoom monitor process found"
}

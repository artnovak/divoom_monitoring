$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logs | Out-Null

$existing = Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -match "divoom_pc_monitor\.app run"
  }

foreach ($process in $existing) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

$stdout = Join-Path $logs "monitor.log"
$stderr = Join-Path $logs "monitor.err.log"
$args = "-m divoom_pc_monitor.app run --port COM7 --fps 2"
$env:PYTHONIOENCODING = "utf-8"

Start-Process `
  -FilePath $python `
  -ArgumentList $args `
  -WorkingDirectory $root `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -WindowStyle Hidden

Write-Host "Divoom monitor started. Logs: $stdout"

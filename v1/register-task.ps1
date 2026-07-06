# Registers the daily Land Scout scheduled task (7:00 AM, only when logged on
# so the off-screen Chrome window can open). Run once from an elevated or
# normal PowerShell:  powershell -ExecutionPolicy Bypass -File register-task.ps1

$py = (Get-Command python).Source
$script = Join-Path $PSScriptRoot "run_tracker.py"
$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "LandScout Daily Tracker" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Registered 'LandScout Daily Tracker' (daily 7:00 AM)."

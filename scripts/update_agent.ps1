param(
    [string]$SourcePath = ".",
    [string]$InstallPath = "C:\MonitoringAgent",
    [string]$TaskName = "MonitoringAgent"
)

Write-Host "Windows Monitoring Agent installatie gestart"

if (-not (Test-Path $SourcePath)) {
    Write-Error "SourcePath bestaat niet: $SourcePath"
    exit 1
}

Write-Host "Installatiemap aanmaken: $InstallPath"
New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null

Write-Host "Agentbestanden kopiëren"
Copy-Item "$SourcePath\agent.py" "$InstallPath\agent.py" -Force
Copy-Item "$SourcePath\metrics.py" "$InstallPath\metrics.py" -Force
Copy-Item "$SourcePath\secure_transport.py" "$InstallPath\secure_transport.py" -Force

if (-not (Test-Path "$InstallPath\agent_config.py")) {
    Copy-Item "$SourcePath\agent_config.py.example" "$InstallPath\agent_config.py" -Force
    Write-Host "agent_config.py aangemaakt. Vul daarna je keys in."
} else {
    Write-Host "agent_config.py bestaat al en wordt niet overschreven."
}

Write-Host "Python packages installeren"
python -m pip install --upgrade pip
python -m pip install requests psutil cryptography urllib3

Write-Host "Scheduled Task verwijderen als deze al bestaat"
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Write-Host "Scheduled Task aanmaken"
$Action = New-ScheduledTaskAction `
    -Execute "python.exe" `
    -Argument "`"$InstallPath\agent.py`""

$Trigger = New-ScheduledTaskTrigger -AtStartup

$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Secure Windows Monitoring Agent"

Write-Host "Agent starten"
Start-ScheduledTask -TaskName $TaskName

Write-Host "Installatie voltooid"
Write-Host "Controleer config:"
Write-Host "$InstallPath\agent_config.py"
Write-Host ""
Write-Host "Logs:"
Write-Host "$InstallPath\agent_windows.log"
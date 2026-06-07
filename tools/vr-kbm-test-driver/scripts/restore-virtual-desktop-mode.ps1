[CmdletBinding()]
param(
    [string]$SteamRoot = "C:\Program Files (x86)\Steam",
    [switch]$StopProcesses,
    [switch]$KeepBindingCache
)

$ErrorActionPreference = "Stop"

$ConfigPath = Join-Path $SteamRoot "config\steamvr.vrsettings"
$OpenXRConfigDir = Join-Path $SteamRoot "config\openxr"

function Ensure-Section {
    param(
        [Parameter(Mandatory = $true)]$Root,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not ($Root.PSObject.Properties.Name -contains $Name)) {
        $Root | Add-Member -MemberType NoteProperty -Name $Name -Value ([pscustomobject]@{})
    }
}

function Set-JsonProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Value
    )

    $Object | Add-Member -Force -MemberType NoteProperty -Name $Name -Value $Value
}

function Remove-JsonProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.PSObject.Properties.Remove($Name)
    }
}

function Backup-AppBindingCache {
    param([string]$Directory)

    if (-not (Test-Path $Directory)) {
        return
    }

    $files = Get-ChildItem $Directory -Filter "steam.app.2307350_*_binding.json" -ErrorAction SilentlyContinue
    if (-not $files) {
        return
    }

    $backupDir = Join-Path $Directory ("codex_2307350_binding_backups\" + (Get-Date -Format "yyyyMMdd_HHmmss"))
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    foreach ($file in $files) {
        Move-Item -Path $file.FullName -Destination (Join-Path $backupDir $file.Name) -Force
    }
    Write-Host "Moved old OpenXR app binding cache to $backupDir"
}

if ($StopProcesses) {
    Get-Process | Where-Object {
        $_.ProcessName -like "IntoTheRadius2*" -or
        $_.ProcessName -like "*Radius*" -or
        $_.ProcessName -like "vr*" -or
        $_.ProcessName -like "SteamVR*" -or
        $_.ProcessName -like "vrdashboard*" -or
        $_.ProcessName -like "vrcompositor*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

if (-not (Test-Path $ConfigPath)) {
    throw "SteamVR config not found: $ConfigPath"
}

$json = Get-Content $ConfigPath -Raw | ConvertFrom-Json

Ensure-Section $json "steamvr"
Ensure-Section $json "dashboard"
Ensure-Section $json "driver_simplecontroller"
Ensure-Section $json "driver_null"

Remove-JsonProperty $json.steamvr "forcedDriver"
Set-JsonProperty $json.steamvr "requireHmd" $true
Set-JsonProperty $json.steamvr "enableHomeApp" $true
Set-JsonProperty $json.steamvr "startDashboardFromAppLaunch" $true
Set-JsonProperty $json.dashboard "enableDashboard" $true
Set-JsonProperty $json.dashboard "startDashboardFromAppLaunch" $true
Set-JsonProperty $json.driver_simplecontroller "enable" $false
Set-JsonProperty $json.driver_null "enable" $false

foreach ($section in @("driver_simplecontroller", "driver_VirtualDesktop")) {
    if ($json.PSObject.Properties.Name -contains $section) {
        $json.$section.PSObject.Properties.Remove("blocked_by_safe_mode")
    }
}

$json | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $ConfigPath

if (-not $KeepBindingCache) {
    Backup-AppBindingCache $OpenXRConfigDir
}

Write-Host "SteamVR fake HMD settings have been removed."
Write-Host "Start Virtual Desktop Streamer and SteamVR normally after this."

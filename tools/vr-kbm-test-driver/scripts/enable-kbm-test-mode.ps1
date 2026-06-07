[CmdletBinding()]
param(
    [string]$SteamRoot = "C:\Program Files (x86)\Steam",
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

if (-not (Test-Path $ConfigPath)) {
    throw "SteamVR config not found: $ConfigPath"
}

$json = Get-Content $ConfigPath -Raw | ConvertFrom-Json

Ensure-Section $json "steamvr"
Ensure-Section $json "dashboard"
Ensure-Section $json "driver_simplecontroller"
Ensure-Section $json "driver_null"

Set-JsonProperty $json.steamvr "forcedDriver" "simplecontroller"
Set-JsonProperty $json.steamvr "requireHmd" $false
Set-JsonProperty $json.steamvr "enableHomeApp" $false
Set-JsonProperty $json.steamvr "startDashboardFromAppLaunch" $false
Set-JsonProperty $json.dashboard "enableDashboard" $false
Set-JsonProperty $json.dashboard "startDashboardFromAppLaunch" $false
Set-JsonProperty $json.driver_simplecontroller "enable" $true
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

Write-Host "SteamVR is now configured for Into the Radius 2 keyboard/mouse test mode."
Write-Host "Restart SteamVR and the game if they were already running."

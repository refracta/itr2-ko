[CmdletBinding()]
param(
    [string]$SteamRoot = "C:\Program Files (x86)\Steam",
    [string]$GameRoot = "C:\Program Files (x86)\Steam\steamapps\common\IntoTheRadius2",
    [int]$SteamVRStartupSeconds = 15,
    [int]$GameStartupSeconds = 35,
    [switch]$KeepBindingCache
)

$ErrorActionPreference = "Stop"

Get-Process | Where-Object {
    $_.ProcessName -like "IntoTheRadius2*" -or
    $_.ProcessName -like "*Radius*" -or
    $_.ProcessName -like "vr*" -or
    $_.ProcessName -like "SteamVR*" -or
    $_.ProcessName -like "vrdashboard*" -or
    $_.ProcessName -like "vrcompositor*"
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$enableScript = Join-Path $PSScriptRoot "enable-kbm-test-mode.ps1"
if ($KeepBindingCache) {
    & $enableScript -SteamRoot $SteamRoot -KeepBindingCache
}
else {
    & $enableScript -SteamRoot $SteamRoot
}

$SteamVRRoot = Join-Path $SteamRoot "steamapps\common\SteamVR"
$VRStartup = Join-Path $SteamVRRoot "bin\win64\vrstartup.exe"
$OpenXRRuntime = Join-Path $SteamVRRoot "steamxr_win64.json"
$GameExe = Join-Path $GameRoot "IntoTheRadius2.exe"

Start-Process -FilePath $VRStartup
Start-Sleep -Seconds $SteamVRStartupSeconds

$env:XR_RUNTIME_JSON = $OpenXRRuntime
Start-Process -FilePath $GameExe -ArgumentList "-windowed" -WorkingDirectory $GameRoot
Start-Sleep -Seconds $GameStartupSeconds

Get-Process | Where-Object {
    $_.ProcessName -like "IntoTheRadius2*" -or
    $_.ProcessName -like "vr*" -or
    $_.ProcessName -like "SteamVR*"
} | Select-Object ProcessName, Id, MainWindowTitle, Responding | Sort-Object ProcessName | Format-Table -AutoSize

[CmdletBinding()]
param(
    [string]$OpenVRRoot = "",
    [string]$WorkDir = "",
    [string]$CMakeExe = "C:\Program Files\CMake\bin\cmake.exe",
    [string]$SteamVRRoot = "C:\Program Files (x86)\Steam\steamapps\common\SteamVR",
    [string]$DriverInstallRoot = "",
    [switch]$SkipOpenVRClone,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$ToolRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DriverSource = Join-Path $ToolRoot "driver"

if (-not (Test-Path $DriverSource)) {
    throw "Driver source not found: $DriverSource"
}

if (-not $WorkDir) {
    $WorkDir = Join-Path $ToolRoot ".work"
}

if (-not $OpenVRRoot) {
    $OpenVRRoot = Join-Path $WorkDir "openvr"
}

if (-not $DriverInstallRoot) {
    $DriverInstallRoot = Join-Path $ToolRoot "build_simplecontroller"
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null

if (-not (Test-Path $OpenVRRoot)) {
    if ($SkipOpenVRClone) {
        throw "OpenVR root does not exist: $OpenVRRoot"
    }
    git clone --depth 1 https://github.com/ValveSoftware/openvr.git $OpenVRRoot
}

$OpenVRDriverRoot = Join-Path $OpenVRRoot "samples\drivers"
$OpenVRSimpleController = Join-Path $OpenVRDriverRoot "drivers\simplecontroller"
if (-not (Test-Path $OpenVRDriverRoot)) {
    throw "OpenVR sample driver CMake root not found: $OpenVRDriverRoot"
}

if (Test-Path $OpenVRSimpleController) {
    Remove-Item $OpenVRSimpleController -Recurse -Force
}
Copy-Item $DriverSource $OpenVRSimpleController -Recurse

$BuildDir = Join-Path $WorkDir "cmake_build_simplecontroller_msvc"
New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null

& $CMakeExe -S $OpenVRDriverRoot -B $BuildDir -G "Visual Studio 17 2022" -A x64
& $CMakeExe --build $BuildDir --target driver_simplecontroller --config Release --parallel 4

$BuiltDriver = Join-Path $OpenVRDriverRoot "output\drivers\simplecontroller"
$BuiltDll = Join-Path $BuiltDriver "bin\win64\driver_simplecontroller.dll"
if (-not (Test-Path $BuiltDll)) {
    throw "Built driver DLL not found: $BuiltDll"
}

if (-not $NoInstall) {
    if (Test-Path $DriverInstallRoot) {
        Remove-Item $DriverInstallRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $DriverInstallRoot -Force | Out-Null
    Copy-Item $BuiltDriver (Join-Path $DriverInstallRoot "simplecontroller") -Recurse

    $VrPathReg = Join-Path $SteamVRRoot "bin\win64\vrpathreg.exe"
    if (-not (Test-Path $VrPathReg)) {
        throw "vrpathreg.exe not found: $VrPathReg"
    }

    & $VrPathReg adddriver (Join-Path $DriverInstallRoot "simplecontroller")
}

Write-Host "Driver build complete."
Write-Host "Built driver: $BuiltDriver"
if (-not $NoInstall) {
    Write-Host "Installed driver root: $(Join-Path $DriverInstallRoot "simplecontroller")"
}

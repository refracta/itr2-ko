# ITR2 keyboard/mouse VR test driver

This tool is a local debug driver for checking Into the Radius 2 UI, translation strings, signs, and subtitles without putting on a VR headset every time.

It is based on Valve's OpenVR `simplecontroller` sample and adds:

- a fake HMD that can be controlled with mouse look
- simple Index/Knuckles-like controller inputs
- W/S fake-HMD forward/back movement for flat-screen translation checks
- SteamVR mode switch scripts for test mode and normal Virtual Desktop mode

This is not a production gameplay driver. It is intended for patch development and quick visual validation.

## Layout

```text
tools/vr-kbm-test-driver/
  driver/                 # OpenVR simplecontroller replacement source
  scripts/
    build-driver.ps1       # Fetch/build/install the OpenVR driver
    enable-kbm-test-mode.ps1
    restore-virtual-desktop-mode.ps1
    start-itr2-kbm-test.ps1
  LICENSE.openvr           # Valve OpenVR sample license
```

## Build and install

Requirements:

- Windows
- SteamVR
- Git
- CMake
- Visual Studio 2022 Build Tools with C++ tools

From PowerShell:

```powershell
cd C:\path\to\itr2-ko
& ".\tools\vr-kbm-test-driver\scripts\build-driver.ps1"
```

The script clones Valve OpenVR into `tools/vr-kbm-test-driver/.work/openvr`, overlays this repository's customized `simplecontroller` driver, builds `driver_simplecontroller.dll`, copies the built driver to `tools/vr-kbm-test-driver/build_simplecontroller/simplecontroller`, and registers it with SteamVR using `vrpathreg.exe`.

If OpenVR is already cloned elsewhere:

```powershell
& ".\tools\vr-kbm-test-driver\scripts\build-driver.ps1" `
  -OpenVRRoot "C:\path\to\openvr"
```

## Start test mode

```powershell
& ".\tools\vr-kbm-test-driver\scripts\start-itr2-kbm-test.ps1" `
  -GameRoot "C:\Program Files (x86)\Steam\steamapps\common\IntoTheRadius2"
```

This stops any running ITR2/SteamVR processes, enables the fake HMD driver, starts SteamVR, then starts ITR2 in a window.

## Restore Virtual Desktop mode

The fake HMD mode modifies global SteamVR settings. Restore normal Virtual Desktop or real-HMD behavior after testing:

```powershell
& ".\tools\vr-kbm-test-driver\scripts\restore-virtual-desktop-mode.ps1" -StopProcesses
```

The restore script removes `forcedDriver=simplecontroller`, disables `driver_simplecontroller`, re-enables normal SteamVR dashboard/home behavior, and moves ITR2 OpenXR binding cache files into a timestamped backup folder.

## Controls

| Key / mouse | Behavior |
| --- | --- |
| Mouse | HMD look while captured |
| `F9` | Toggle mouse capture |
| `Alt` or `Win` | Release mouse capture |
| `Home` | Reset yaw/pitch/HMD position/height |
| `W` / `S` | Move the fake HMD forward/back |
| `A` / `D` | Game-side lateral movement where supported |
| `PageUp` / `PageDown` | Adjust fake HMD height |
| Left mouse / `Enter` | Right trigger |
| `Q` / `E` | Grip |
| `Tab` | Stick click |
| `F5`-`F8` | Trackpad axis fallback |
| `F10` | Left menu |
| `F12` | System button |

Notes:

- W/S are blocked from reaching the game window and are consumed by the fake HMD movement code.
- ESC is blocked while the game/headset window is focused to avoid accidental test-session shutdown.
- The movement is HMD-pose movement, not real game locomotion. It is good enough for translation checks but can ignore collision or player-body constraints.

## SteamVR settings touched

`enable-kbm-test-mode.ps1` sets:

```text
steamvr.forcedDriver = simplecontroller
steamvr.requireHmd = false
driver_simplecontroller.enable = true
driver_null.enable = false
dashboard/home startup disabled
```

`restore-virtual-desktop-mode.ps1` removes `steamvr.forcedDriver`, disables `driver_simplecontroller`, and restores normal HMD requirements/dashboard behavior.

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms

$AppId = "2307350"
$PatchFiles = @(
    "pakchunk99-KO_Locres_P.pak",
    "pakchunk98-KO_EnglishSource-Windows_P.pak",
    "pakchunk98-KO_EnglishSource-Windows_P.utoc",
    "pakchunk98-KO_EnglishSource-Windows_P.ucas",
    "pakchunk100-KO_NotoSansKRFonts_P.pak",
    "pakchunk999-Windows_P.pak",
    "pakchunk999-Windows_P.utoc",
    "pakchunk999-Windows_P.ucas"
)

$StaleFiles = @(
    "pakchunk99-KO_LocresUnionPreserve_P.pak",
    "pakchunk99-KO_UAsset-Windows.pak",
    "pakchunk99-KO_UAsset-Windows.utoc",
    "pakchunk99-KO_UAsset-Windows.ucas"
)

function Get-SteamRoots {
    $roots = New-Object System.Collections.Generic.List[string]

    foreach ($registryPath in @(
        "HKCU:\Software\Valve\Steam",
        "HKLM:\Software\WOW6432Node\Valve\Steam",
        "HKLM:\Software\Valve\Steam"
    )) {
        try {
            $installPath = (Get-ItemProperty -Path $registryPath -ErrorAction Stop).InstallPath
            if ($installPath -and (Test-Path -LiteralPath $installPath)) {
                $roots.Add($installPath)
            }
        } catch {}
    }

    Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -like "[A-Z]:\" } | ForEach-Object {
        $candidate = Join-Path $_.Root "Program Files (x86)\Steam"
        if (Test-Path -LiteralPath $candidate) {
            $roots.Add($candidate)
        }
    }

    return $roots | Select-Object -Unique
}

function Get-SteamLibraries {
    $libraries = New-Object System.Collections.Generic.List[string]

    foreach ($steamRoot in Get-SteamRoots) {
        $libraries.Add($steamRoot)
        $vdfPath = Join-Path $steamRoot "config\libraryfolders.vdf"
        if (-not (Test-Path -LiteralPath $vdfPath)) {
            continue
        }

        $content = Get-Content -LiteralPath $vdfPath -Raw
        [regex]::Matches($content, '"path"\s+"([^"]+)"') | ForEach-Object {
            $path = $_.Groups[1].Value -replace "\\\\", "\"
            if ($path -and (Test-Path -LiteralPath $path)) {
                $libraries.Add($path)
            }
        }
    }

    return $libraries | Select-Object -Unique
}

function Read-AcfValue {
    param (
        [string]$Path,
        [string]$Key
    )

    $content = Get-Content -LiteralPath $Path -Raw
    $match = [regex]::Match($content, '"' + [regex]::Escape($Key) + '"\s+"([^"]+)"')
    if ($match.Success) {
        return $match.Groups[1].Value
    }

    return $null
}

function Get-SteamITR2Path {
    foreach ($library in Get-SteamLibraries) {
        $manifest = Join-Path $library "steamapps\appmanifest_$AppId.acf"
        if (-not (Test-Path -LiteralPath $manifest)) {
            continue
        }

        $installDir = Read-AcfValue -Path $manifest -Key "installdir"
        if (-not $installDir) {
            $installDir = "intotheradius2"
        }

        $gamePath = Join-Path $library ("steamapps\common\" + $installDir)
        if (Test-Path -LiteralPath (Join-Path $gamePath "IntoTheRadius2\Content\Paks")) {
            return $gamePath
        }
    }

    return $null
}

function Get-UserITR2Path {
    $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
    $folderBrowser.Description = "Into the Radius 2 설치 폴더를 선택하세요."
    $folderBrowser.RootFolder = [System.Environment+SpecialFolder]::MyComputer

    if ($folderBrowser.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $folderBrowser.SelectedPath
    }

    return $null
}

function Disable-StaleFile {
    param (
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return
    }

    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $destination = "$Path.disabled.$timestamp"
    Move-Item -LiteralPath $Path -Destination $destination -Force
    Write-Host "비활성화: $Path" -ForegroundColor Yellow
}

function Copy-PatchFile {
    param (
        [string]$Source,
        [string]$Destination
    )

    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    Write-Host "복사 완료: $(Split-Path -Leaf $Source)" -ForegroundColor Green
}

Write-Host "Into the Radius 2 한국어 패치 자동 설치를 시작합니다." -ForegroundColor Cyan

$gamePath = Get-SteamITR2Path
if ($gamePath) {
    Write-Host "Steam 설치 경로 감지: $gamePath"
} else {
    Write-Host "Steam 설치 경로를 자동으로 찾지 못했습니다."
    $gamePath = Get-UserITR2Path
}

if (-not $gamePath) {
    Write-Host "설치가 취소되었습니다." -ForegroundColor Yellow
    exit 1
}

$paksPath = Join-Path $gamePath "IntoTheRadius2\Content\Paks"
if (-not (Test-Path -LiteralPath $paksPath)) {
    Write-Host "올바른 Into the Radius 2 설치 폴더가 아닙니다: $gamePath" -ForegroundColor Red
    Write-Host "IntoTheRadius2\Content\Paks 폴더가 있는 위치를 선택해야 합니다." -ForegroundColor Red
    exit 1
}

foreach ($file in $PatchFiles) {
    $source = Join-Path $PSScriptRoot $file
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        Write-Host "패치 파일을 찾을 수 없습니다: $file" -ForegroundColor Red
        Write-Host "압축을 완전히 푼 뒤 install.bat를 다시 실행하세요." -ForegroundColor Red
        exit 1
    }
}

foreach ($file in $StaleFiles) {
    Disable-StaleFile -Path (Join-Path $paksPath $file)
}

foreach ($file in $PatchFiles) {
    Copy-PatchFile -Source (Join-Path $PSScriptRoot $file) -Destination (Join-Path $paksPath $file)
}

Write-Host ""
Write-Host "한국어 패치 설치가 완료되었습니다." -ForegroundColor Green
Write-Host "게임을 이미 실행 중이라면 종료 후 다시 실행하세요."

# Into the Radius 2 한국어 패치

Into the Radius 2 커뮤니티 한국어 패치입니다.

## 번역 참여

웹 번역 제안 페이지: [https://refracta.github.io/itr2-ko/](https://refracta.github.io/itr2-ko/)

페이지에서 번역을 수정한 뒤 `Issue로 PR 요청`을 누르면 GitHub Issue 작성 화면이 열립니다. Issue를 제출하면 번역 제안 Pull Request가 생성됩니다.

직접 수정하려면 `translations/unique_sources_with_ko.json`과 `translations/records_with_ko.json`을 같은 `source_id` 기준으로 함께 수정한 뒤 Pull Request를 열면 됩니다.

## 설치

릴리즈에서 `ITR2_Korean.zip`을 받은 뒤 압축을 풀고 `install.bat`를 실행합니다.

자동 설치가 실패하면 zip 안의 `.pak`, `.utoc`, `.ucas` 파일을 아래 경로에 직접 복사합니다.

```text
IntoTheRadius2/Content/Paks
```

설치 대상 파일:

```text
pakchunk99-KO_Locres_P.pak
pakchunk99-KO_UAsset-Windows.pak
pakchunk99-KO_UAsset-Windows.utoc
pakchunk99-KO_UAsset-Windows.ucas
pakchunk100-KO_NotoSansKRFonts_P.pak
pakchunk999-Windows_P.pak
pakchunk999-Windows_P.utoc
pakchunk999-Windows_P.ucas
```

## Raw 입력 준비

직접 빌드할 때 사용하는 로컬 입력 파일입니다. 평문 원본 게임 파일은 커밋하지 않습니다.

게임 설치 폴더 예:

```text
I:\SteamLibrary\steamapps\common\IntoTheRadius2
```

원본 게임 폴더에서 프로젝트로 복사하는 파일:

| 원본 게임 파일 | 프로젝트 위치 | 용도 |
| --- | --- | --- |
| `IntoTheRadius2/Content/Paks/pakchunk0-Windows.pak` | `raw/game/pakchunk0-Windows.pak` | 원본 `Game.locres`, `Game.locmeta` 추출 |

`EnglishSource.uasset` raw 파일을 새로 만들 때는 원본 게임 폴더의 아래 두 파일도 필요합니다.

```text
IntoTheRadius2/Content/Paks/pakchunk0-Windows.utoc
IntoTheRadius2/Content/Paks/pakchunk0-Windows.ucas
```

추출 예:

```bash
python scripts/build/extract_iostore_file.py \
  "/path/to/IntoTheRadius2/Content/Paks/pakchunk0-Windows.utoc" \
  "/path/to/IntoTheRadius2/Content/Paks/pakchunk0-Windows.ucas" \
  "../../../Projectc/Content/ITR2/Configurations/Localization/EnglishSource.uasset" \
  -o raw/base/EnglishSource.uasset.raw
```

전체 raw 입력 구조:

```text
raw/
  game/
    pakchunk0-Windows.pak
  base/
    EnglishSource.uasset.raw
    EnglishSource.locres_meta.json
  prebuilt/
    pakchunk100-KO_NotoSansKRFonts_P.pak
    pakchunk999-Windows_P.pak
    pakchunk999-Windows_P.utoc
    pakchunk999-Windows_P.ucas
```

`raw/base/EnglishSource.uasset.raw`는 원본 게임의 `../../../Projectc/Content/ITR2/Configurations/Localization/EnglishSource.uasset`를 추출한 raw 파일입니다.

`raw/base/EnglishSource.locres_meta.json`는 `EnglishSource.uasset` 문자열을 `Game.locres`의 `EnglishSource` namespace에도 넣기 위한 해시 메타데이터입니다. 일부 UI는 uasset 직접 패치보다 locres 경로를 먼저 읽기 때문에 필요합니다.

`raw/prebuilt/` 파일은 한국어 폰트와 UI 폰트 override입니다. 번역문만 수정하는 경우 다시 만들 필요가 없습니다.

## 참고한 모드

아래 모드와 글은 파일 구조, 설치 경로, 폰트 처리, 번역 범위 분석에 참고했습니다. 이 저장소와 릴리즈에는 해당 모드의 파일, 번역문, 에셋을 포함하지 않습니다.

- Nexus Mods: Japanese Translation Mod
- Nexus Mods: ITR2 Japanese Translation by Reindeer1899
- Nexus Mods: Russian for Into the Radius 2
- Steam Community Guide: Руссификатор
- Steam Discussion: LOCALIZATION - MOD - DEV

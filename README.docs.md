# Into the Radius 2 한국어 번역 패치 기술 기록

이 문서는 사용자용 설치 안내가 아니라, 패치를 유지보수할 때 필요한 조사 결과와 시행착오를 남기는 내부 기록입니다. 특히 코드만 읽어서는 알기 어려운 판단 근거를 보존하는 데 목적이 있습니다.

## 호환 버전

이 패치는 아래 게임 빌드를 기준으로 추출하고 검증했습니다.

| 항목 | 값 |
| --- | --- |
| 게임 버전 | `v1.0.6 rev 44918` |
| Steam appid | `2307350` |
| Steam buildid | `23110238` |
| Depot manifest | `8219654773261890178` |

게임 업데이트 후에는 `Game.locres` 엔트리, `EnglishSource.uasset` offset, IoStore override 경로가 달라질 수 있습니다. 새 빌드에서는 원본 리소스를 다시 추출하고 빌드 검증을 다시 해야 합니다.

## 참고한 커뮤니티 번역 모드

파일 구조, 번역 범위, 폰트 처리, 설치 방식 분석에 참고했습니다.

| 언어 | 사례 | 확인한 점 |
| --- | --- | --- |
| 일본어 | Nexus Mods: [Japanese Translation Mod](https://www.nexusmods.com/intotheradius2/mods/145) | 기계번역 기반으로 튜토리얼, 퀘스트, UI, 아이템명을 폭넓게 처리한 것으로 보입니다. `Game.locres`뿐 아니라 `EnglishSource` 계열 문자열을 함께 다루는 구조가 확인됐습니다. |
| 일본어 | Nexus Mods: [ITR2 Japanese Translation by Reindeer1899](https://www.nexusmods.com/intotheradius2/mods/211) | 수동 번역 모드입니다. v1.0.6 대응, 일부 폰트를 Noto Sans Japanese로 교체, 하드코딩 텍스트 일부는 영어로 남는다고 설명합니다. 설치는 여러 파일을 `IntoTheRadius2/Content/Paks`에 넣는 방식입니다. |
| 러시아어 | Nexus Mods: [Russian for Into the Radius 2](https://www.nexusmods.com/intotheradius2/mods/144) | 게임을 러시아어로 번역하는 모드입니다. locres와 uasset 양쪽을 분석할 때 기준 자료로 썼습니다. |
| 러시아어 | Steam Community Guide: [Руссификатор](https://steamcommunity.com/sharedfiles/filedetails/?id=3657194872) | 99% 텍스트 러시아어화를 주장합니다. 설치 경로가 `Content/Paks`와 `Content/Paks/Mods`로 나뉘며, `Game.locres`, `EnglishSource.uasset` 언급이 있습니다. |
| 이탈리아어 | Steam Discussion: [LOCALIZATION - MOD - DEV](https://steamcommunity.com/app/2307350/discussions/0/591783706468080541/) | 첫 챕터 번역 모드 사례가 있었습니다. 개발자는 정식 1.0 또는 그 직후 로컬라이징을 검토하겠다고 답했습니다. |

중요한 결론은 러시아어와 일본어 모드 모두 `Game.locres`만 바꾸는 방식으로는 충분하지 않았다는 점입니다. Into the Radius 2는 일부 UI와 자막성 텍스트를 `EnglishSource.uasset` 쪽에서도 읽습니다.

## 추출 범위와 번역량

현재 기준 추출 수치는 `reports/itr2_translation_extraction_report.md`에 남아 있습니다.

| 구분 | 수치 |
| --- | ---: |
| 원본 `Game.locres` 엔트리 | 2164 |
| 원본 `Game.locres` 고유 문자열 | 1282 |
| 원본 `EnglishSource.uasset` GUID/text pair | 3301 |
| 통합 위치 레코드 | 5465 |
| 고유 source queue | 3535 |
| 번역 대상 source | 3427 |
| 번역 완료 source | 3427 |

러시아어 모드와 대조했을 때, 러시아어 `Game.locres`는 원본 locres 키 2164개를 모두 덮었지만 `EnglishSource.uasset`는 현재 기준 3301개 중 2444개 키만 겹쳤고 857개가 빠졌습니다. 그래서 러시아어 번역량을 기준으로 삼지 않고, 영어 원문 전체를 기준으로 추출해서 한국어를 붙였습니다.

일본어 fUyU 1.0.5 계열은 locres에 4701개 엔트리가 있었고, 원본 locres 2164개와 EnglishSource 추가 키 2537개를 함께 담는 형태였습니다. 다만 `EnglishSource` namespace에서 같은 key가 서로 다른 영어 문자열을 가리키는 충돌이 있어, key 하나만으로 병합하면 오역 또는 누락이 생깁니다.

## 번역 데이터 구조

번역 데이터는 두 파일로 나뉩니다.

| 파일 | 역할 |
| --- | --- |
| `translations/unique_sources_with_ko.json` | 번역자가 다루기 좋은 고유 원문 단위입니다. 같은 영어 원문은 하나의 `source_id`로 묶습니다. |
| `translations/records_with_ko.json` | 실제 패치에 필요한 위치 단위 레코드입니다. locres namespace/key/hash, uasset offset/end 같은 바이너리 패치 정보를 포함합니다. |

`source_id`는 영어 원문 기준 식별자입니다. 같은 영어가 여러 위치에 있어도 하나의 번역을 공유하고, 빌드 전에는 `records_with_ko.json`에도 같은 한국어가 반영되어 있어야 합니다.

검증 스크립트 `scripts/validate/translations.py`는 다음을 확인합니다.

- `source_id`가 원문과 일치하는지
- 고유 원문과 위치 레코드가 서로 참조되는지
- 번역 대상인데 `ko`가 비어 있지 않은지
- placeholder가 번역문에서 사라지지 않았는지

## 번역 대상 게임 리소스

현재 텍스트 패치의 기준이 되는 원본 리소스는 아래입니다.

| 원본 게임 리소스 | 프로젝트 입력 | 패치 산출물 | 용도 |
| --- | --- | --- | --- |
| `IntoTheRadius2/Content/Localization/Game/en/Game.locres` | `raw/game/pakchunk0-Windows.pak`에서 추출 | `pakchunk99-KO_Locres_P.pak` | 일반 Unreal localization 문자열 |
| `IntoTheRadius2/Content/Localization/Game/Game.locmeta` | `raw/game/pakchunk0-Windows.pak`에서 추출 | `pakchunk99-KO_Locres_P.pak` | locres와 함께 들어가는 localization metadata |
| `../../../Projectc/Content/ITR2/Configurations/Localization/EnglishSource.uasset` | `raw/base/EnglishSource.uasset.raw` | `pakchunk99-KO_UAsset-Windows.*` | locres 밖에 남는 UI, 자막성 텍스트, 설정 문자열 |
| `EnglishSource` namespace locres metadata | `raw/base/EnglishSource.locres_meta.json` | `pakchunk99-KO_Locres_P.pak` | uasset 문자열을 locres 경로에서도 읽히게 하는 보강 데이터 |
| UI/Slate/UMG 폰트 에셋 | `raw/prebuilt/*` | `pakchunk100-KO_NotoSansKRFonts_P.pak`, `pakchunk999-Windows_P.*` | 한글 글리프 표시 |

텍스처에 구워진 표지판 문구는 위 리소스로 번역되지 않습니다. 그런 문구는 별도 텍스처 패치 대상입니다.

### 로컬 입력 파일 준비

직접 빌드할 때 사용하는 로컬 입력 파일입니다.

게임 설치 폴더 예:

```text
C:\Program Files (x86)\Steam\steamapps\common\IntoTheRadius2
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

## 키보드/마우스 VR 테스트 드라이버

VR 착용 없이 번역 UI, 자막, 표지판을 빠르게 확인하기 위한 SteamVR fake HMD 도구를 `tools/vr-kbm-test-driver/`에 포함했습니다. 번역 패치 검증 비용을 낮추기 위한 유지보수용 도구입니다.

빌드/설치:

```powershell
& ".\tools\vr-kbm-test-driver\scripts\build-driver.ps1"
```

테스트 모드 실행:

```powershell
& ".\tools\vr-kbm-test-driver\scripts\start-itr2-kbm-test.ps1" `
  -GameRoot "C:\Program Files (x86)\Steam\steamapps\common\IntoTheRadius2"
```

Virtual Desktop/일반 HMD 모드로 원복:

```powershell
& ".\tools\vr-kbm-test-driver\scripts\restore-virtual-desktop-mode.ps1" -StopProcesses
```

이 도구는 SteamVR 전역 설정의 `forcedDriver`를 바꾸므로 테스트 후 반드시 원복해야 합니다. 자세한 사용법은 `tools/vr-kbm-test-driver/README.md`를 참고하세요.

## 현재 패치 적용 원리

현재 패치는 세 갈래로 적용됩니다.

| 산출물 | 목적 |
| --- | --- |
| `pakchunk99-KO_Locres_P.pak` | `Game.locres`를 한국어 locres로 override합니다. |
| `pakchunk99-KO_UAsset-Windows.*` | `EnglishSource.uasset`를 직접 패치한 IoStore override입니다. |
| `pakchunk100-KO_NotoSansKRFonts_P.pak`, `pakchunk999-Windows_P.*` | 한국어 표시를 위한 폰트와 UI 폰트 override입니다. |

### Game.locres

`raw/game/pakchunk0-Windows.pak`에서 원본 `IntoTheRadius2/Content/Localization/Game/en/Game.locres`와 `Game.locmeta`를 읽습니다. locres는 namespace와 key, `key_hash`, `source_hash`, localized string array로 구성됩니다.

중요한 시행착오는 `source_hash`입니다. Unreal locres의 source hash는 영어 원문을 UTF-32LE로 인코딩한 뒤 CRC32를 계산해야 합니다. 이 값이 틀리면 엔트리가 존재해도 런타임에서 원하는 번역으로 잡히지 않는 사례가 있었습니다.

### EnglishSource.uasset 직접 패치

`EnglishSource.uasset` 내부에는 GUID와 문자열이 FString 형태로 들어 있습니다. 빌드 스크립트는 `records_with_ko.json`의 `text_offset`과 `end`를 기준으로 원문 FString을 다시 읽어 검증한 뒤, 같은 위치를 한국어 FString으로 교체합니다.

한국어는 ASCII가 아니므로 FString 길이가 음수인 UTF-16LE 형식으로 저장됩니다. 문자열 길이가 바뀌기 때문에 export serial size도 같이 갱신합니다. 패치 후에는 다시 파싱해서 namespace가 `EnglishSource`인지, 엔트리 수와 번역 결과가 기대값과 맞는지 확인합니다.

완성된 raw uasset은 단독 파일로는 로드되지 않으므로 IoStore 컨테이너로 다시 감쌉니다. 런타임 override에 필요한 mount path는 `../../../Projectc/Content/ITR2/Configurations/Localization/`입니다. `IntoTheRadius2` mount path로 만든 컨테이너도 빌드는 됐지만 실제 게임에서는 override되지 않았습니다.

### EnglishSource locres union

일부 UI는 `EnglishSource.uasset` 직접 패치보다 `Game.locres`의 `EnglishSource` namespace를 먼저 읽는 것으로 보였습니다. 그래서 `EnglishSource.uasset`의 문자열도 `Game.locres` 안의 `EnglishSource` namespace에 union 형태로 넣습니다.

이때 `EnglishSource.locres_meta.json`의 `key_hash`가 필요하고, `source_hash`는 위와 같은 CRC32 UTF-32LE 규칙으로 다시 계산합니다.

key 충돌 처리는 조심해야 합니다. 조사 시 `EnglishSource` namespace에서 같은 key를 공유하지만 영어 원문이 다른 locres/uasset 레코드가 600개 있었습니다. 그래서 단순히 key 기준으로 합치지 않습니다. 현재 빌드는 uasset 쪽 실문자열을 우선하고, `Placeholder text` 충돌은 원래 locres 값을 보존합니다.

### 수동 추가 locres 엔트리

테스트 중 일부 메인 메뉴 UI는 추출된 레코드만으로 번역되지 않았습니다. 대표적으로 다음 계열입니다.

- `Start new game`
- `Starting a new game will delete all Single-player saves. Are you sure?`
- `Yes` / `No`
- `On` / `Off`
- `Measurement` / `Metric` / `Imperial`

이 문자열들은 `scripts/build/build_locres_patch.py`의 `EXTRA_ENGLISHSOURCE_LOCRES_ENTRIES`로 보강합니다. 이때 key hash는 Unreal `FTextKey` 계열 해시를 맞춰야 해서 CityHash64 UTF-16LE 결과의 하위 32비트와 상위 32비트 조합을 사용합니다.

## 시행착오 기록

`Game.locres`만 패치하면 기본 메뉴, 체인지로그, 일부 설정 UI가 영어로 남았습니다. 반대로 `EnglishSource.uasset`만 직접 패치해도 일부 UI가 locres 경로를 타는 것처럼 보여 누락이 남았습니다. 현재처럼 locres와 uasset을 동시에 패치해야 합니다.

러시아어 모드가 100%에 가깝다고 설명되어 있어도, 현재 게임 빌드의 영어 원문 전체를 기준으로는 누락이 있었습니다. 그래서 다른 언어 모드의 고유 번역량을 기준으로 번역 대상을 정하면 안 됩니다.

일본어 모드의 폰트 처리 방식은 참고할 만했지만, 일본어 CJK 폰트가 곧 한국어 표시를 보장하지는 않았습니다. 실제 테스트에서 한국어가 공백처럼 보이는 UI가 있었고, Noto Sans KR 계열 폰트 override가 필요했습니다. 맑은 고딕은 스타일상 제외했습니다.

셰이더 컴파일 캐시는 텍스트 미표시 원인으로 보지 않았습니다. 한국어가 보이지 않는 문제는 셰이더보다 로드된 폰트 에셋, locres source hash, 또는 실제 로드 경로 문제였습니다.

`Retoc`류 도구로 새 IoStore 컨테이너를 만들 때 mount path가 맞지 않으면 파일은 정상처럼 보여도 게임에서 override되지 않습니다. `EnglishSource.uasset`는 `Projectc` mount point가 필요했습니다.

이미지 표지판에 박힌 영어는 텍스트 리소스가 아닙니다. 예를 들어 `Follow the UNPSC instructions to enter the Facility` 같은 표지판은 locres/uasset 번역으로 바뀌지 않습니다. 텍스처를 찾아 수정해야 하며, dds 계열 추출 결과가 노이즈처럼 보이는 경우에는 압축 포맷, swizzle, mipmap, 채널 해석 문제를 별도로 풀어야 합니다.

## 번역 용어와 UI 정책

현재 적용한 주요 용어 기준입니다.

| 원문 | 한국어 |
| --- | --- |
| Radius | 반경 |
| Return to the Radius | 반경으로 복귀 |
| Ironman | 철인 |
| OK | 확인 |
| On / Off | 켜기 / 끄기 |
| Yes / No | 예 / 아니요 |
| Measurement | 단위 |
| Metric | 미터법 |
| Imperial | 야드파운드법 |

버튼이나 짧은 UI는 직역보다 실제 게임 안에서 읽히는 길이와 맥락을 우선합니다. `Return to the Radius`는 메뉴 버튼 문맥에서 `반경으로 복귀`로 맞췄습니다.

## 업데이트 때 확인할 것

게임 버전이 바뀌면 다음을 확인해야 합니다.

1. `Game.locres` 엔트리 수와 namespace 구성이 바뀌었는지 확인합니다.
2. `EnglishSource.uasset`의 GUID/text pair 수와 offset이 바뀌었는지 확인합니다.
3. `records_with_ko.json`의 offset 기반 레코드가 새 raw uasset과 일치하는지 확인합니다.
4. 새 영어 원문이 생기면 `unique_sources_with_ko.json`과 `records_with_ko.json`에 반영합니다.
5. 빌드 후 메인 메뉴, 설정, 새 게임 확인 모달, 체인지로그, 튜토리얼 진입부, 자막을 직접 확인합니다.
6. 한국어가 빈칸으로 보이면 먼저 폰트 로드 문제인지, 해당 문자열이 어느 컨테이너에서 로드되는지, 이미지 텍스처인지 분리합니다.

이 패치에서 말하는 "번역 완료"는 추출된 텍스트 리소스 기준입니다. 텍스처에 구워진 글자, 실제 하드코딩 문자열, 업데이트로 새로 생긴 문자열은 별도 작업 대상입니다.

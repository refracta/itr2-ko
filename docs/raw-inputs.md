# Raw 입력 구조

CI 빌드는 `raw/`를 표준 입력 디렉터리로 사용합니다. 다른 maintainer도 같은 구조로 파일을 복사하면 동일한 파이프라인을 사용할 수 있습니다.

```text
raw/
  game/
    pakchunk0-Windows.pak
  base/
    EnglishSource.uasset.raw
  templates/
    englishsource_iostore/
      pakchunk98-KO_EnglishSource-Windows_P.pak
      pakchunk98-KO_EnglishSource-Windows_P.utoc
      pakchunk98-KO_EnglishSource-Windows_P.ucas
  prebuilt/
    pakchunk100-KO_NotoSansKRFonts_P.pak
    pakchunk999-Windows_P.pak
    pakchunk999-Windows_P.utoc
    pakchunk999-Windows_P.ucas
```

`pakchunk0-Windows.pak`는 원본 `Game.locres`와 `Game.locmeta`를 읽는 데 사용합니다.

`base/EnglishSource.uasset.raw`는 원본 게임에서 추출한 `ITR2/Configurations/Localization/EnglishSource.uasset` export bundle입니다. 이 파일을 직접 패치하므로 `EnglishSource.uasset` 문자열은 locres 우회 방식에 의존하지 않습니다.

`templates/englishsource_iostore/`는 원본 게임의 `EnglishSource.uasset/.uexp`를 retoc으로 다시 패키징해서 만든 자체 IoStore 템플릿입니다. 러시아/일본어 모드 파일을 사용하지 않습니다.

`prebuilt/` 파일은 현재 한국어 폰트/UI 폰트 override입니다. 번역문만 수정하는 PR에서는 이 파일들을 다시 만들 필요가 없습니다.

## 암호화 Raw Bundle

평문 raw 입력을 커밋하지 않고 저장하려면 다음 명령을 사용합니다.

```bash
RAW_PACK_PASSPHRASE='long secret here' scripts/build/package_raw_inputs.sh
```

그러면 아래 파일이 생성됩니다.

```text
raw/private_inputs.tar.gpg
```

CI는 이 파일을 복호화한 뒤 `raw/` 아래에 평문 입력을 펼칩니다.

GitHub Actions secret에는 아래 값을 설정해야 합니다.

```text
RAW_PACK_PASSPHRASE
```

빌드 workflow는 먼저 `raw/`의 평문 파일을 확인하고, 없으면 `raw/private_inputs.tar.gpg`를 복호화합니다.

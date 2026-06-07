# Into the Radius 2 한국어 패치

Into the Radius 2 커뮤니티 한국어 패치 빌드 파이프라인입니다.

## 번역 참여

1. `translations/records_with_ko.json` 또는 `translations/unique_sources_with_ko.json`을 수정합니다.
2. Pull Request를 엽니다.
3. CI가 JSON 형식, placeholder 보존, 번역 누락 여부를 검사합니다.
4. `main`에 병합되면 CI가 패치를 다시 빌드하고 새 릴리즈를 만듭니다.

## 릴리즈 이름

릴리즈는 DF_Korean과 같은 방식으로 생성됩니다.

```text
ITR2_Korean-YYYYMMDDHHMMSS-<commit>
```

릴리즈 제목은 다음 형식입니다.

```text
ITR2_Korean (<commit>)
```

배포 파일 이름은 `ITR2_Korean.zip`입니다.

## 설치

릴리즈에서 `ITR2_Korean.zip`을 받은 뒤 압축을 풀고 `install.bat`를 실행합니다.

자동 설치가 실패하면 zip 안의 `.pak`, `.utoc`, `.ucas` 파일을 아래 경로에 직접 복사합니다.

```text
IntoTheRadius2/Content/Paks
```

설치 대상 파일:

```text
pakchunk99-KO_LocresUnionPreserve_P.pak
pakchunk100-KO_NotoSansKRFonts_P.pak
pakchunk999-Windows_P.pak
pakchunk999-Windows_P.utoc
pakchunk999-Windows_P.ucas
```

## Raw 입력

평문 원본 게임 파일은 커밋하지 않습니다. 빌드 스크립트는 maintainer 전용 입력을 `raw/`에서 읽습니다.

```text
raw/game/pakchunk0-Windows.pak
raw/references/japanese_entries.json
raw/prebuilt/pakchunk100-KO_NotoSansKRFonts_P.pak
raw/prebuilt/pakchunk999-Windows_P.pak
raw/prebuilt/pakchunk999-Windows_P.utoc
raw/prebuilt/pakchunk999-Windows_P.ucas
```

CI는 `raw/private_inputs.tar.gpg`를 `RAW_PACK_PASSPHRASE` secret으로 복호화해서 같은 구조로 사용합니다.

자세한 내용은 `docs/raw-inputs.md`를 참고하세요.

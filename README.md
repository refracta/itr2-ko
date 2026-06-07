# Into the Radius 2 한국어 번역 패치

커뮤니티 한국어 번역 패치입니다.

## 호환 버전

이 패치는 `Into the Radius 2 v1.0.6 rev 44918` 기준으로 제작했습니다.

Steam buildid는 `23110238`입니다. 게임 업데이트 후에는 일부 문자열이나 패치 경로가 맞지 않을 수 있습니다.

## 번역 견본

<table>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/74e8e2f9-6e89-4fbd-8f9a-e5e9ddd77e30" alt="Into the Radius 2 한국어 번역 패치 견본 1" width="640" height="360"></td>
    <td width="50%"><img src="https://github.com/user-attachments/assets/ca0a719a-5789-493e-80c0-ab7889ae8ec4" alt="Into the Radius 2 한국어 번역 패치 견본 2" width="640" height="360"></td>
  </tr>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/f826e7bd-7ccf-4850-8a81-d71f5c77f680" alt="Into the Radius 2 한국어 번역 패치 견본 3" width="640" height="360"></td>
    <td width="50%"><img src="https://github.com/user-attachments/assets/4fbf4ecd-bc79-465c-8d8c-ff428e9810be" alt="Into the Radius 2 한국어 번역 패치 견본 4" width="640" height="360"></td>
  </tr>
</table>

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

## 개발 문서

원본 게임 리소스 준비, 번역 대상 리소스, VR 테스트 드라이버, 패치 적용 원리는 [README.docs.md](README.docs.md)를 참고하세요.

## 참고한 모드

아래 모드와 글은 파일 구조, 설치 경로, 폰트 처리, 번역 범위 분석에 참고했습니다.

- Nexus Mods: [Japanese Translation Mod](https://www.nexusmods.com/intotheradius2/mods/145)
- Nexus Mods: [ITR2 Japanese Translation by Reindeer1899](https://www.nexusmods.com/intotheradius2/mods/211)
- Nexus Mods: [Russian for Into the Radius 2](https://www.nexusmods.com/intotheradius2/mods/144)
- Steam Community Guide: [Руссификатор](https://steamcommunity.com/sharedfiles/filedetails/?id=3657194872)
- Steam Discussion: [LOCALIZATION - MOD - DEV](https://steamcommunity.com/app/2307350/discussions/0/591783706468080541/)

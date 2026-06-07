# Into the Radius 2 Korean Patch

Community Korean translation build pipeline for Into the Radius 2.

## Contributor Flow

1. Edit `translations/records_with_ko.json` or `translations/unique_sources_with_ko.json`.
2. Open a PR.
3. CI validates JSON shape, placeholder preservation, and translation coverage.
4. After merge, the rolling release workflow rebuilds the patch from `raw/` inputs.

## Raw Inputs

Plain raw game files are not committed. The build script expects maintainer-only inputs under:

```text
raw/game/pakchunk0-Windows.pak
raw/references/japanese_entries.json
raw/prebuilt/pakchunk100-KO_NotoSansKRFonts_P.pak
raw/prebuilt/pakchunk999-Windows_P.pak
raw/prebuilt/pakchunk999-Windows_P.utoc
raw/prebuilt/pakchunk999-Windows_P.ucas
```

CI can either receive those files as plaintext under `raw/`, or decrypt `raw/private_inputs.tar.gpg` using the `RAW_PACK_PASSPHRASE` secret.

See `docs/raw-inputs.md` for details.

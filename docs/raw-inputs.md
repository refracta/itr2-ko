# Raw Input Layout

The CI build treats `raw/` as the canonical input directory. Other maintainers can use the same pipeline by copying their own files into this layout.

```text
raw/
  game/
    pakchunk0-Windows.pak
  references/
    japanese_entries.json
  prebuilt/
    pakchunk100-KO_NotoSansKRFonts_P.pak
    pakchunk999-Windows_P.pak
    pakchunk999-Windows_P.utoc
    pakchunk999-Windows_P.ucas
```

`pakchunk0-Windows.pak` is used only to read the original `Game.locres` and `Game.locmeta`.

`japanese_entries.json` is used as metadata for uasset-only `EnglishSource` keys added to the union locres patch.

The `prebuilt/` files are the current Korean font/UI font override assets. Translation-only PRs do not need to rebuild them.

## Encrypted Raw Bundle

To store raw inputs without committing plaintext files:

```bash
RAW_PACK_PASSPHRASE='long secret here' scripts/build/package_raw_inputs.sh
```

This creates:

```text
raw/private_inputs.tar.gpg
```

The archive contains uncompressed raw files under `raw/` after CI decrypts and extracts it.

Set this GitHub Actions secret:

```text
RAW_PACK_PASSPHRASE
```

The build workflow first checks for plaintext files in `raw/`. If they are missing and `raw/private_inputs.tar.gpg` exists, it decrypts that bundle.

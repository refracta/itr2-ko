#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${RAW_PACK_PASSPHRASE:-}" ]]; then
  echo "RAW_PACK_PASSPHRASE is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

for required in \
  raw/game/pakchunk0-Windows.pak \
  raw/base/EnglishSource.uasset.raw \
  raw/base/EnglishSource.locres_meta.json \
  raw/prebuilt/pakchunk100-KO_NotoSansKRFonts_P.pak \
  raw/prebuilt/pakchunk999-Windows_P.pak \
  raw/prebuilt/pakchunk999-Windows_P.utoc \
  raw/prebuilt/pakchunk999-Windows_P.ucas
do
  if [[ ! -f "$required" ]]; then
    echo "missing raw input: $required" >&2
    exit 1
  fi
done

tar -C raw -cf - game base prebuilt \
  | gpg --batch --yes --symmetric --cipher-algo AES256 \
      --passphrase "$RAW_PACK_PASSPHRASE" \
      -o raw/private_inputs.tar.gpg

echo "wrote raw/private_inputs.tar.gpg"

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import zipfile
import ctypes
from collections import Counter
from pathlib import Path

import pyuepak.entry as pyuepak_entry
from pyuepak import PakFile
from pyuepak.version import PakVersion


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"
DIST = ROOT / "dist"
RECORDS = ROOT / "translations" / "records_with_ko.json"
INSTALLER_DIR = ROOT / "scripts" / "install"

BASE_PAK_CANDIDATES = [
    RAW / "game" / "pakchunk0-Windows.pak",
    RAW / "pakchunk0-Windows.pak",
    RAW / "IntoTheRadius2" / "Content" / "Paks" / "pakchunk0-Windows.pak",
]
JAPANESE_ENTRIES_CANDIDATES = [
    RAW / "references" / "japanese_entries.json",
    RAW / "japanese_entries.json",
]

GAME_LOCRES_PATH = "IntoTheRadius2/Content/Localization/Game/en/Game.locres"
GAME_LOCMETA_PATH = "IntoTheRadius2/Content/Localization/Game/Game.locmeta"
MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")


def patch_pyuepak_oodle_nullable_args() -> None:
    """Work around pyuepak passing integer 0 where Linux Oodle expects NULL."""

    def fixed_decompress(data: bytes, output_size: int) -> bytes:
        lib = pyuepak_entry.oodle_comp.lib
        out_buffer = (ctypes.c_ubyte * output_size)()
        written = lib.OodleLZ_Decompress(
            data,
            len(data),
            out_buffer,
            output_size,
            1,
            1,
            0,
            None,
            0,
            None,
            None,
            None,
            0,
            3,
        )
        if written <= 0:
            raise RuntimeError("Oodle decompression failed")
        return bytes(out_buffer[:written])

    pyuepak_entry.oodle_comp.decompress = fixed_decompress


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("missing any of: " + ", ".join(str(p) for p in paths))


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_fstring(data: bytes, offset: int) -> tuple[str, int]:
    (length,) = struct.unpack_from("<i", data, offset)
    offset += 4
    if length == 0:
        return "", offset
    if length > 0:
        raw = data[offset : offset + length - 1]
        return raw.decode("utf-8", errors="replace"), offset + length
    units = -length
    raw = data[offset : offset + (units - 1) * 2]
    return raw.decode("utf-16le", errors="replace"), offset + units * 2


def write_fstring(text: str) -> bytes:
    if text == "":
        return struct.pack("<i", 0)
    try:
        raw = text.encode("ascii")
        return struct.pack("<i", len(raw) + 1) + raw + b"\0"
    except UnicodeEncodeError:
        raw = text.encode("utf-16le") + b"\0\0"
        return struct.pack("<i", -(len(raw) // 2)) + raw


def extract_pak_file(pak_path: Path, logical_path: str) -> bytes:
    pak = PakFile()
    pak.read(pak_path)
    entry = pak._index.entrys[logical_path]
    pak.reader.reopen()
    try:
        return entry.read_file(pak.reader, pak.version, pak.key)
    finally:
        pak.reader.close()


def parse_locres(data: bytes) -> tuple[list[dict], list[dict]]:
    if data[:16] != MAGIC:
        raise ValueError("unsupported locres magic")
    version = data[16]
    if version != 3:
        raise ValueError(f"unsupported locres version: {version}")
    offset = 17
    string_array_offset = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    offset += 4
    entry_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    namespace_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4

    namespace_infos = []
    entries = []
    for _ in range(namespace_count):
        ns_hash = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        namespace, offset = read_fstring(data, offset)
        ns_entry_count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        namespace_infos.append({"namespace": namespace, "hash": ns_hash})
        for _ in range(ns_entry_count):
            key_hash = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            key, offset = read_fstring(data, offset)
            source_hash = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            localized_index = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            entries.append(
                {
                    "namespace": namespace,
                    "key": key,
                    "key_hash": key_hash,
                    "source_hash": source_hash,
                    "localized_index": localized_index,
                }
            )

    offset = string_array_offset
    string_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    strings = []
    for _ in range(string_count):
        text, offset = read_fstring(data, offset)
        refs = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        strings.append({"text": text, "refs": refs})

    for entry in entries:
        idx = entry["localized_index"]
        entry["localized"] = strings[idx]["text"] if 0 <= idx < len(strings) else ""

    if len(entries) != entry_count:
        raise ValueError(f"entry count mismatch: parsed={len(entries)} declared={entry_count}")
    return namespace_infos, entries


def build_locres(namespaces: list[dict], entries: list[dict]) -> bytes:
    entries_by_ns: dict[str, list[dict]] = {ns["namespace"]: [] for ns in namespaces}
    for entry in entries:
        entries_by_ns.setdefault(entry["namespace"], []).append(entry)

    strings: list[str] = []
    string_index: dict[str, int] = {}
    for entry in entries:
        text = entry["ko"]
        if text not in string_index:
            string_index[text] = len(strings)
            strings.append(text)
        entry["localized_index"] = string_index[text]

    body = bytearray()
    body += MAGIC
    body += struct.pack("<B", 3)
    body += b"\0\0\0\0"
    body += struct.pack("<I", 0)
    body += struct.pack("<I", len(entries))
    body += struct.pack("<I", len(namespaces))

    for ns in namespaces:
        ns_entries = entries_by_ns.get(ns["namespace"], [])
        body += struct.pack("<I", ns["hash"])
        body += write_fstring(ns["namespace"])
        body += struct.pack("<I", len(ns_entries))
        for entry in ns_entries:
            body += struct.pack("<I", entry["key_hash"])
            body += write_fstring(entry["key"])
            body += struct.pack("<I", entry["source_hash"])
            body += struct.pack("<i", entry["localized_index"])

    string_array_offset = len(body)
    struct.pack_into("<I", body, 17, string_array_offset)

    refs = Counter(entry["localized_index"] for entry in entries)
    body += struct.pack("<I", len(strings))
    for idx, text in enumerate(strings):
        body += write_fstring(text)
        body += struct.pack("<i", refs[idx])
    return bytes(body)


def make_pak(name: str, locres: bytes, locmeta: bytes) -> Path:
    pak = PakFile()
    pak.version = PakVersion.V11
    pak.add_file(GAME_LOCRES_PATH, locres)
    pak.add_file(GAME_LOCMETA_PATH, locmeta)
    path = DIST / name
    pak.write(path)
    return path


def copy_prebuilt() -> list[Path]:
    copied = []
    prebuilt = RAW / "prebuilt"
    for name in [
        "pakchunk100-KO_NotoSansKRFonts_P.pak",
        "pakchunk999-Windows_P.pak",
        "pakchunk999-Windows_P.utoc",
        "pakchunk999-Windows_P.ucas",
    ]:
        src = prebuilt / name
        if src.exists():
            dst = DIST / name
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def write_release_readme() -> Path:
    path = DIST / "README_KO.txt"
    path.write_text(
        "\n".join(
            [
                "Into the Radius 2 한국어 패치",
                "",
                "설치 방법:",
                "1. ITR2_Korean.zip의 압축을 완전히 풉니다.",
                "2. install.bat를 실행합니다.",
                "3. 자동 설치가 실패하면 아래 파일들을 IntoTheRadius2/Content/Paks 폴더에 직접 복사합니다.",
                "",
                "복사할 파일:",
                "- pakchunk99-KO_LocresUnionPreserve_P.pak",
                "- pakchunk100-KO_NotoSansKRFonts_P.pak",
                "- pakchunk999-Windows_P.pak",
                "- pakchunk999-Windows_P.utoc",
                "- pakchunk999-Windows_P.ucas",
                "",
                "주의:",
                "- 기존의 pakchunk99-KO_UAsset-Windows.* 파일은 오래된 실험판입니다. install.ps1은 해당 파일이 있으면 비활성화합니다.",
                "- 게임을 실행 중이라면 종료한 뒤 설치하세요.",
                "- 설치 후에도 일부 이미지 표지판이나 하드코딩 UI 텍스트는 영어로 남을 수 있습니다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def copy_installer() -> list[Path]:
    files = []
    for name in ["install.bat", "install.ps1"]:
        src = INSTALLER_DIR / name
        dst = DIST / name
        shutil.copy2(src, dst)
        files.append(dst)
    return files


def main() -> None:
    patch_pyuepak_oodle_nullable_args()
    DIST.mkdir(parents=True, exist_ok=True)
    base_pak = first_existing(BASE_PAK_CANDIDATES)
    records = load_json(RECORDS)
    base_locres = extract_pak_file(base_pak, GAME_LOCRES_PATH)
    locmeta = extract_pak_file(base_pak, GAME_LOCMETA_PATH)
    namespaces, _ = parse_locres(base_locres)

    locres_records = [r for r in records if r["container"] == "Game.locres"]
    uasset_records = [r for r in records if r["container"] == "EnglishSource.uasset"]
    safe_entries = [
        {
            "namespace": r["namespace"],
            "key": r["key"],
            "key_hash": r["key_hash"],
            "source_hash": r["source_hash"],
            "ko": r.get("ko") or r["source"],
        }
        for r in locres_records
    ]

    ja_path = next((p for p in JAPANESE_ENTRIES_CANDIDATES if p.exists()), None)
    ja_es_meta = {}
    if ja_path:
        ja_entries = load_json(ja_path)
        ja_es_meta = {
            e["key"]: {"key_hash": e["key_hash"], "source_hash": e["source_hash"]}
            for e in ja_entries
            if e["namespace"] == "EnglishSource"
        }

    existing_es_keys = {e["key"] for e in safe_entries if e["namespace"] == "EnglishSource"}
    union_entries = list(safe_entries)
    skipped_without_meta = 0
    for r in uasset_records:
        if r["key"] in existing_es_keys:
            continue
        meta = ja_es_meta.get(r["key"])
        if not meta:
            skipped_without_meta += 1
            continue
        union_entries.append(
            {
                "namespace": "EnglishSource",
                "key": r["key"],
                "key_hash": meta["key_hash"],
                "source_hash": meta["source_hash"],
                "ko": r.get("ko") or r["source"],
            }
        )

    union_locres = build_locres(namespaces, union_entries)
    locres_path = DIST / "Game.ko.union-preserve-locres.locres"
    locres_path.write_bytes(union_locres)
    pak_path = make_pak("pakchunk99-KO_LocresUnionPreserve_P.pak", union_locres, locmeta)
    prebuilt_files = copy_prebuilt()

    readme = write_release_readme()
    installer_files = copy_installer()

    zip_path = DIST / "ITR2_Korean.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in [pak_path, *prebuilt_files, readme, *installer_files]:
            zf.write(path, path.name)

    summary = {
        "base_pak": str(base_pak),
        "locres_entries": len(locres_records),
        "uasset_records": len(uasset_records),
        "union_entries": len(union_entries),
        "uasset_only_added": len(union_entries) - len(safe_entries),
        "uasset_only_skipped_without_reference_meta": skipped_without_meta,
        "files": {
            path.name: {
                "size": path.stat().st_size,
                "sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
            }
            for path in [locres_path, pak_path, *prebuilt_files, readme, *installer_files, zip_path]
        },
    }
    (DIST / "build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

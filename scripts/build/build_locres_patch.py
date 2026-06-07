#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import zipfile
import ctypes
import zlib
from collections import Counter
from pathlib import Path

import cityhash
import pyuepak.entry as pyuepak_entry
from pyuepak import PakFile
from pyuepak.version import PakVersion


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"
DIST = ROOT / "dist"
RECORDS = ROOT / "translations" / "records_with_ko.json"
INSTALLER_DIR = ROOT / "scripts" / "install"
LOCRES_BASENAME = "pakchunk99-KO_Locres_P.pak"
ENGLISHSOURCE_BASENAME = "pakchunk99-KO_UAsset-Windows"
COMPAT_GAME_VERSION = "v1.0.6 rev 44918"
EXPORT_SERIAL_SIZE_OFFSET = 0xD0
FIRST_FSTRING_RELATIVE_OFFSET = 2
AES_ALIGNMENT = 16
IOSTORE_BLOCK_SIZE = 65536

BASE_PAK_CANDIDATES = [
    RAW / "game" / "pakchunk0-Windows.pak",
    RAW / "pakchunk0-Windows.pak",
    RAW / "IntoTheRadius2" / "Content" / "Paks" / "pakchunk0-Windows.pak",
]
BASE_ENGLISHSOURCE_CANDIDATES = [
    RAW / "base" / "EnglishSource.uasset.raw",
    RAW / "base_EnglishSource.uasset.raw",
]
ENGLISHSOURCE_LOCRES_META_CANDIDATES = [
    RAW / "base" / "EnglishSource.locres_meta.json",
    RAW / "base_EnglishSource.locres_meta.json",
]

GAME_LOCRES_PATH = "IntoTheRadius2/Content/Localization/Game/en/Game.locres"
GAME_LOCMETA_PATH = "IntoTheRadius2/Content/Localization/Game/Game.locmeta"
MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")
PROJECTC_IOSTORE_HEADER = bytes.fromhex(
    "2d3d3d2d2d3d3d2d2d3d3d2d2d3d3d2d08000000900000000200000006000000"
    "0c0000000100000020000000000001008100000001000000a695fe34ff106667"
    "000000000000000000000000000000000900000001000000ffffffffffffffff"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000"
)
PROJECTC_CHUNK_IDS = bytes.fromhex("de7d8cef4d05444100000001a695fe34ff10666700000006")
PROJECTC_EXTRA = struct.pack("<I", 2)
PROJECTC_METHODS = b"Oodle" + b"\0" * 27
PROJECTC_ENTRY1_PAYLOAD = bytes.fromhex(
    "6e436f4904000000a695fe34ff10666701000000de7d8cef4d054441"
    "10000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000"
)
PROJECTC_COMPANION_PAK = bytes.fromhex(
    "020000002f00000000007d82ab1b00000000010000006a000000000000000800"
    "00000000000005fe405753166f125559e7c9ac558654f107c7e9010000007200"
    "00000000000004000000000000009069ca78e7450a285173431b3e52c5c25299"
    "e473000000000000000000000000000000000000000000000000000000000000"
    "00000000000000e1126f5a0b00000000000000000000006a00000000000000e4"
    "faadb5b628ab73599320225bfd6a7f2364666000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000000000"
)

EXTRA_ENGLISHSOURCE_LOCRES_ENTRIES = [
    {
        "key": "41C7E447418490718B2CE78EFFFAE0D7",
        "source": "Start new game",
        "ko": "새 게임 시작",
    },
    {
        "key": "CC36858D44605D96DB012A8B5292C316",
        "source": "Starting a new game will delete all Single-player saves. Are you sure?",
        "ko": "새 게임을 시작하면 모든 싱글플레이어 저장 데이터가 삭제됩니다. 계속하시겠습니까?",
    },
    {
        "key": "A837DF4B4E68A3C81400B5BCE7986796",
        "source": "Yes",
        "ko": "예",
    },
    {
        "key": "1368F6664F6161BA319FDDABB666CEB8",
        "source": "No",
        "ko": "아니요",
    },
    {
        "key": "F3F66CB94CDD9B0AE45F8B92100FAB71",
        "source": "Measurement",
        "ko": "단위",
    },
    {
        "key": "48FEA94B43498BA0086D6BACDDABA292",
        "source": "Metric",
        "ko": "미터법",
    },
    {
        "key": "0185BCCD483EDA65844454AC76A01419",
        "source": "Imperial",
        "ko": "야드파운드법",
    },
    {
        "key": "D20537AC41AB1CF99AD596893398A711",
        "source": "Off",
        "ko": "끄기",
    },
    {
        "key": "0D9E1FDA4C51A50B250D1EA0CA569138",
        "source": "On",
        "ko": "켜기",
    },
]


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


def load_optional_json(path_candidates: list[Path]):
    for path in path_candidates:
        if path.exists():
            return load_json(path)
    raise FileNotFoundError("missing any of: " + ", ".join(str(p) for p in path_candidates))


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


def source_hash(text: str) -> int:
    return zlib.crc32(text.encode("utf-32le")) & 0xFFFFFFFF


def text_key_hash(text: str) -> int:
    if text == "":
        return 0
    hashed = cityhash.CityHash64(text.encode("utf-16le"))
    return ((hashed & 0xFFFFFFFF) + (((hashed >> 32) & 0xFFFFFFFF) * 23)) & 0xFFFFFFFF


def align(value: int, alignment: int = AES_ALIGNMENT) -> int:
    return (value + alignment - 1) // alignment * alignment


def pack_offset_length(offset: int, length: int) -> bytes:
    if offset >= 1 << 40 or length >= 1 << 40:
        raise ValueError("IoStore offset/length exceeds 40-bit field")
    return offset.to_bytes(5, "big") + length.to_bytes(5, "big")


def pack_block(physical_offset: int, compressed_size: int, uncompressed_size: int, method: int) -> bytes:
    if physical_offset >= 1 << 40:
        raise ValueError("IoStore physical offset exceeds 40-bit field")
    if compressed_size >= 1 << 24 or uncompressed_size >= 1 << 24:
        raise ValueError("IoStore block size exceeds 24-bit field")
    return (
        physical_offset.to_bytes(5, "little")
        + compressed_size.to_bytes(3, "little")
        + uncompressed_size.to_bytes(3, "little")
        + bytes([method])
    )


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


def parse_template_utoc_layout(utoc: bytes) -> dict[str, int]:
    header_size = struct.unpack_from("<I", utoc, 0x14)[0]
    entry_count = struct.unpack_from("<I", utoc, 0x18)[0]
    block_count = struct.unpack_from("<I", utoc, 0x1C)[0]
    block_entry_size = struct.unpack_from("<I", utoc, 0x20)[0]
    method_count = struct.unpack_from("<I", utoc, 0x24)[0]
    method_name_len = struct.unpack_from("<I", utoc, 0x28)[0]
    block_size = struct.unpack_from("<I", utoc, 0x2C)[0]
    directory_size = struct.unpack_from("<I", utoc, 0x30)[0]

    chunk_ids_start = header_size
    chunk_ids_size = entry_count * 12
    offset_lengths_start = chunk_ids_start + chunk_ids_size
    offset_lengths_size = entry_count * 10
    extra_start = offset_lengths_start + offset_lengths_size
    extra_size = 4
    block_table_start = extra_start + extra_size
    method_table_start = block_table_start + block_count * block_entry_size
    method_table_size = method_count * method_name_len
    directory_start = method_table_start + method_table_size
    meta_start = directory_start + directory_size

    return {
        "header_size": header_size,
        "entry_count": entry_count,
        "block_count": block_count,
        "block_entry_size": block_entry_size,
        "method_count": method_count,
        "method_name_len": method_name_len,
        "block_size": block_size,
        "directory_size": directory_size,
        "chunk_ids_start": chunk_ids_start,
        "chunk_ids_size": chunk_ids_size,
        "offset_lengths_start": offset_lengths_start,
        "extra_start": extra_start,
        "extra_size": extra_size,
        "block_table_start": block_table_start,
        "method_table_start": method_table_start,
        "method_table_size": method_table_size,
        "directory_start": directory_start,
        "meta_start": meta_start,
    }


def read_iostore_offset_length(utoc: bytes, offset: int) -> tuple[int, int]:
    raw = utoc[offset : offset + 10]
    return int.from_bytes(raw[:5], "big"), int.from_bytes(raw[5:], "big")


def read_iostore_entry(utoc: bytes, ucas: bytes, entry_index: int) -> bytes:
    layout = parse_template_utoc_layout(utoc)
    block_size = layout["block_size"]
    offset_length_offset = layout["offset_lengths_start"] + entry_index * 10
    logical_offset, logical_length = read_iostore_offset_length(utoc, offset_length_offset)
    first_block = logical_offset // block_size
    last_block = (align(logical_offset + logical_length, block_size) - 1) // block_size
    offset_in_block = logical_offset % block_size
    remaining = logical_length
    output = bytearray()
    for block_index in range(first_block, last_block + 1):
        block_offset = layout["block_table_start"] + block_index * layout["block_entry_size"]
        block = utoc[block_offset : block_offset + layout["block_entry_size"]]
        physical_offset = int.from_bytes(block[:5], "little")
        compressed_size = int.from_bytes(block[5:8], "little")
        uncompressed_size = int.from_bytes(block[8:11], "little")
        method = block[11]
        if method != 0:
            raise RuntimeError("roundtrip reader only supports uncompressed blocks")
        src = ucas[physical_offset : physical_offset + compressed_size]
        if len(src) != uncompressed_size:
            raise RuntimeError("uncompressed block size mismatch")
        take = min(block_size - offset_in_block, remaining)
        output += src[offset_in_block : offset_in_block + take]
        remaining -= take
        offset_in_block = 0
    return bytes(output)


def patch_englishsource_uasset(records: list[dict]) -> tuple[bytes, dict]:
    raw_path = first_existing(BASE_ENGLISHSOURCE_CANDIDATES)
    raw = bytearray(raw_path.read_bytes())
    uasset_records = sorted(
        (r for r in records if r["container"] == "EnglishSource.uasset"),
        key=lambda r: r["text_offset"],
    )
    if not uasset_records:
        raise RuntimeError("no EnglishSource.uasset records found")

    for record in uasset_records:
        parsed, end = read_fstring(raw, record["text_offset"])
        if parsed != record["source"] or end != record["end"]:
            raise RuntimeError(
                "EnglishSource raw does not match translation offsets: "
                f"{record['key']} parsed={parsed!r} expected={record['source']!r}"
            )

    original_serial_size = struct.unpack_from("<Q", raw, EXPORT_SERIAL_SIZE_OFFSET)[0]
    serial_start = len(raw) - original_serial_size
    rebuilt = bytearray()
    cursor = 0
    encoded_sizes = []
    translated_count = 0

    for record in uasset_records:
        text = record.get("ko") or record["source"]
        rebuilt += raw[cursor : record["text_offset"]]
        encoded = write_fstring(text)
        rebuilt += encoded
        cursor = record["end"]
        encoded_sizes.append(len(encoded))
        if text != record["source"]:
            translated_count += 1
    rebuilt += raw[cursor:]

    new_serial_size = len(rebuilt) - serial_start
    struct.pack_into("<Q", rebuilt, EXPORT_SERIAL_SIZE_OFFSET, new_serial_size)

    namespace_offset = serial_start + FIRST_FSTRING_RELATIVE_OFFSET
    namespace, offset = read_fstring(rebuilt, namespace_offset)
    (entry_count,) = struct.unpack_from("<i", rebuilt, offset)
    offset += 4
    parsed_translations = {}
    for _ in range(entry_count):
        key, offset = read_fstring(rebuilt, offset)
        text, offset = read_fstring(rebuilt, offset)
        parsed_translations[key] = text

    expected = {r["key"]: r.get("ko") or r["source"] for r in uasset_records}
    mismatches = [key for key, text in expected.items() if parsed_translations.get(key) != text]
    if namespace != "EnglishSource" or entry_count != len(uasset_records) or mismatches:
        raise RuntimeError(
            "patched EnglishSource parse check failed: "
            f"namespace={namespace!r}, entry_count={entry_count}, mismatches={len(mismatches)}"
        )

    return bytes(rebuilt), {
        "input": str(raw_path),
        "uasset_entries": len(uasset_records),
        "translated_or_changed_entries": translated_count,
        "original_size": len(raw),
        "patched_size": len(rebuilt),
        "original_serial_size": original_serial_size,
        "patched_serial_size": new_serial_size,
        "sha1": hashlib.sha1(rebuilt).hexdigest(),
        "encoded_fstring_bytes": {
            "min": min(encoded_sizes),
            "max": max(encoded_sizes),
            "sum": sum(encoded_sizes),
        },
    }


def build_projectc_directory() -> bytes:
    # The game resolves this package through the original Projectc mount point.
    # Retoc-generated IntoTheRadius2 mount paths build cleanly but do not override
    # the runtime asset.
    body = bytearray()
    body += write_fstring("../../../Projectc/Content/ITR2/Configurations/Localization/")
    body += struct.pack("<i", 1)
    body += struct.pack("<IIII", 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0)
    body += struct.pack("<i", 1)
    body += struct.pack("<III", 0, 0xFFFFFFFF, 0)
    body += struct.pack("<i", 1)
    body += write_fstring("EnglishSource.uasset")
    return bytes(body)


def build_englishsource_iostore(patched_uasset: bytes) -> tuple[list[Path], dict]:
    block_size = IOSTORE_BLOCK_SIZE
    entry0_length = len(patched_uasset)
    entry0_blocks = max(1, math.ceil(entry0_length / block_size))
    entry1_offset = entry0_blocks * block_size
    entry1_payload = PROJECTC_ENTRY1_PAYLOAD
    entry1_length = len(entry1_payload)
    block_entries = []
    ucas = bytearray()

    for block_index in range(entry0_blocks):
        block = patched_uasset[block_index * block_size : (block_index + 1) * block_size]
        physical_offset = len(ucas)
        ucas += block
        ucas += b"\0" * (align(len(ucas)) - len(ucas))
        block_entries.append(pack_block(physical_offset, len(block), len(block), 0))

    physical_offset = len(ucas)
    ucas += entry1_payload
    ucas += b"\0" * (align(len(ucas)) - len(ucas))
    block_entries.append(pack_block(physical_offset, entry1_length, entry1_length, 0))

    header = bytearray(PROJECTC_IOSTORE_HEADER)
    struct.pack_into("<I", header, 0x1C, len(block_entries))
    directory = build_projectc_directory()
    struct.pack_into("<I", header, 0x30, len(directory))
    offset_lengths = pack_offset_length(0, entry0_length) + pack_offset_length(entry1_offset, entry1_length)
    meta = (
        hashlib.sha1(patched_uasset).digest()
        + b"\0\0\0\0"
        + hashlib.sha1(entry1_payload).digest()
        + b"\0\0\0\0"
    )

    new_utoc = (
        bytes(header)
        + PROJECTC_CHUNK_IDS
        + offset_lengths
        + PROJECTC_EXTRA
        + b"".join(block_entries)
        + PROJECTC_METHODS
        + directory
        + meta
    )
    pak_out = DIST / f"{ENGLISHSOURCE_BASENAME}.pak"
    utoc_out = DIST / f"{ENGLISHSOURCE_BASENAME}.utoc"
    ucas_out = DIST / f"{ENGLISHSOURCE_BASENAME}.ucas"
    pak_out.write_bytes(PROJECTC_COMPANION_PAK)
    utoc_out.write_bytes(new_utoc)
    ucas_out.write_bytes(bytes(ucas))

    roundtrip = read_iostore_entry(utoc_out.read_bytes(), ucas_out.read_bytes(), entry_index=0)
    if roundtrip != patched_uasset:
        raise RuntimeError("EnglishSource IoStore roundtrip validation failed")

    files = [pak_out, utoc_out, ucas_out]
    return files, {
        "basename": ENGLISHSOURCE_BASENAME,
        "mount": "../../../Projectc/Content/ITR2/Configurations/Localization/",
        "entry0_length": entry0_length,
        "entry1_length": entry1_length,
        "entry0_blocks": entry0_blocks,
        "block_count": len(block_entries),
        "files": {
            path.name: {
                "size": path.stat().st_size,
                "sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
            }
            for path in files
        },
    }


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
                "Into the Radius 2 한국어 번역 패치",
                "",
                "커뮤니티 한국어 번역 패치입니다.",
                f"Into the Radius 2 {COMPAT_GAME_VERSION} 버전 기준입니다.",
                "",
                "설치 방법:",
                "1. ITR2_Korean.zip의 압축을 완전히 풉니다.",
                "2. install.bat를 실행합니다.",
                "3. 자동 설치가 실패하면 아래 파일들을 IntoTheRadius2/Content/Paks 폴더에 직접 복사합니다.",
                "",
                "복사할 파일:",
                "- pakchunk99-KO_Locres_P.pak",
                "- pakchunk99-KO_UAsset-Windows.pak",
                "- pakchunk99-KO_UAsset-Windows.utoc",
                "- pakchunk99-KO_UAsset-Windows.ucas",
                "- pakchunk100-KO_NotoSansKRFonts_P.pak",
                "- pakchunk999-Windows_P.pak",
                "- pakchunk999-Windows_P.utoc",
                "- pakchunk999-Windows_P.ucas",
                "",
                "주의:",
                "- 기존의 pakchunk99-KO_LocresUnionPreserve_P.pak 및 pakchunk98-KO_EnglishSource-Windows_P.* 파일은 오래된 실험판입니다. install.ps1은 해당 파일이 있으면 비활성화합니다.",
                "- 게임을 실행 중이라면 종료한 뒤 설치하세요.",
                "- 설치 후에도 일부 이미지 표지판이나 진짜 하드코딩 UI 텍스트는 영어로 남을 수 있습니다.",
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
    englishsource_locres_meta = load_optional_json(ENGLISHSOURCE_LOCRES_META_CANDIDATES)
    union_entries_by_ns_key = {(entry["namespace"], entry["key"]): entry for entry in safe_entries}
    uasset_only_added = 0
    uasset_collision_overridden = 0
    uasset_placeholder_preserved = 0
    missing_locres_meta = []
    for record in uasset_records:
        entry_key = ("EnglishSource", record["key"])
        if record["source"] == "Placeholder text":
            uasset_placeholder_preserved += int(entry_key in union_entries_by_ns_key)
            continue
        meta = englishsource_locres_meta.get(record["key"])
        if not meta:
            missing_locres_meta.append(record["key"])
            continue
        uasset_entry = {
            "namespace": "EnglishSource",
            "key": record["key"],
            "key_hash": meta["key_hash"],
            "source_hash": source_hash(record["source"]),
            "ko": record.get("ko") or record["source"],
        }
        if entry_key in union_entries_by_ns_key:
            uasset_collision_overridden += 1
        else:
            uasset_only_added += 1
        union_entries_by_ns_key[entry_key] = uasset_entry
    if missing_locres_meta:
        raise RuntimeError(f"missing EnglishSource locres metadata entries: {len(missing_locres_meta)}")

    for extra in EXTRA_ENGLISHSOURCE_LOCRES_ENTRIES:
        entry_key = ("EnglishSource", extra["key"])
        if entry_key not in union_entries_by_ns_key:
            uasset_only_added += 1
        else:
            uasset_collision_overridden += 1
        union_entries_by_ns_key[entry_key] = {
            "namespace": "EnglishSource",
            "key": extra["key"],
            "key_hash": text_key_hash(extra["key"]),
            "source_hash": source_hash(extra["source"]),
            "ko": extra["ko"],
        }

    union_entries = list(union_entries_by_ns_key.values())
    locres = build_locres(namespaces, union_entries)
    locres_path = DIST / "Game.ko.locres"
    locres_path.write_bytes(locres)
    pak_path = make_pak(LOCRES_BASENAME, locres, locmeta)
    patched_uasset, uasset_summary = patch_englishsource_uasset(records)
    patched_uasset_path = DIST / "EnglishSource.ko.uasset.raw"
    patched_uasset_path.write_bytes(patched_uasset)
    englishsource_files, englishsource_summary = build_englishsource_iostore(patched_uasset)
    prebuilt_files = copy_prebuilt()

    readme = write_release_readme()
    installer_files = copy_installer()

    zip_path = DIST / "ITR2_Korean.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in [pak_path, *englishsource_files, *prebuilt_files, readme, *installer_files]:
            zf.write(path, path.name)

    summary = {
        "base_pak": str(base_pak),
        "locres_entries": len(locres_records),
        "uasset_records": len(uasset_records),
        "locres_entries_built": len(union_entries),
        "locres_uasset_only_added": uasset_only_added,
        "locres_uasset_collision_overridden": uasset_collision_overridden,
        "locres_uasset_placeholder_preserved": uasset_placeholder_preserved,
        "englishsource_strategy": "direct-uasset-iostore",
        "englishsource_uasset": uasset_summary,
        "englishsource_iostore": englishsource_summary,
        "files": {
            path.name: {
                "size": path.stat().st_size,
                "sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
            }
            for path in [
                locres_path,
                pak_path,
                patched_uasset_path,
                *englishsource_files,
                *prebuilt_files,
                readme,
                *installer_files,
                zip_path,
            ]
        },
    }
    (DIST / "build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

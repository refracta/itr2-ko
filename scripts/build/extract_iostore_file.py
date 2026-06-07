#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import math
import struct
from pathlib import Path

from pyuepak.oodle import oodle

from list_iostore_directory import parse_directory_index, read_fstring


def align(value: int, alignment: int = 16) -> int:
    return (value + alignment - 1) // alignment * alignment


def parse_layout(utoc: bytes) -> dict[str, int]:
    header_size = struct.unpack_from("<I", utoc, 0x14)[0]
    entry_count = struct.unpack_from("<I", utoc, 0x18)[0]
    block_count = struct.unpack_from("<I", utoc, 0x1C)[0]
    block_entry_size = struct.unpack_from("<I", utoc, 0x20)[0]
    method_count = struct.unpack_from("<I", utoc, 0x24)[0]
    method_name_len = struct.unpack_from("<I", utoc, 0x28)[0]
    block_size = struct.unpack_from("<I", utoc, 0x2C)[0]
    directory_size = struct.unpack_from("<I", utoc, 0x30)[0]

    chunk_ids_start = header_size
    offset_lengths_start = chunk_ids_start + entry_count * 12
    offset_lengths_size = entry_count * 10
    extra_start = offset_lengths_start + offset_lengths_size

    directory_start = -1
    if directory_size:
        mount_pos = utoc.find(b"../../../", extra_start)
        if mount_pos >= 4:
            declared_len = struct.unpack_from("<i", utoc, mount_pos - 4)[0]
            if declared_len > 0 and declared_len < 512:
                directory_start = mount_pos - 4
    if directory_start < 0:
        method_table_start = extra_start + block_count * block_entry_size
        directory_start = method_table_start + method_count * method_name_len
    method_table_start = directory_start - method_count * method_name_len
    block_table_start = method_table_start - block_count * block_entry_size

    return {
        "entry_count": entry_count,
        "block_count": block_count,
        "block_entry_size": block_entry_size,
        "method_count": method_count,
        "method_name_len": method_name_len,
        "block_size": block_size,
        "directory_size": directory_size,
        "chunk_ids_start": chunk_ids_start,
        "offset_lengths_start": offset_lengths_start,
        "offset_lengths_size": offset_lengths_size,
        "extra_start": extra_start,
        "block_table_start": block_table_start,
        "method_table_start": method_table_start,
        "directory_start": directory_start,
    }


def read_offset_length(raw: bytes) -> tuple[int, int]:
    return int.from_bytes(raw[:5], "big"), int.from_bytes(raw[5:10], "big")


def oodle_decompress(data: bytes, output_size: int) -> bytes:
    # pyuepak's Oodle wrapper currently passes integer zeroes for nullable
    # pointer arguments. The Linux Oodle 2.9.10 library expects NULL pointers
    # here; passing 0 makes valid streams fail to decompress.
    lib = oodle().lib
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
    if written != output_size:
        raise RuntimeError(f"Oodle decompression failed: wrote {written}, expected {output_size}")
    return bytes(out_buffer)


def parse_directory_with_userdata(buffer: bytes) -> tuple[str, dict[str, int]]:
    mount, offset = read_fstring(buffer, 0)

    (dir_count,) = struct.unpack_from("<i", buffer, offset)
    offset += 4
    dirs = [struct.unpack_from("<IIII", buffer, offset + i * 16) for i in range(dir_count)]
    offset += dir_count * 16

    (file_count,) = struct.unpack_from("<i", buffer, offset)
    offset += 4
    files = [struct.unpack_from("<III", buffer, offset + i * 12) for i in range(file_count)]
    offset += file_count * 12

    (string_count,) = struct.unpack_from("<i", buffer, offset)
    offset += 4
    strings = []
    for _ in range(string_count):
        value, offset = read_fstring(buffer, offset)
        strings.append(value)

    def name(idx: int) -> str:
        if idx == 0xFFFFFFFF:
            return ""
        return strings[idx]

    paths: dict[str, int] = {}

    def walk(dir_index: int, prefix: str) -> None:
        while dir_index != 0xFFFFFFFF:
            dir_name_idx, first_child, next_sibling, first_file = dirs[dir_index]
            dir_name = name(dir_name_idx)
            current_prefix = prefix + (dir_name + "/" if dir_name else "")
            file_index = first_file
            while file_index != 0xFFFFFFFF:
                file_name_idx, next_file, user_data = files[file_index]
                paths[mount + current_prefix + name(file_name_idx)] = user_data
                file_index = next_file
            if first_child != 0xFFFFFFFF:
                walk(first_child, current_prefix)
            dir_index = next_sibling

    if dirs:
        walk(0, "")
    return mount, paths


def read_iostore_entry(utoc: bytes, ucas_path: Path, entry_index: int) -> bytes:
    layout = parse_layout(utoc)
    block_size = layout["block_size"]
    off = layout["offset_lengths_start"] + entry_index * 10
    logical_offset, logical_length = read_offset_length(utoc[off : off + 10])
    first_block = logical_offset // block_size
    last_block = (math.ceil((logical_offset + logical_length) / block_size) * block_size - 1) // block_size
    offset_in_block = logical_offset % block_size
    remaining = logical_length

    methods = []
    method_table_start = layout["method_table_start"]
    for i in range(layout["method_count"]):
        start = method_table_start + i * layout["method_name_len"]
        method = utoc[start : start + layout["method_name_len"]].split(b"\x00", 1)[0].decode("utf-8")
        methods.append(method)

    output = bytearray()
    with ucas_path.open("rb") as f:
        for block_index in range(first_block, last_block + 1):
            boff = layout["block_table_start"] + block_index * layout["block_entry_size"]
            block = utoc[boff : boff + layout["block_entry_size"]]
            physical_offset = int.from_bytes(block[:5], "little")
            compressed_size = int.from_bytes(block[5:8], "little")
            uncompressed_size = int.from_bytes(block[8:11], "little")
            method_idx = block[11]
            f.seek(physical_offset)
            aligned_payload = f.read(align(compressed_size))
            payload = aligned_payload[:compressed_size]
            if method_idx == 0:
                decompressed = payload
            else:
                method = methods[method_idx - 1]
                if method != "Oodle":
                    raise RuntimeError(f"unsupported compression method {method!r}")
                decompressed = oodle_decompress(payload, uncompressed_size)
            take = min(block_size - offset_in_block, remaining)
            output += decompressed[offset_in_block : offset_in_block + take]
            remaining -= take
            offset_in_block = 0
    return bytes(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("utoc", type=Path)
    parser.add_argument("ucas", type=Path)
    parser.add_argument("path")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    utoc = args.utoc.read_bytes()
    layout = parse_layout(utoc)
    directory = utoc[
        layout["directory_start"] : layout["directory_start"] + layout["directory_size"]
    ]
    _, mapping = parse_directory_with_userdata(directory)
    wanted = args.path
    candidates = [wanted]
    if not wanted.startswith("../../../"):
        candidates.append("../../../" + wanted.lstrip("/"))
    entry_index = None
    for candidate in candidates:
        if candidate in mapping:
            entry_index = mapping[candidate]
            break
    if entry_index is None:
        lower = wanted.lower()
        matches = [p for p in mapping if lower in p.lower()]
        raise SystemExit(f"path not found. matches={matches[:20]}")
    data = read_iostore_entry(utoc, args.ucas, entry_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"{entry_index} {len(data)} {args.output}")


if __name__ == "__main__":
    main()

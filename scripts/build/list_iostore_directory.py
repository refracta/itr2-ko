#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
from pathlib import Path


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


def parse_layout(utoc: bytes) -> dict[str, int]:
    header_size = struct.unpack_from("<I", utoc, 0x14)[0]
    entry_count = struct.unpack_from("<I", utoc, 0x18)[0]
    block_count = struct.unpack_from("<I", utoc, 0x1C)[0]
    block_entry_size = struct.unpack_from("<I", utoc, 0x20)[0]
    method_count = struct.unpack_from("<I", utoc, 0x24)[0]
    method_name_len = struct.unpack_from("<I", utoc, 0x28)[0]
    directory_size = struct.unpack_from("<I", utoc, 0x30)[0]

    chunk_ids_start = header_size
    offset_lengths_start = chunk_ids_start + entry_count * 12
    extra_start = offset_lengths_start + entry_count * 10

    # UE5.4+ version 8 has a 4-byte perfect-hash seed/index chunk before block entries.
    extra_size = 4
    block_table_start = extra_start + extra_size
    method_table_start = block_table_start + block_count * block_entry_size
    directory_start = method_table_start + method_count * method_name_len
    # Version 8 containers can include an additional perfect-hash/index table
    # before the directory index. The header does not expose its size in the
    # same layout used by older pyueparse builds, so locate the mount point
    # FString directly when present.
    if directory_size:
        mount_pos = utoc.find(b"../../../", max(0, directory_start - 16))
        if mount_pos == -1:
            mount_pos = utoc.find(b"../../../")
        if mount_pos >= 4:
            declared_len = struct.unpack_from("<i", utoc, mount_pos - 4)[0]
            if declared_len > 0 and declared_len < 512:
                directory_start = mount_pos - 4
    return {
        "entry_count": entry_count,
        "directory_start": directory_start,
        "directory_size": directory_size,
    }


def read_tarray(data: bytes, offset: int, item_size: int) -> tuple[list[bytes], int]:
    (count,) = struct.unpack_from("<i", data, offset)
    offset += 4
    items = [data[offset + i * item_size : offset + (i + 1) * item_size] for i in range(count)]
    return items, offset + count * item_size


def parse_directory_index(buffer: bytes) -> tuple[str, list[str]]:
    mount, offset = read_fstring(buffer, 0)
    dirs_raw, offset = read_tarray(buffer, offset, 16)
    files_raw, offset = read_tarray(buffer, offset, 12)
    (string_count,) = struct.unpack_from("<i", buffer, offset)
    offset += 4
    strings = []
    for _ in range(string_count):
        value, offset = read_fstring(buffer, offset)
        strings.append(value)

    dirs = [struct.unpack("<IIII", item) for item in dirs_raw]
    files = [struct.unpack("<III", item) for item in files_raw]

    paths: list[str] = []

    def name(idx: int) -> str:
        if idx == 0xFFFFFFFF:
            return ""
        if 0 <= idx < len(strings):
            return strings[idx]
        return f"<bad-string-{idx}>"

    def walk(dir_index: int, prefix: str) -> None:
        while dir_index != 0xFFFFFFFF:
            dir_name_idx, first_child, next_sibling, first_file = dirs[dir_index]
            dir_name = name(dir_name_idx)
            current_prefix = prefix + (dir_name + "/" if dir_name else "")

            file_index = first_file
            while file_index != 0xFFFFFFFF:
                file_name_idx, next_file, user_data = files[file_index]
                paths.append(current_prefix + name(file_name_idx))
                file_index = next_file

            if first_child != 0xFFFFFFFF:
                walk(first_child, current_prefix)
            dir_index = next_sibling

    if dirs:
        walk(0, "")
    return mount, paths


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: list_iostore_directory.py <file.utoc> [filter...]")
    path = Path(sys.argv[1])
    filters = [f.lower() for f in sys.argv[2:]]
    utoc = path.read_bytes()
    layout = parse_layout(utoc)
    start = layout["directory_start"]
    end = start + layout["directory_size"]
    mount, paths = parse_directory_index(utoc[start:end])
    for p in paths:
        full = mount + p
        if not filters or any(f in full.lower() for f in filters):
            print(full)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / "translations" / "records_with_ko.json"
UNIQUE = ROOT / "translations" / "unique_sources_with_ko.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def source_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def placeholders(text: str) -> set[str]:
    pattern = r"\{[^{}]+\}|<[^<>/]+>|</[^<>]+>|\[[A-Za-z0-9_]+\]|#[A-Za-z0-9_]+"
    return set(re.findall(pattern, text or ""))


def main() -> int:
    errors: list[str] = []
    records = load_json(RECORDS)
    unique = load_json(UNIQUE)

    if not isinstance(records, list) or not isinstance(unique, list):
        errors.append("records_with_ko.json and unique_sources_with_ko.json must be JSON arrays")
    else:
        unique_by_id = {}
        for item in unique:
            sid = item.get("source_id")
            if not sid:
                errors.append("unique source missing source_id")
                continue
            if sid in unique_by_id:
                errors.append(f"duplicate unique source_id: {sid}")
            unique_by_id[sid] = item
            if source_id(item.get("source", "")) != sid:
                errors.append(f"source_id mismatch in unique source: {sid}")
            if item.get("translatable") and not item.get("ko"):
                errors.append(f"missing ko for translatable unique source: {sid}")
            if item.get("ko") is not None:
                missing = placeholders(item.get("source", "")) - placeholders(item.get("ko", ""))
                if missing:
                    errors.append(f"placeholder missing in unique source {sid}: {sorted(missing)}")

        record_ids = set()
        for record in records:
            rid = record.get("record_id")
            if not rid:
                errors.append("record missing record_id")
                continue
            if rid in record_ids:
                errors.append(f"duplicate record_id: {rid}")
            record_ids.add(rid)

            sid = record.get("source_id")
            if sid not in unique_by_id:
                errors.append(f"record references missing source_id: {rid} -> {sid}")
            if source_id(record.get("source", "")) != sid:
                errors.append(f"source_id mismatch in record: {rid}")
            if record.get("ko") is None:
                errors.append(f"record missing ko: {rid}")
            missing = placeholders(record.get("source", "")) - placeholders(record.get("ko", ""))
            if missing:
                errors.append(f"placeholder missing in record {rid}: {sorted(missing)}")

    summary = {
        "records": len(records) if isinstance(records, list) else None,
        "unique_sources": len(unique) if isinstance(unique, list) else None,
        "errors": len(errors),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        for error in errors[:100]:
            print(f"ERROR: {error}", file=sys.stderr)
        if len(errors) > 100:
            print(f"ERROR: ... {len(errors) - 100} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

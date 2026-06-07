#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "translations" / "records_with_ko.json"
UNIQUE = ROOT / "translations" / "unique_sources_with_ko.json"
MARKER = "ITR2_KO_TRANSLATION_PROPOSAL_V1"
MAX_CHANGES = 250
MAX_KO_CHARS = 12000


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def placeholders(text: str) -> set[str]:
    pattern = r"\{[^{}]+\}|<[^<>/]+>|</[^<>]+>|\[[A-Za-z0-9_]+\]|#[A-Za-z0-9_]+"
    return set(re.findall(pattern, text or ""))


def extract_proposal_from_issue_body(body: str) -> dict:
    marker_pos = body.find(MARKER)
    if marker_pos < 0:
        raise ValueError(f"missing marker: {MARKER}")
    after_marker = body[marker_pos + len(MARKER) :]
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", after_marker, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("missing fenced JSON block after proposal marker")
    return json.loads(match.group(1))


def load_proposal(args: argparse.Namespace) -> dict:
    if args.proposal:
        return load_json(args.proposal)
    if args.issue_body:
        return extract_proposal_from_issue_body(args.issue_body.read_text(encoding="utf-8"))
    raise ValueError("either --proposal or --issue-body is required")


def validate_change(change: dict, unique_by_id: dict[str, dict], seen: set[str]) -> tuple[str, str]:
    if not isinstance(change, dict):
        raise ValueError("each change must be an object")

    sid = change.get("source_id")
    ko = change.get("ko")
    if not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f]{16}", sid):
        raise ValueError(f"invalid source_id: {sid!r}")
    if sid in seen:
        raise ValueError(f"duplicate source_id in proposal: {sid}")
    seen.add(sid)

    if sid not in unique_by_id:
        raise ValueError(f"unknown source_id: {sid}")
    row = unique_by_id[sid]
    if not row.get("translatable"):
        raise ValueError(f"source_id is not translatable: {sid}")

    if not isinstance(ko, str):
        raise ValueError(f"ko must be a string: {sid}")
    if not ko:
        raise ValueError(f"ko must not be empty: {sid}")
    if len(ko) > MAX_KO_CHARS:
        raise ValueError(f"ko is too long: {sid}")

    expected_source = row.get("source", "")
    if "source" in change and change["source"] != expected_source:
        raise ValueError(f"source mismatch for {sid}")
    if source_id(expected_source) != sid:
        raise ValueError(f"stored source_id mismatch: {sid}")

    missing = placeholders(expected_source) - placeholders(ko)
    if missing:
        raise ValueError(f"placeholder missing for {sid}: {sorted(missing)}")

    return sid, ko


def apply_proposal(proposal: dict) -> dict:
    if not isinstance(proposal, dict):
        raise ValueError("proposal must be an object")
    if proposal.get("version") != 1:
        raise ValueError("proposal version must be 1")
    changes = proposal.get("changes")
    if not isinstance(changes, list):
        raise ValueError("proposal changes must be an array")
    if not changes:
        raise ValueError("proposal has no changes")
    if len(changes) > MAX_CHANGES:
        raise ValueError(f"proposal has too many changes: {len(changes)} > {MAX_CHANGES}")

    unique = load_json(UNIQUE)
    records = load_json(RECORDS)
    unique_by_id = {row["source_id"]: row for row in unique}

    parsed_changes: list[tuple[str, str]] = []
    seen: set[str] = set()
    for change in changes:
        parsed_changes.append(validate_change(change, unique_by_id, seen))

    changed_unique = 0
    changed_records = 0
    affected_records = 0
    for sid, ko in parsed_changes:
        row = unique_by_id[sid]
        if row.get("ko") != ko:
            row["ko"] = ko
            row["translation_status"] = "translated"
            changed_unique += 1

        for record in records:
            if record.get("source_id") != sid:
                continue
            affected_records += 1
            if record.get("ko") != ko:
                record["ko"] = ko
                changed_records += 1

    write_json(UNIQUE, unique)
    write_json(RECORDS, records)
    return {
        "proposal_version": proposal.get("version"),
        "base_commit": proposal.get("base_commit"),
        "changes_requested": len(parsed_changes),
        "unique_changed": changed_unique,
        "records_changed": changed_records,
        "records_affected": affected_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--issue-body", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    try:
        proposal = load_proposal(args)
        summary = apply_proposal(proposal)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(summary, ensure_ascii=False, indent=2)
    print(output)
    if args.summary:
        args.summary.write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

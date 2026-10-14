#!/usr/bin/env python3
"""
Merge community metadata into master_list.csv.

- Reads: master_list.csv (authoritative DB export)
- Reads: community_stamp_info.csv (optional; generated from Willow workbook)
- Writes: master_list.csv (overwrites) and master_list.backup.csv (backup)

Output master_list.csv will:
- REMOVE the 'source' column
- ADD a compact 'info' column (single field combining action/definition/notes)
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
from typing import Dict


def _build_info(ci_row: Dict[str, str]) -> str:
    action = (ci_row.get("action") or "").strip()
    definition = (ci_row.get("server_definition") or "").strip()
    notes = (ci_row.get("notes") or "").strip()

    parts = []
    if action:
        parts.append(f"Action: {action}")
    if definition:
        parts.append(f"Def: {definition}")
    if notes:
        parts.append(f"Notes: {notes}")
    return " | ".join(parts)


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    master_path = os.path.join(script_dir, "master_list.csv")
    community_path = os.path.join(script_dir, "community_stamp_info.csv")
    backup_path = os.path.join(script_dir, "master_list.backup.csv")
    tmp_path = os.path.join(script_dir, "master_list.tmp.csv")
    merged_path = os.path.join(script_dir, "master_list.merged.csv")

    if not os.path.exists(master_path):
        print(f"ERROR: master list not found: {master_path}", file=sys.stderr)
        return 1

    community_by_stamp: Dict[str, Dict[str, str]] = {}
    if os.path.exists(community_path):
        with open(community_path, "r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                stamp = (row.get("stamp_name") or "").strip()
                if stamp:
                    community_by_stamp[stamp] = row

    # Backup first
    shutil.copy2(master_path, backup_path)

    with open(master_path, "r", encoding="utf-8", newline="") as src, open(
        tmp_path, "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        if not reader.fieldnames:
            print("ERROR: master_list.csv has no headers", file=sys.stderr)
            return 1

        # Build output columns:
        # - keep everything except 'source'
        # - ensure 'info' exists (at end)
        out_fields = [fn for fn in reader.fieldnames if fn != "source"]
        if "info" not in out_fields:
            out_fields.append("info")

        writer = csv.DictWriter(dst, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()

        rows = 0
        merged = 0
        for row in reader:
            stamp = (row.get("stamp_name") or "").strip()
            ci = community_by_stamp.get(stamp)
            info = _build_info(ci) if ci else ""
            if info:
                merged += 1
            row["info"] = info
            writer.writerow(row)
            rows += 1

    try:
        os.replace(tmp_path, master_path)
        print(f"Updated master_list.csv: {rows} rows, {merged} rows with community info.")
        print(f"Backup written to: {backup_path}")
    except PermissionError:
        # Windows will deny replace if the CSV is open in Excel/IDE or locked by another process.
        # Keep the merged output under a new name instead.
        try:
            os.replace(tmp_path, merged_path)
        except Exception as e:
            print(f"ERROR: failed to write merged output: {e}", file=sys.stderr)
            return 1
        print(
            "WARNING: Could not overwrite master_list.csv (file is likely open/locked).",
            file=sys.stderr,
        )
        print(f"Wrote merged output to: {merged_path}", file=sys.stderr)
        print(f"Backup written to: {backup_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


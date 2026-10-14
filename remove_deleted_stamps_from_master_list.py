#!/usr/bin/env python3
"""
Remove stamps listed in:
  "Infinite Leaftide Shared Weenies - QB to DELETE.csv"

from:
  - master_list.csv
  - master_list.merged.csv (if present)

Safe behavior on Windows:
- Writes a backup for each file touched
- Attempts in-place replace; if blocked (file open/locked), writes a *.cleaned.csv output instead.
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
from typing import Iterable, Set


def _read_delete_set(delete_csv_path: str) -> Set[str]:
    with open(delete_csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Delete CSV has no headers")

        # Known header from your file: "Quest Stamp"
        key = "Quest Stamp" if "Quest Stamp" in reader.fieldnames else reader.fieldnames[0]

        stamps: Set[str] = set()
        for row in reader:
            stamp = (row.get(key) or "").strip()
            if stamp:
                stamps.add(stamp)
    return stamps


def _clean_csv(
    input_path: str,
    output_path: str,
    delete_set: Set[str],
    stamp_field: str = "stamp_name",
) -> tuple[int, int]:
    """Return (rows_in, rows_removed)."""
    rows_in = 0
    rows_removed = 0
    with open(input_path, "r", encoding="utf-8", newline="") as src, open(
        output_path, "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        if not reader.fieldnames:
            raise ValueError(f"{os.path.basename(input_path)} has no headers")

        writer = csv.DictWriter(dst, fieldnames=reader.fieldnames, extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            rows_in += 1
            stamp = (row.get(stamp_field) or "").strip()
            if stamp and stamp in delete_set:
                rows_removed += 1
                continue
            writer.writerow(row)

    return rows_in, rows_removed


def _process_one(path: str, delete_set: Set[str]) -> None:
    if not os.path.exists(path):
        return

    base = os.path.basename(path)
    backup = path + ".before_delete_backup.csv"
    tmp = path + ".tmp"
    cleaned_fallback = path + ".cleaned.csv"

    shutil.copy2(path, backup)
    rows_in, rows_removed = _clean_csv(path, tmp, delete_set, stamp_field="stamp_name")

    try:
        os.replace(tmp, path)
        print(f"{base}: removed {rows_removed} of {rows_in} rows. Backup: {os.path.basename(backup)}")
    except PermissionError:
        os.replace(tmp, cleaned_fallback)
        print(
            f"WARNING: {base} is locked; wrote cleaned output to: {os.path.basename(cleaned_fallback)}",
            file=sys.stderr,
        )
        print(f"{base}: would remove {rows_removed} of {rows_in} rows. Backup: {os.path.basename(backup)}", file=sys.stderr)


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    delete_csv = os.path.join(script_dir, "Infinite Leaftide Shared Weenies - QB to DELETE.csv")
    if not os.path.exists(delete_csv):
        print(f"ERROR: delete list not found: {delete_csv}", file=sys.stderr)
        return 1

    delete_set = _read_delete_set(delete_csv)
    print(f"Loaded {len(delete_set)} stamps to delete.")

    _process_one(os.path.join(script_dir, "master_list.csv"), delete_set)
    _process_one(os.path.join(script_dir, "master_list.merged.csv"), delete_set)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


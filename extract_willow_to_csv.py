#!/usr/bin/env python3
"""
Extract community metadata from:
  "Willow Leaftide Tracking Book v1.5a.xlsx"

and write a lightweight, distribution-friendly CSV:
  community_stamp_info.csv

This keeps the main app dependency-light (CSV only), while allowing maintainers
to regenerate the community dataset from the workbook when it changes.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xlsx_path = os.path.join(script_dir, "Willow Leaftide Tracking Book v1.5a.xlsx")
    out_path = os.path.join(script_dir, "community_stamp_info.csv")

    if not os.path.exists(xlsx_path):
        print(f"ERROR: workbook not found: {xlsx_path}", file=sys.stderr)
        return 1

    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        print("ERROR: pandas is required to extract the workbook.", file=sys.stderr)
        print("Install with: python -m pip install --user pandas openpyxl", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return 1

    # The "qb-list-alt" sheet has 2 header/title rows, then a real header row.
    # We use header=2 to get: Flag, quest, Action, Notes, Server Side Definition, Completed
    df = pd.read_excel(xlsx_path, sheet_name="qb-list-alt", header=2)

    # Normalize/clean
    df = df.rename(
        columns={
            "Flag": "stamp_name",
            "quest": "quest_slug",
            "Action": "action",
            "Notes": "notes",
            "Server Side Definition": "server_definition",
            "Completed": "completed_in_willow",
        }
    )

    # Keep only rows with a stamp name
    df["stamp_name"] = df["stamp_name"].astype(str).str.strip()
    df = df[df["stamp_name"].notna() & (df["stamp_name"] != "")].copy()

    # De-dupe by stamp_name (keep the first non-empty info row)
    df["quest_slug"] = df["quest_slug"].astype("string")
    df["action"] = df["action"].astype("string")
    df["notes"] = df["notes"].astype("string")
    df["server_definition"] = df["server_definition"].astype("string")

    df = df.sort_values(by=["stamp_name"], kind="stable").drop_duplicates(subset=["stamp_name"], keep="first")

    out_cols = ["stamp_name", "quest_slug", "action", "notes", "server_definition"]
    df[out_cols].to_csv(out_path, index=False, encoding="utf-8", lineterminator="\n")

    print(f"Wrote {len(df)} rows to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


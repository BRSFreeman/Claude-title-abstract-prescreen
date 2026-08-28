#!/usr/bin/env python3
"""
merge_datasets.py — merge several screening-round outputs on the record ID.

Takes two or more combined CSVs (the output of combine.py, one per screening
round) and outer-joins them on the record ID column, so each record ends up
with one row carrying every round's `<TYPE>_decision` column.

Columns that already exist in the accumulated result are dropped from the
right-hand file, so shared metadata (Title, Abstract, ...) is not duplicated
with _x/_y suffixes.

All paths are resolved relative to the CURRENT WORKING DIRECTORY.

Usage:
    python merge_datasets.py FILE [FILE ...] [--output OUT] [--key COLUMN]

Example:
    python merge_datasets.py objective_20260611_0819.csv PICO_20260611_0819.csv \
        --output merged.csv
"""
import argparse
import io
import os
import sys

import pandas as pd


def load_csv(path):
    with open(path, "rb") as fh:
        raw = fh.read().replace(b"\x00", b"")
    return pd.read_csv(io.StringIO(raw.decode("utf-8", errors="replace")), dtype=str)


def main():
    ap = argparse.ArgumentParser(
        description="Merge screening-round outputs on the record ID column.")
    ap.add_argument("files", nargs="+", help="Two or more CSVs to merge")
    ap.add_argument("--output", default="merged.csv",
                    help="Output path (default: merged.csv)")
    ap.add_argument("--key", default="Covidence #",
                    help='Column to merge on (default: "Covidence #")')
    args = ap.parse_args()

    merge_key = args.key

    dfs = []
    for f in args.files:
        if not os.path.exists(f):
            print(f"WARNING: File not found - {f}", file=sys.stderr)
            continue
        df = load_csv(f)
        if merge_key not in df.columns:
            print(f"WARNING: '{merge_key}' column not found in {f} - skipping", file=sys.stderr)
            continue
        dfs.append((f, df))

    if not dfs:
        sys.exit("ERROR: No valid files loaded. Check file names and paths.")
    if len(dfs) == 1:
        print(f"WARNING: only one usable file ({dfs[0][0]}); output is a copy of it.",
              file=sys.stderr)

    if os.path.exists(args.output):
        sys.exit(f"ERROR: Output file already exists: {args.output}")

    merged = dfs[0][1]
    for name, df in dfs[1:]:
        # Keep only the key plus columns not already present, so shared metadata
        # (Title, Abstract, ...) is not duplicated with _x/_y suffixes.
        right_cols = [merge_key] + [c for c in df.columns if c not in merged.columns]
        merged = merged.merge(df[right_cols], on=merge_key, how="outer")
        print(f"  merged {name}: +{len(right_cols) - 1} new column(s)")

    merged.to_csv(args.output, index=False)
    print(f"Done. Merged {len(dfs)} files -> {args.output} "
          f"({len(merged)} rows, {len(merged.columns)} columns)")


if __name__ == "__main__":
    main()

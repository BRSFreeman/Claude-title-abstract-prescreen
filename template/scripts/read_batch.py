#!/usr/bin/env python3
"""
read_batch.py — read a batch CSV for screening.

Two modes:

  1. Summary (no --start/--end): print the row count and the list of
     record IDs in the batch.

  2. Range (with --start/--end): print the Title and Abstract for the
     rows in the half-open interval [start, end), e.g. --start 0 --end 10.

The batch CSV may contain embedded NUL bytes; they are stripped before
parsing. Never use `cat` on the full file - use this script instead.

Examples:
  python read_batch.py batches/batch_002_TAG.csv
  python read_batch.py batches/batch_002_TAG.csv --start 0 --end 10
"""
import argparse
import io
import sys

import pandas as pd


def load(path):
    with open(path, "rb") as f:
        raw = f.read().replace(b"\x00", b"")
    return pd.read_csv(io.StringIO(raw.decode("utf-8", errors="replace")), dtype=str)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # Python < 3.7
        pass

    ap = argparse.ArgumentParser(description="Read a batch CSV for screening.")
    ap.add_argument("input", help="Path to batch_NNN_TAG.csv")
    ap.add_argument("--start", type=int, default=None, help="First row (inclusive, 0-based)")
    ap.add_argument("--end", type=int, default=None, help="Last row (exclusive)")
    ap.add_argument("--id-column", default="Covidence #",
                    help='Unique record ID column (default: "Covidence #")')
    args = ap.parse_args()

    df = load(args.input)

    required = {args.id_column, "Title", "Abstract"}
    missing = required - set(df.columns)
    if missing:
        print(f"ERROR: input is missing required column(s): {sorted(missing)}", file=sys.stderr)
        print(f"       Found columns: {sorted(df.columns)}", file=sys.stderr)
        sys.exit(1)

    if args.start is None and args.end is None:
        print("Rows:", len(df))
        print("Record IDs:", list(df[args.id_column]))
        return

    start = args.start if args.start is not None else 0
    end = args.end if args.end is not None else len(df)
    for _, row in df.iloc[start:end].iterrows():
        print("=== " + str(row[args.id_column]) + " ===")
        print("TITLE: " + str(row["Title"]))
        print("ABSTRACT: " + str(row["Abstract"]))
        print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
split_batches.py — shuffle a screening export and split it into batch CSVs.

Reads an Excel (.xlsx/.xlsm/.xls) or CSV export of records, shuffles the rows,
and writes fixed-size batches as `<out-dir>/batch_NNN_TAG.csv`, where TAG is a
run tag of the form YYYYMMDD_HHMM. The tag is printed on stdout and is the
handle you pass to every later stage of the pipeline.

All paths are resolved relative to the CURRENT WORKING DIRECTORY. Run this from
your project root.

Usage:
    python split_batches.py INPUT [options]

Examples:
    python split_batches.py example_input.csv
    python split_batches.py exports/review.xlsx --batch-size 25 --seed 42

Reproducibility:
    Row order is shuffled. Pass --seed to make batch composition reproducible;
    without it, two runs on the same input produce different batches.
"""
import argparse
import io
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xls"}


def read_table(path, header_row):
    """Read an Excel or CSV export as all-string columns."""
    suffix = os.path.splitext(path)[1].lower()
    if suffix in EXCEL_SUFFIXES:
        return pd.read_excel(path, dtype=str, skiprows=header_row)
    with open(path, "rb") as fh:
        raw = fh.read().replace(b"\x00", b"")
    return pd.read_csv(
        io.StringIO(raw.decode("utf-8", errors="replace")),
        dtype=str,
        skiprows=header_row,
    )


def write_batches(df, out_dir, batch_size, tag):
    """Write df to out_dir as batch_NNN_TAG.csv files. Returns the file count."""
    os.makedirs(out_dir, exist_ok=True)
    total = len(df)
    num_batches = (total + batch_size - 1) // batch_size  # ceiling division

    for i in range(num_batches):
        start = i * batch_size
        end = min(start + batch_size, total)
        batch = df.iloc[start:end].copy()
        batch["position"] = np.arange(len(batch))

        name = f"batch_{i + 1:03d}_{tag}.csv"
        batch.to_csv(os.path.join(out_dir, name), index=False)
        print(f"  Saved {name}  (rows {start + 1}-{end})")

    return num_batches


def main():
    ap = argparse.ArgumentParser(
        description="Shuffle a screening export and split it into batch CSVs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", help="Path to the .xlsx/.xlsm/.xls or .csv export")
    ap.add_argument("--batch-size", type=int, default=50,
                    help="Records per batch (default: 50)")
    ap.add_argument("--out-dir", default="batches",
                    help="Directory to write batch files into (default: batches)")
    ap.add_argument("--header-row", type=int, default=0,
                    help="Rows to skip before the header row (default: 0)")
    ap.add_argument("--seed", type=int, default=None,
                    help="Random seed for the shuffle. Omit for a random shuffle "
                         "(not reproducible).")
    ap.add_argument("--id-column", default="Covidence #",
                    help='Unique record ID column (default: "Covidence #")')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"ERROR: input file not found: {args.input}")

    tag = datetime.now().strftime("%Y%m%d_%H%M")
    print(f"Run tag: {tag}")
    print("  (Pass this tag to the screening command and to combine.py)")

    print(f"Reading: {args.input}")
    df = read_table(args.input, args.header_row)

    required = {args.id_column, "Title", "Abstract"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(
            f"ERROR: input is missing required column(s): {sorted(missing)}\n"
            f"       Found columns: {sorted(df.columns)}\n"
            f"       Rename your columns to match, or pass --id-column for the ID column."
        )

    if df[args.id_column].isna().any():
        n = int(df[args.id_column].isna().sum())
        print(f"WARNING: {n} row(s) have an empty {args.id_column}. "
              f"These cannot be matched back to a decision.", file=sys.stderr)

    df = df.sample(frac=1, random_state=args.seed).fillna("")
    if args.seed is None:
        print("NOTE: no --seed given; this split is not reproducible.")
    else:
        print(f"Seed: {args.seed}")

    print(f"Total records found: {len(df)}")
    num_batches = write_batches(df, args.out_dir, args.batch_size, tag)

    print(f"\nDone! {num_batches} batch files saved to: {args.out_dir}")
    print(f"Run tag was: {tag}")


if __name__ == "__main__":
    main()

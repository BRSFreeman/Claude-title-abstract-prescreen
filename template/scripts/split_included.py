#!/usr/bin/env python3
"""
split_included.py — re-batch the records that PASSED a previous screening round.

Round 2 (and later) of a staged screen. Takes the combined output of an earlier
round (e.g. `PICO_20260611_0819.csv`, produced by combine.py), keeps only the
rows whose `<DECISION>_decision` column is "include", shuffles them, and writes
fresh `batch_NNN_TAG.csv` files under a NEW run tag.

Use split_batches.py for round 1 (from the raw export); use this script for
every round after that.

All paths are resolved relative to the CURRENT WORKING DIRECTORY.

Usage:
    python split_included.py INPUT DECISION [options]

Examples:
    # Take everything the PICO round included and re-batch it for a design screen
    python split_included.py PICO_20260611_0819.csv PICO --seed 42
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
    """Read an Excel or CSV file as all-string columns."""
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
        description="Re-batch the records included by a previous screening round.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", help="Combined output of a previous round, e.g. PICO_TAG.csv")
    ap.add_argument("decision", help='Screening type to filter on, e.g. "PICO". '
                                     'Looks for the column <decision>_decision.')
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

    decision_col = f"{args.decision}_decision"
    required = {args.id_column, "Title", "Abstract", decision_col}
    missing = required - set(df.columns)
    if missing:
        sys.exit(
            f"ERROR: input is missing required column(s): {sorted(missing)}\n"
            f"       Found columns: {sorted(df.columns)}\n"
            f"       Check the DECISION argument matches a <name>_decision column."
        )

    included = df[df[decision_col].str.strip().str.lower() == "include"].copy()
    print(f"Rows in input: {len(df)}  ->  included by '{decision_col}': {len(included)}")
    if included.empty:
        sys.exit(f"ERROR: no rows with {decision_col} == 'include'. Nothing to batch.")

    included = included.sample(frac=1, random_state=args.seed).fillna("")
    if args.seed is None:
        print("NOTE: no --seed given; this split is not reproducible.")
    else:
        print(f"Seed: {args.seed}")

    num_batches = write_batches(included, args.out_dir, args.batch_size, tag)

    print(f"\nDone! {num_batches} batch files saved to: {args.out_dir}")
    print(f"Run tag was: {tag}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
combine.py — combine all per-batch outputs for a run tag into one master CSV.

Reads every `<TYPE>/<TYPE>_NNN_TAG.csv` produced by apply_decisions.py, adds a
`batch` column, concatenates them, and sorts by (<TYPE>_decision, numeric
record ID). Refuses to overwrite an existing output file.

All paths are resolved relative to the CURRENT WORKING DIRECTORY. Run this from
your project root.

Usage:
    python combine.py TAG TYPE [options]

Example:
    python combine.py 20260528_1034 PICO

TAG is printed by split_batches.py when the batches are created.
TYPE is the screening round name, e.g. 'objective', 'PICO', 'design'.
Output file: <TYPE>_<TAG>.csv
"""
import argparse
import glob
import io
import os
import sys

import pandas as pd


def load_csv(path):
    with open(path, "rb") as fh:
        raw = fh.read().replace(b"\x00", b"")
    return pd.read_csv(io.StringIO(raw.decode("utf-8", errors="replace")), dtype=str)


def numeric_id(value):
    """Best-effort numeric sort key for an ID like '#12345'. Non-numeric -> 0."""
    text = str(value).lstrip("#").strip()
    return int(text) if text.isdigit() else 0


def main():
    ap = argparse.ArgumentParser(
        description="Combine per-batch screening outputs into one master CSV.")
    ap.add_argument("tag", help="Run tag printed by split_batches.py, e.g. 20260528_1034")
    ap.add_argument("type", help="Screening type, e.g. objective, PICO, design")
    ap.add_argument("--in-dir", default=None,
                    help="Directory holding the per-batch outputs (default: <TYPE>)")
    ap.add_argument("--output", default=None,
                    help="Output path (default: <TYPE>_<TAG>.csv in the current directory)")
    ap.add_argument("--id-column", default="Covidence #",
                    help='Unique record ID column (default: "Covidence #")')
    args = ap.parse_args()

    tag = args.tag
    type_ = args.type
    in_dir = args.in_dir or type_
    output = args.output or f"{type_}_{tag}.csv"
    output_tmp = output + ".tmp"
    decision_col = f"{type_}_decision"

    # Guard against overwrite
    if os.path.exists(output_tmp):
        print(f"ERROR: Temp file already exists: {output_tmp}", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(output):
        try:
            with open(output, "r"):
                pass
            print(f"ERROR: Output file already exists: {output}", file=sys.stderr)
            sys.exit(1)
        except OSError:
            print(f"WARNING: Stale inode at {output} - will overwrite.", file=sys.stderr)

    # Collect all per-batch files for this tag, in order
    pattern = os.path.join(in_dir, f"{type_}_[0-9][0-9][0-9]_{tag}.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"ERROR: No files matched {pattern}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files)} files to combine.")

    frames = []
    for f in files:
        df = load_csv(f)
        base = os.path.basename(f)
        batch_num = base[len(f"{type_}_"):-len(f"_{tag}.csv")]
        df["batch"] = batch_num
        frames.append(df)
        print(f"  {base}: {len(df)} rows")

    combined = pd.concat(frames, ignore_index=True)

    for needed in (decision_col, args.id_column):
        if needed not in combined.columns:
            print(f"ERROR: combined data is missing column '{needed}'.", file=sys.stderr)
            print(f"       Found columns: {sorted(combined.columns)}", file=sys.stderr)
            sys.exit(1)

    combined["_id_num"] = combined[args.id_column].apply(numeric_id)
    combined = (combined
                .sort_values([decision_col, "_id_num"])
                .drop(columns=["_id_num"])
                .reset_index(drop=True))

    combined.to_csv(output_tmp, index=False)
    os.replace(output_tmp, output)

    print(f"\nDone. Combined {len(combined)} entries from {len(files)} batches.")
    print("Screening counts:")
    print(combined[decision_col].value_counts().sort_index())
    print(f"Output: {output}")


if __name__ == "__main__":
    main()

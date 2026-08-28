#!/usr/bin/env python3
"""
apply_decisions.py — apply screening decisions to a batch and write output.

Generic across screening types. The `--type` argument (e.g. "objective",
"PICO", "design") controls:
  * the name of the decision column added to the output: <TYPE>_decision
  * nothing else - paths are passed explicitly.

The screening agent does NOT edit this file. It only:
  1. writes a small 2-column CSV of its decisions, and
  2. runs this script pointing at that file.

Decisions CSV format (header required):
    Covidence #,decision
    #12345,include
    #12346,exclude
    ...

This script reads the batch, joins the decisions by record ID, adds a
`<TYPE>_decision` column, sorts by (<TYPE>_decision, numeric record ID), and
writes the result atomically. It refuses to overwrite an existing output file -
that guard is what makes the pipeline resume-safe.

Example:
  python apply_decisions.py \
      --type   objective \
      --batch  002 \
      --input  batches/batch_002_TAG.csv \
      --decisions temp/objective_002_TAG.decisions.csv \
      --output objective/objective_002_TAG.csv
"""
import argparse
import io
import os
import sys

import pandas as pd


def load_csv(path):
    with open(path, "rb") as f:
        raw = f.read().replace(b"\x00", b"")
    return pd.read_csv(io.StringIO(raw.decode("utf-8", errors="replace")), dtype=str)


def numeric_id(value):
    """Best-effort numeric sort key for an ID like '#12345'. Non-numeric -> 0."""
    text = str(value).lstrip("#").strip()
    return int(text) if text.isdigit() else 0


def load_decisions(path, id_column):
    ddf = load_csv(path)
    cols = {c.strip().lower(): c for c in ddf.columns}
    cov_col = (cols.get(id_column.strip().lower())
               or cols.get("covidence #")
               or cols.get("covidence")
               or cols.get("id")
               or ddf.columns[0])
    dec_col = cols.get("decision") or cols.get("label") or ddf.columns[1]

    mapping = {}
    for _, r in ddf.iterrows():
        key = str(r[cov_col]).strip()
        val = str(r[dec_col]).strip().lower()
        if val not in ("include", "exclude"):
            print(f"WARNING: unexpected decision '{val}' for {key} - treating as 'include'.",
                  file=sys.stderr)
            val = "include"
        mapping[key] = val
    return mapping


def main():
    ap = argparse.ArgumentParser(description="Apply screening decisions to a batch.")
    ap.add_argument("--type", required=True, help="Screening type, e.g. objective, PICO, design")
    ap.add_argument("--batch", required=True, help="Batch number, zero-padded (e.g. 002)")
    ap.add_argument("--input", required=True, help="Path to batch_NNN_TAG.csv")
    ap.add_argument("--decisions", required=True, help="2-column CSV: <id>,decision")
    ap.add_argument("--output", required=True, help="Path to <TYPE>_NNN_TAG.csv to write")
    ap.add_argument("--id-column", default="Covidence #",
                    help='Unique record ID column (default: "Covidence #")')
    args = ap.parse_args()

    col = f"{args.type}_decision"
    output = args.output
    output_tmp = output + ".tmp"

    if os.path.exists(output_tmp):
        print(f"ERROR: Temp file already exists - a previous run may be in progress: {output_tmp}",
              file=sys.stderr)
        sys.exit(1)

    if os.path.exists(output):
        try:
            open(output, "r").close()
            print(f"ERROR: Output file already exists - do NOT re-run this script: {output}",
                  file=sys.stderr)
            sys.exit(1)
        except OSError:
            print(f"WARNING: Stale inode detected at {output} - will overwrite via atomic replace.",
                  file=sys.stderr)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    df = load_csv(args.input)
    if args.id_column not in df.columns:
        print(f"ERROR: batch is missing the ID column '{args.id_column}'.", file=sys.stderr)
        print(f"       Found columns: {sorted(df.columns)}", file=sys.stderr)
        sys.exit(1)

    decisions = load_decisions(args.decisions, args.id_column)

    ids = df[args.id_column].fillna("").astype(str).str.strip()
    missing = [cid for cid in ids if cid not in decisions]
    if missing:
        print(f"WARNING: No decision found for {len(missing)} record ID(s): {missing}",
              file=sys.stderr)
        print("Defaulting missing entries to 'include' - please review.", file=sys.stderr)

    df[col] = ids.map(lambda x: decisions.get(x, "include"))

    df["_id_num"] = df[args.id_column].apply(numeric_id)
    df = df.sort_values([col, "_id_num"]).drop(columns=["_id_num"]).reset_index(drop=True)

    df.to_csv(output_tmp, index=False)
    os.replace(output_tmp, output)

    n = len(df)
    counts = df[col].value_counts().to_dict()
    print(f"[{args.type}] Batch {args.batch}: processed {n} entries.")
    print(f"{args.type} screening counts:")
    for label, count in sorted(counts.items()):
        print(f"  {label}: {count}")
    print(f"Output written: {output}")


if __name__ == "__main__":
    main()

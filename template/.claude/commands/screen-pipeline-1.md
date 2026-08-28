---
description: End-to-end screening pipeline (split - screen - combine)
argument-hint: [INPUT_FILE]   e.g. example_input.csv
---

Act as the **pipeline orchestrator**. Run the full screening pipeline end to
end: split the input into batches, screen them, and combine the output. Drive
the three steps below **in order**, threading the run tag printed by the split
step into the steps that follow it.

Because `/screen-batches-wf` launches a **background** Workflow, this is a
multi-turn job: after launching the screening stage, **wait for that Workflow
to finish** (you'll get a completion notification) before running the next
step. Do not skip ahead while a screening Workflow is running.

Arguments: `$ARGUMENTS`
- The entire argument string is `INPUT_FILE`, the `.xlsx` or `.csv` export to
  screen (the name may contain spaces). If omitted, resolve it in Step 0.

## Step 0 — Resolve the environment (do this BEFORE any step)

Nothing below is machine- or project-specific; resolve it all at runtime.

1. **`PROJECT`** = the current project directory as an absolute path with
   forward slashes. Get it from Bash `pwd`. Every path below is relative to it,
   and every `python` command is run from `$PROJECT`.

2. **`PYTHON`** — find a working interpreter and record its **absolute** path.
   On Windows the bare `python`/`python3` aliases are often Microsoft Store
   stubs that fail, so verify whatever you find:

   ```bash
   python --version || python3 --version
   ```

   Windows fallback — look for a real interpreter:

   ```bash
   ls /c/Users/*/anaconda3/python.exe /c/Python3*/python.exe 2>/dev/null | head
   ```

   macOS / Linux fallback: `command -v python3`.

3. **Locate the scripts.** Confirm `scripts/split_batches.py` and
   `scripts/combine.py` exist. If either is missing, stop and tell the user
   which, so they can restore it.

4. **Check the criteria are filled in.** Open `screening_agent_<TYPE>.md`
   (default TYPE is `PICO`) and confirm the Criteria section has no remaining
   FILL-THIS-IN markers. If it does, **stop** — screening with empty criteria
   produces meaningless decisions. Tell the user to fill them in first, and
   point them at `screening_agent_PICO.example.md`.

5. **`INPUT_FILE`** — from `$ARGUMENTS` if provided. If omitted, list the
   `.xlsx` and `.csv` files in `$PROJECT`; if exactly one plausible export
   exists, use it; if zero or several, ask the user which to screen. Record its
   **absolute** path as `INPUT_PATH`.

Notes that hold for every step:
- Run every `python` command from **`$PROJECT`**. All scripts resolve their
  paths relative to the current working directory.
- The split script writes its `batch_NNN_<TAG>.csv` files into
  **`$PROJECT/batches/`**, which is where `/screen-batches-wf` reads them.

---

## Step 1 — Split the input into batches

```bash
"$PYTHON" scripts/split_batches.py "$INPUT_PATH"
```

Add `--seed` if the user wants the split to be reproducible; add `--batch-size N` to change the
default of 50, and `--id-column "..."` if the export does not use
`Covidence #`.

Capture **TAG1** from the `Run tag: YYYYMMDD_HHMM` line in stdout.

Report: TAG1 and the number of batch files written to `batches/`.

## Step 2 — Screen the batches

Invoke the screening command and **wait for it to complete**:

```
/screen-batches-wf PICO <TAG1>
```

This writes `PICO/PICO_NNN_<TAG1>.csv` for every batch. Do not proceed until
the Workflow reports completion and every batch has an output.

## Step 3 — Combine the outputs

```bash
"$PYTHON" scripts/combine.py "$TAG1" PICO
```

Produces `PICO_<TAG1>.csv` at the project root (sorted, with a `PICO_decision`
column). Report the include/exclude counts it prints.

---

## Final report

Summarize the whole run:
- Input file and **TAG1** (and TAG2, if a second round ran).
- Total abstracts, include vs. exclude, and the output filename.
- Any batches still missing an output in either stage (re-run the relevant
  `/screen-batches-wf <TYPE> <TAG>` to retry only those).

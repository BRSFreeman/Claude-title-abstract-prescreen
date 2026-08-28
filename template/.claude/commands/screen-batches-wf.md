---
description: Screen all remaining abstract batches via a single Workflow pipeline (up to 16 concurrent)
argument-hint: [TYPE] [TAG]   e.g. PICO 20260625_1545
---

Act as the screening **orchestrator**, but instead of hand-driving waves of
sub-agents, launch ONE background **Workflow** that pipelines every remaining
batch through a screening sub-agent (up to 16 running concurrently). Do not
stop to ask the user once the queue is built — launch the Workflow and report
when it finishes.

> **Requires the `Workflow` tool**, which is opt-in. If it is unavailable in
> this session, say so and offer to screen the batches with ordinary `Agent`
> sub-agents in waves instead — the per-batch instructions below are identical.

Arguments: `$ARGUMENTS`
- First token = TYPE (e.g. `PICO`, `objective`). Default `PICO` if omitted.
- Second token = TAG (e.g. `20260625_1545`). If omitted, infer it from the
  `batch_*_TAG.csv` filenames in `batches/` (use the most recent tag).

Paths (relative to the current project directory):
- `BATCHES_DIR = batches`
- `SCRIPTS_DIR = scripts`
- `OUTPUT_DIR  = <TYPE>` (e.g. `PICO/`)
- `TEMP_DIR    = temp` (scratch dir for the per-batch decisions CSVs)
- Per-agent template = `screening_agent_<TYPE>.md`

---

## Step 0 — Resolve the environment (do this BEFORE launching)

Nothing below is machine- or project-specific; resolve it all at runtime.

1. **`PROJECT`** = the current project directory as an absolute path with
   forward slashes. Get it from Bash `pwd`.

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

   Confirm the chosen path runs before continuing. Every sub-agent is given
   this path explicitly.

3. **Confirm `screening_agent_<TYPE>.md` exists** in `$PROJECT`, and that its
   Criteria section is filled in (no remaining FILL-THIS-IN markers). If the
   markers are still there, **stop** and tell the user — the screen would
   produce meaningless decisions.

4. **Ensure `OUTPUT_DIR` and `TEMP_DIR` exist** (create them if not).

5. **Resolve TAG** from the batch filenames if not supplied.

---

## Step 1 — Build the resume-safe queue

List the batch numbers that have NO output yet. `apply_decisions.py` refuses to
overwrite an existing output, so the queue is just "every batch missing a
`<TYPE>/<TYPE>_NNN_TAG.csv`".

Portable (Bash) — substitute TYPE and TAG:

```bash
for b in batches/batch_*_TAG.csv; do
  nnn=$(basename "$b" | cut -d_ -f2)
  [ -f "TYPE/TYPE_${nnn}_TAG.csv" ] || echo "$nnn"
done
```

Or with PowerShell:

```
$batches = Get-ChildItem batches\batch_*_TAG.csv
$done    = Get-ChildItem TYPE\TYPE_*_TAG.csv -ErrorAction SilentlyContinue |
             ForEach-Object { $_.BaseName.Split('_')[1] }
$batches | ForEach-Object { $_.BaseName.Split('_')[1] } |
  Where-Object { $_ -notin $done }
```

Report: total batches, already done, remaining. **If nothing remains, skip to
the final report.** Otherwise capture the remaining numbers as a zero-padded
array (e.g. `['144','145',…]`).

---

## Step 2 — Launch ONE Workflow that pipelines the remaining batches

Call the **Workflow** tool with a script shaped like the template below. Fill in
the resolved `PYTHON`, `PROJECT`, `TAG`, and the `REMAINING` array from Step 1.
Each sub-agent is given concrete paths plus an instruction to **read
`screening_agent_<TYPE>.md`** for the full objective and decision rules, so the
criteria live in one place and this command stays generic across TYPEs.

```javascript
export const meta = {
  name: 'screen-TYPE-TAG',
  description: 'Screen remaining batches for one screening round via pipeline',
  phases: [{ title: 'Screen' }, { title: 'Report' }],
};

const TYPE    = 'PICO';                 // <-- your screening round
const TAG     = '20260625_1545';        // <-- your run tag
const PYTHON  = '/absolute/path/to/python';
const PROJECT = '/absolute/project/dir';
const SCRIPTS = PROJECT + '/scripts';
const BATCHES = PROJECT + '/batches';
const TEMP    = PROJECT + '/temp';
const OUT     = PROJECT + '/' + TYPE;

// Zero-padded batch numbers with no output yet (from Step 1):
const REMAINING = [ /* '001','002',... */ ];

log('Screening ' + REMAINING.length + ' remaining ' + TYPE + ' batches');
phase('Screen');

const SCHEMA = {
  type: 'object',
  properties: {
    batch:         { type: 'string' },
    total:         { type: 'number' },
    include_count: { type: 'number' },
    exclude_count: { type: 'number' },
    success:       { type: 'boolean' },
    note:          { type: 'string' },
  },
  required: ['batch', 'total', 'include_count', 'exclude_count', 'success'],
};

function prompt(nnn) {
  const batchCsv = BATCHES + '/batch_' + nnn + '_' + TAG + '.csv';
  const decCsv   = TEMP + '/' + TYPE + '_' + nnn + '_' + TAG + '.decisions.csv';
  const outCsv   = OUT + '/' + TYPE + '_' + nnn + '_' + TAG + '.csv';
  return [
    'You are an expert systematic reviewer screening abstracts for a systematic review.',
    'Screen batch ' + nnn + ' (TYPE=' + TYPE + ', TAG=' + TAG + ') and write its output.',
    '',
    'FIRST read the screening criteria file in full (Read tool):',
    '  ' + PROJECT + '/screening_agent_' + TYPE + '.md',
    'Follow its Objective and decision rules. Err toward INCLUDE when unsure;',
    'if an abstract is empty/missing, label include.',
    '',
    'Paths (use these EXACT strings; forward slashes in Bash):',
    '  Python:         ' + PYTHON,
    '  read_batch.py:  ' + SCRIPTS + '/read_batch.py',
    '  apply_decisions:' + SCRIPTS + '/apply_decisions.py',
    '  Batch CSV:      ' + batchCsv,
    '  Decisions CSV:  ' + decCsv,
    '  Output CSV:     ' + outCsv,
    '',
    'STEP 1 (Bash) - row count + record IDs:',
    '  "' + PYTHON + '" "' + SCRIPTS + '/read_batch.py" "' + batchCsv + '"',
    '',
    'STEP 2 (Bash) - read ALL rows in chunks of 10 until every row is read:',
    '  "' + PYTHON + '" "' + SCRIPTS + '/read_batch.py" "' + batchCsv + '" --start 0 --end 10',
    '  ...continue --start 10 --end 20, etc. up to the row count.',
    '',
    'STEP 3 - decide include/exclude per abstract (1-sentence reason each).',
    '',
    'STEP 4 (Write tool) - write ' + decCsv + ' starting with the exact header',
    '  Covidence #,decision',
    'then one include/exclude line for EVERY record ID (no gaps).',
    '',
    'STEP 5 (Bash) - apply, exactly once (skip if output already exists):',
    '  "' + PYTHON + '" "' + SCRIPTS + '/apply_decisions.py" --type ' + TYPE +
      ' --batch ' + nnn + ' --input "' + batchCsv + '" --decisions "' + decCsv +
      '" --output "' + outCsv + '"',
    '',
    'STEP 6 (Bash) - verify: head -3 "' + outCsv + '"',
    '',
    'Return structured output: batch, total, include_count, exclude_count, success, note.',
  ].join('\n');
}

const results = await pipeline(
  REMAINING,
  (nnn) => agent(prompt(nnn), { label: 'screen-' + nnn, phase: 'Screen', schema: SCHEMA })
);

phase('Report');
const ok      = results.filter(Boolean).filter(r => r.success);
const failed  = REMAINING.filter(nnn => !ok.find(r => r.batch === nnn));
const include = ok.reduce((s, r) => s + (r.include_count || 0), 0);
const exclude = ok.reduce((s, r) => s + (r.exclude_count || 0), 0);
log('Succeeded ' + ok.length + '/' + REMAINING.length +
    ' | include ' + include + ' | exclude ' + exclude +
    (failed.length ? ' | still missing: ' + failed.join(', ') : ' | all complete'));
return { succeeded: ok.length, include, exclude, missing_batches: failed };
```

Notes on the script:
- If your project uses an ID column other than `Covidence #`, add
  `--id-column "<your column>"` to both `read_batch.py` and
  `apply_decisions.py` in the prompt above, and change the decisions-CSV header
  in STEP 4 to match.
- `pipeline()` keeps up to ~16 agents running at once and is itself resume-safe
  at the file level: any batch whose output already exists is a no-op in
  `apply_decisions.py`, so re-running this command only reprocesses what's
  missing.
- Pass the `REMAINING` array as a real JS array literal in the script — do not
  stringify it.
- The Workflow runs in the **background**; you'll be notified on completion.

---

## Step 3 — Final report

When the Workflow finishes (or immediately, if the queue was empty), tally the
**combined** totals across ALL `<TYPE>/<TYPE>_*_<TAG>.csv` files (not just this
run) so the numbers reflect the whole corpus. With PowerShell:

```
$rows = Get-ChildItem TYPE\TYPE_*_TAG.csv | ForEach-Object { Import-Csv $_.FullName }
$rows.Count
($rows | Where-Object { $_.'TYPE_decision' -eq 'include' }).Count
($rows | Where-Object { $_.'TYPE_decision' -eq 'exclude' }).Count
```

Report: total batches, processed this run vs. already done, output files present
(should equal total batches), combined include/exclude totals, and any batches
still missing an output (re-running `/screen-batches-wf` retries only those).

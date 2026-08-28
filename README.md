# LLM-Assisted Abstract Screening Template

A template for pre-screening titles and abstracts for a systematic review, in advance of dual-reviewer screening. Uses [Claude Code](https://claude.com/claude-code) and Python.

The user provides inclusion criteria into a templated prompt as well as a spreadsheet containing titles and abstracts (e.g. from Covidence). The pipeline splits the records into batches, hands each batch to a screening agent, and reassembles the decisions into one CSV with an `include`/`exclude` column corresponding to the LLMs decisions.

---

## Details

**This is a screening aid to reduce the overall burden of title and abstract screening.** It does not fully replace dual independent human screening. Previous testing suggests that about 80% of irrelevant abstracts are removed on average. The systematic review team is still responsible for the remaining 20%.

- The prompt is deliberately tuned for **high sensitivity**: agents are told to
  include anything ambiguous, and to include records with a missing abstract.
- You should still audit a handful of excluded abstracts to ensure that you are getting the intended behaviour.
- **LLM output is not deterministic.** The same abstract can receive different
  labels on different runs.
- **Reporting** If findings from this pipeline appear in a
  publication, describe the model, the prompt, the date, and the human
  verification you performed. PRISMA and Cochrane guidance on automation tools
  applies.
- **Data-sharing.** Some bibliographic databases restrict what
  you may send to a third-party service, including Claude.

---

## Requirements

- Python 3.8+
- [Claude Code](https://claude.com/claude-code)
- Python packages: see `requirements.txt`

```bash
pip install -r requirements.txt
```

The `/screen-batches-wf` command uses Claude Code's **Workflow** tool, which is
opt-in and may not be enabled in your session. If it isn't, the command falls
back to ordinary sub-agents — see the note at the top of that file.

### Finding your Python interpreter

The commands need an interpreter that actually runs. On Windows, the bare
`python` and `python3` aliases are frequently Microsoft Store stubs that fail.
Verify before you start:

```bash
python --version
```

If that errors, find a real one (Anaconda, python.org) and use its absolute
path everywhere. The slash commands do this resolution automatically. Claude is
also capable of finding Python installations if necessary.

---

## Input format

The input is an `.xlsx`, `.xlsm`, `.xls`, or `.csv` export. Three columns are
**required**:

| Column | Purpose |
|---|---|
| `Covidence #` | Unique record ID. |
| `Title` | Record title. |
| `Abstract` | Abstract text. May be blank — blanks are included by default. |

Every other column is carried through untouched to the output.

The default ID column name and the `#12345` ID format come from
[Covidence](https://www.covidence.org/) exports. If you use a different tool,
either rename your ID column to `Covidence #` or pass
`--id-column "Your Column"` to `split_batches.py`, `read_batch.py`,
`apply_decisions.py`, and `combine.py`.

---

## Setup

1. **Copy this template** into a new folder for your review.
2. **Fill in your criteria.** Open `screening_agent_PICO.md` and replace every
   `<!-- FILL THIS IN -->` block in the **Criteria** section. This is the only
   file you must edit, and the pipeline is worthless until you do. 
   Delete unused criteria (e.g. if outcomes do not affect inclusion in the review).
   `screening_agent_PICO.example.md` shows a fully worked example.
3. **Drop your export** into the project folder.

---

## Running it

### Completely automated processing

From Claude Code, in the project folder:

```
/screen-pipeline-1 <Input csv file>
```

### Manually driven steps

```bash
# 1. Split into batches. Note the run tag it prints. Can optionally add a seed tag e.g. --seed 42 if you want the split to be reproducible
python scripts/split_batches.py <input-file>

# 2. Screen every batch (from Claude Code, using the tag from step 1)
#    /screen-batches-wf PICO 20260824_0930

# 3. Combine the per-batch outputs into one CSV
python scripts/combine.py 20260824_0930 PICO
```

Result: `PICO_20260824_0930.csv` — every input row, plus a `PICO_decision` column and a `batch` column, sorted with excludes first.

---

## How it works

```
export.xlsx
    |
    |  split_batches.py  generates the run tag, splits the records into batches in random order (default 50 per)
    v
batches/batch_001_TAG.csv ... batch_NNN_TAG.csv
    |
    |  /screen-batches-wf   one agent per batch, up to 16 at once (or number of processors, whichever is smaller)
    |     each agent: read -> decide -> decisions CSV -> apply_decisions.py
    v
PICO/PICO_001_TAG.csv ... PICO_NNN_TAG.csv
    |
    |  combine.py
    v
PICO_TAG.csv
```

**The run tag** (`YYYYMMDD_HHMM`) ties a batch set to its outputs. It is printed by the split scripts and passed to every later stage.

**Resume safety**
In case of interruptions, the orchestration agent can determine which batches still require processing. The `apply_decisions` script also refuses to overwrite existing output, so old decisions should be safe.

**Batches are shuffled** to reduce risk of bias by publication year, database, etc.

---

## Scripts

All scripts resolve paths relative to the **current working directory** — run them from the project root. Every script takes `--help`.

| Script | Purpose |
|---|---|
| `scripts/split_batches.py` | Round 1: shuffle a raw export into `batches/batch_NNN_TAG.csv`. |
| `scripts/read_batch.py` | Read a batch, whole or by row range. Used by the screening agent. |
| `scripts/apply_decisions.py` | Join an agent's decisions onto a batch and write the output. |
| `scripts/combine.py` | Concatenate all per-batch outputs for one tag. |
| `scripts/merge_datasets.py` | Outer-join several rounds' outputs on the record ID. |

Useful options: `--batch-size`, `--seed`, `--id-column`, `--out-dir`, `--header-row`.

---

## Files you will edit

| File | Edit? |
|---|---|
| `screening_agent_PICO.md` | **Yes — required.** Your criteria go here. |
| `.claude/settings.json` | Only to adjust permissions. |
| `.claude/commands/*.md` | Only to change orchestration behaviour. |

Other files should not require editing.
---

## Data handling

`.gitignore` excludes tabulated data and processing results by default to avoid committing this information to github.

`.claude/settings.local.json` is also excluded: Once used, that file holds machine-specific paths and personal permission grants and should never be shared.

---

## Adding another screening round

1. Copy `screening_agent_PICO.md` to `screening_agent_<TYPE>.md`.
2. Replace `PICO` with `<TYPE>` throughout and rewrite the Criteria section.
3. Run `/screen-batches-wf <TYPE> <TAG>`. It picks up the new file
   automatically.

---

## Licence

MIT — see `LICENSE`. **Set the copyright holder before publishing**; the file
ships with a `<COPYRIGHT HOLDER>` placeholder.

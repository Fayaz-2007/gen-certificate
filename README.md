# KNOW-I Certificate Generator

Fills a KNOW-I certificate template with a student's name and serial number
— for a single certificate or a CSV batch run. Runs 100% offline: no network
calls, no API keys, no external services, at any point in the pipeline.
All image work is done with Pillow (PIL) as a coordinate-based text overlay
onto `blank.png` — there is no model involved.

## Setup

```bash
pip install -r requirements.txt
```

### Fonts (required)

This tool needs two exact font files and will refuse to run without them —
it never silently substitutes a different font, since that would break the
calibrated text alignment:

- `Poppins-Regular.ttf`
- `Poppins-Medium.ttf`

At startup the script looks for each font in this order:

1. `fonts/Poppins-Regular.ttf` and `fonts/Poppins-Medium.ttf` next to
   `gen_certificates.py`
2. `%LOCALAPPDATA%\Microsoft\Windows\Fonts\`
3. `%WINDIR%\Fonts\` (the system-wide Windows Fonts folder)

**Neither font is currently installed on this machine or bundled in this
project.** To fix that, do one of:

- Install Poppins system-wide (e.g. via Google Fonts:
  https://fonts.google.com/specimen/Poppins — download, then right-click
  each `.ttf` → "Install"), or
- Drop `Poppins-Regular.ttf` and `Poppins-Medium.ttf` directly into the
  `fonts/` folder in this project (already created, currently empty).

Poppins is licensed under the SIL Open Font License, so bundling the two
`.ttf` files in `fonts/` is permitted if you'd rather keep the project
self-contained.

## Usage

### Single certificate

```bash
python gen_certificates.py --template blank.png --name "Full Name" --serial "KI-26-AW-001"
```

### Batch from CSV

CSV must have a `name` column; `serial` is optional per row.

```bash
python gen_certificates.py --template blank.png --csv students.csv --prefix "KI-26-AW-" --start 1
```

If a row's `serial` is blank, one is auto-generated as `{prefix}{counter:03d}`.
The counter only increments for rows that needed an auto-generated serial —
rows with an explicit serial don't consume a counter value.

## Output

- If `--out-dir` is not passed, you'll be prompted:
  `Enter a folder name for this run (e.g. AgentWorkshop_Feb2026)`
- Everything is written under `output/<folder_name>/`.
- Single mode: one PNG saved inside `output/<folder_name>/`.
- Batch mode: one PNG per row inside `output/<folder_name>/`, plus the whole
  folder zipped to `output/<folder_name>.zip`.
- Passing `--out-dir <name>` skips the interactive prompt and uses that name
  directly.

## Template requirements

`blank.png` must be exactly **6250 x 4419 px**. The script checks this and
will refuse to run against a mismatched template, since the text coordinates
are calibrated to that exact canvas size.

Calibrated placement (do not change without re-calibrating against the
actual template):

| Field  | Position                             | Font              | Size  | Color            |
|--------|----------------------------------------|-------------------|-------|------------------|
| Name   | centered at (3125, 2040), upper-cased  | Poppins Regular   | 172px | RGB(30, 30, 30)  |
| Serial | left-aligned from (4930, 422), +12px letter spacing | Poppins Medium | 117px | RGB(20, 20, 20) |

`_reference_Tejaswini_K_KI-26-AW-001.png` in the project root is the saved
regression reference — a known-good render of the real template with
`--name "Tejaswini K" --serial "KI-26-AW-001"`. Compare against it before
and after any future change:

```bash
python gen_certificates.py --template blank.png --name "Tejaswini K" --serial "KI-26-AW-001" --out-dir _regression_test
```

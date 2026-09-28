#!/usr/bin/env python3
"""
KNOW-I Certificate Generator

Fills a KNOW-I certificate template with a student's name and serial number.
Runs fully offline: no network calls, no API keys, no external services.
Uses Pillow only for coordinate-based text overlay onto a pre-designed
template image.

Usage:
    Single certificate:
        python gen_certificates.py --template blank.png --name "Full Name" --serial "KI-26-AW-001"

    Batch from CSV (columns: name, serial [serial optional per row]):
        python gen_certificates.py --template blank.png --csv students.csv --prefix "KI-26-AW-" --start 1
"""

import argparse
import csv
import os
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Calibrated template constants -- do not change without re-calibrating
# against the actual blank.png design.
#
# Recalibrated 2026-08-09: the real blank.png supplied is 6250x4419px, the
# same KNOW-I/SVCE design as the original calibration but exported at
# ~3.906x resolution (aspect ratio matches to within 0.01%). Verified by
# pixel-scanning the actual image for the gold "presented to" underline
# (found at x=1392-4874, y=2273-2288) -- its center lines up with the
# proportionally-scaled name position within 0.25%, and the proportionally
# -scaled serial origin lands on blank reserved space. Values below are the
# original constants scaled by that measured ratio, not guessed.
# ---------------------------------------------------------------------------

CANVAS_SIZE = (6250, 4419)

NAME_CENTER = (3125, 2040)
NAME_FONT_SIZE = 172
NAME_COLOR = (30, 30, 30)

SERIAL_ORIGIN = (4930, 422)
SERIAL_FONT_SIZE = 117
SERIAL_COLOR = (20, 20, 20)
SERIAL_LETTER_SPACING = 12

SCRIPT_DIR = Path(__file__).resolve().parent
FONTS_DIR = SCRIPT_DIR / "fonts"

NAME_FONT_FILENAME = "Poppins-Regular.ttf"
SERIAL_FONT_FILENAME = "Poppins-Medium.ttf"


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def _candidate_font_paths(filename: str):
    """Locations to check for a required font file, in priority order."""
    candidates = [FONTS_DIR / filename]

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Microsoft" / "Windows" / "Fonts" / filename)

    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates.append(Path(windir) / "Fonts" / filename)

    return candidates


def load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """
    Load a required font by exact filename. Never falls back to a
    substitute font -- a silent substitution would visibly break the
    calibrated alignment. Raises a clear, actionable error instead.
    """
    for path in _candidate_font_paths(filename):
        if path.is_file():
            return ImageFont.truetype(str(path), size)

    searched = "\n".join(f"  - {p}" for p in _candidate_font_paths(filename))
    raise SystemExit(
        f"ERROR: Required font '{filename}' was not found.\n"
        f"Searched:\n{searched}\n\n"
        f"Fix: install {filename} on this machine, or place a copy of it in the\n"
        f"'fonts/' folder next to gen_certificates.py. See README.md for details.\n"
        f"This tool never substitutes a different font -- that would silently\n"
        f"break the calibrated text alignment."
    )


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_name(draw: ImageDraw.ImageDraw, name: str, font: ImageFont.FreeTypeFont) -> None:
    text = name.upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = NAME_CENTER[0] - text_width / 2 - bbox[0]
    y = NAME_CENTER[1] - text_height / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=NAME_COLOR)


def draw_serial(draw: ImageDraw.ImageDraw, serial: str, font: ImageFont.FreeTypeFont) -> None:
    x, y = SERIAL_ORIGIN
    for ch in serial:
        draw.text((x, y), ch, font=font, fill=SERIAL_COLOR)
        bbox = draw.textbbox((0, 0), ch, font=font)
        char_width = bbox[2] - bbox[0]
        if char_width == 0:
            char_width = font.getlength(ch)
        x += char_width + SERIAL_LETTER_SPACING


def render_certificate(template_path: Path, name: str, serial: str,
                        name_font: ImageFont.FreeTypeFont,
                        serial_font: ImageFont.FreeTypeFont) -> Image.Image:
    img = Image.open(template_path).convert("RGB")
    if img.size != CANVAS_SIZE:
        raise SystemExit(
            f"ERROR: Template '{template_path}' is {img.size[0]}x{img.size[1]}px, "
            f"but the calibration expects exactly {CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}px.\n"
            f"Using a differently-sized template will misplace the text."
        )
    draw = ImageDraw.Draw(img)
    draw_name(draw, name, name_font)
    draw_serial(draw, serial, serial_font)
    return img


# ---------------------------------------------------------------------------
# Output folder handling
# ---------------------------------------------------------------------------

def resolve_out_dir(out_dir_arg: str | None) -> Path:
    if out_dir_arg:
        folder_name = out_dir_arg
    else:
        folder_name = input(
            "Enter a folder name for this run (e.g. AgentWorkshop_Feb2026): "
        ).strip()
        if not folder_name:
            raise SystemExit("ERROR: A folder name is required.")

    out_dir = SCRIPT_DIR / "output" / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def safe_filename(name: str, serial: str) -> str:
    base = f"{name}_{serial}".strip()
    for ch in '<>:"/\\|?*':
        base = base.replace(ch, "_")
    return base + ".png"


def zip_folder(folder: Path) -> Path:
    zip_path = folder.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(folder.parent))
    return zip_path


# ---------------------------------------------------------------------------
# CSV / batch handling
# ---------------------------------------------------------------------------

def read_rows(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip().lower() for fn in (reader.fieldnames or [])]
        if "name" not in fieldnames:
            raise SystemExit("ERROR: CSV must have a 'name' column.")
        rows = []
        for raw_row in reader:
            row = {k.strip().lower(): (v.strip() if v else v) for k, v in raw_row.items()}
            rows.append(row)
        return rows


def run_batch(args) -> None:
    template_path = Path(args.template)
    csv_path = Path(args.csv)
    rows = read_rows(csv_path)

    name_font = load_font(NAME_FONT_FILENAME, NAME_FONT_SIZE)
    serial_font = load_font(SERIAL_FONT_FILENAME, SERIAL_FONT_SIZE)

    out_dir = resolve_out_dir(args.out_dir)

    counter = args.start
    generated = 0
    for row in rows:
        name = row.get("name") or ""
        if not name:
            print("WARNING: skipping row with blank name.", file=sys.stderr)
            continue

        serial = row.get("serial") or ""
        if not serial:
            serial = f"{args.prefix}{counter:03d}"
            counter += 1

        img = render_certificate(template_path, name, serial, name_font, serial_font)
        out_path = out_dir / safe_filename(name, serial)
        img.save(out_path)
        generated += 1
        print(f"Generated: {out_path.name}")

    zip_path = zip_folder(out_dir)
    print(f"\nDone. {generated} certificate(s) generated in {out_dir}")
    print(f"Zipped to {zip_path}")


def run_single(args) -> None:
    template_path = Path(args.template)

    name_font = load_font(NAME_FONT_FILENAME, NAME_FONT_SIZE)
    serial_font = load_font(SERIAL_FONT_FILENAME, SERIAL_FONT_SIZE)

    out_dir = resolve_out_dir(args.out_dir)

    img = render_certificate(template_path, args.name, args.serial, name_font, serial_font)
    out_path = out_dir / safe_filename(args.name, args.serial)
    img.save(out_path)
    print(f"Done. Certificate saved to {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="KNOW-I Certificate Generator")
    parser.add_argument("--template", required=True, help="Path to the blank certificate template PNG")
    parser.add_argument("--out-dir", default=None, help="Output folder name under output/ (skips interactive prompt)")

    parser.add_argument("--name", help="Student full name (single mode)")
    parser.add_argument("--serial", help="Serial number (single mode)")

    parser.add_argument("--csv", help="Path to CSV file with 'name' and optional 'serial' columns (batch mode)")
    parser.add_argument("--prefix", default="", help="Prefix for auto-generated serial numbers (batch mode)")
    parser.add_argument("--start", type=int, default=1, help="Starting counter for auto-generated serial numbers (batch mode)")

    args = parser.parse_args()

    if args.csv and (args.name or args.serial):
        parser.error("Use either --csv (batch mode) or --name/--serial (single mode), not both.")
    if not args.csv and not (args.name and args.serial):
        parser.error("Single mode requires --name and --serial. Batch mode requires --csv.")

    return args


def main():
    args = parse_args()
    if args.csv:
        run_batch(args)
    else:
        run_single(args)


if __name__ == "__main__":
    main()

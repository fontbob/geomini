#!/usr/bin/env python3
"""
Post-build patch for generated TTF/OTF under fonts/.

Older Fontspector / Font Bakery profiles may fail on:
  - copyright name records not matching OFL.txt line 1
  - missing Name ID 13 (license description) / 14 (license URL)

This script rewrites those entries from OFL.txt so CI or local QA matches the
packaged license without editing UFO sources. Latest Fontspector may not warn
about these, but the patch keeps binaries aligned with OFL.txt.

Usage (from repo root, venv active):
    python3 scripts/post_build_patch_fonts.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord


REPO_ROOT = Path(__file__).resolve().parent.parent
OFL_DEFAULT = REPO_ROOT / "OFL.txt"
FONT_GLOBS = (
    REPO_ROOT / "fonts" / "variable",
    REPO_ROOT / "fonts" / "ttf",
)

# Standard English entries we normalize (same as typical GF statics tooling).
_MAC_ENGLISH = (1, 0, 0)
_WIN_EN_US = (3, 1, 0x0409)


def _parse_ofl(path: Path) -> tuple[str, str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise ValueError(f"OFL.txt has no copyright line: {path}")

    copyright_line = lines[0].strip()

    license_lines: list[str] = []
    url_line = ""
    for i, raw in enumerate(lines[1:], start=1):
        s = raw.strip()
        if not s:
            if license_lines:
                break
            continue
        if s.startswith("---") or s.startswith("SIL OPEN FONT LICENSE"):
            break
        if s.startswith("http://") or s.startswith("https://"):
            url_line = s
            if license_lines:
                license_lines.append(s)
            break
        license_lines.append(s)

    if not license_lines:
        raise ValueError(f"Could not find license preamble in {path}")

    # If URL was on its own line, join as "FAQ at:\nURL" style is already in license_lines.
    license_description = "\n".join(license_lines).strip()
    if not url_line:
        m = re.search(r"https://[^\s]+", license_description)
        if m:
            url_line = m.group(0)

    if not url_line:
        raise ValueError(f"Could not find license URL in {path}")

    return copyright_line, license_description, url_line


def _should_replace_record(rec: NameRecord, name_ids: set[int]) -> bool:
    """True if this record is one we overwrite (Mac English + Windows en-US only)."""
    if rec.nameID not in name_ids:
        return False
    if rec.platformID == 1 and rec.platEncID == 0 and rec.langID == 0:
        return True
    if rec.platformID == 3 and rec.platEncID == 1 and rec.langID == 0x0409:
        return True
    return False


def _drop_name_records(name_table, name_ids: set[int]) -> None:
    name_table.names = [r for r in name_table.names if not _should_replace_record(r, name_ids)]


def _append_name(name_table, name_id: int, string: str) -> None:
    for platform_id, plat_enc_id, lang_id in (_MAC_ENGLISH, _WIN_EN_US):
        rec = NameRecord()
        rec.nameID = name_id
        rec.platformID = platform_id
        rec.platEncID = plat_enc_id
        rec.langID = lang_id
        rec.string = string
        name_table.names.append(rec)


def patch_font(path: Path, copyright_line: str, license_description: str, license_url: str) -> None:
    font = TTFont(path)
    try:
        name_table = font["name"]
        _drop_name_records(name_table, {0, 13, 14})
        _append_name(name_table, 0, copyright_line)
        _append_name(name_table, 13, license_description)
        _append_name(name_table, 14, license_url)
        font.save(path, reorderTables=True)
    finally:
        font.close()


def main() -> int:
    ofl_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else OFL_DEFAULT
    if not ofl_path.is_file():
        print(f"post_build_patch_fonts: skip (no OFL at {ofl_path})", file=sys.stderr)
        return 0

    try:
        copyright_line, license_description, license_url = _parse_ofl(ofl_path)
    except ValueError as e:
        print(f"post_build_patch_fonts: {e}", file=sys.stderr)
        return 1

    font_files: list[Path] = []
    for base in FONT_GLOBS:
        if not base.is_dir():
            continue
        font_files.extend(p for p in base.rglob("*") if p.suffix.lower() in (".ttf", ".otf"))

    if not font_files:
        print("post_build_patch_fonts: no fonts under fonts/variable or fonts/ttf", file=sys.stderr)
        return 0

    for fp in sorted(font_files):
        print(f"post_build_patch_fonts: patching {fp.relative_to(REPO_ROOT)}")
        patch_font(fp, copyright_line, license_description, license_url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

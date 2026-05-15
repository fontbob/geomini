#!/usr/bin/env python3
"""
Post-build patch for generated TTF/OTF under fonts/.

Older Fontspector / Font Bakery profiles may complain about missing license
records; this script adds only Name IDs 13 and 14. Copyright (Name ID 0) is
left as produced by UFO / fontmake.

Constants below must stay aligned with OFL.txt in this repo.

Usage (from repo root, venv active):
    python3 scripts/post_build_patch_fonts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord


REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_GLOBS = (
    REPO_ROOT / "fonts" / "variable",
    REPO_ROOT / "fonts" / "ttf",
)

# Name ID 13 — SIL preamble matching OFL.txt lines 3–5.
LICENSE_DESCRIPTION = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1.\n"
    "This license is copied below, and is also available with a FAQ at:\n"
    "https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"

_MAC_ENGLISH = (1, 0, 0)
_WIN_EN_US = (3, 1, 0x0409)


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


def patch_font(path: Path, license_description: str, license_url: str) -> None:
    font = TTFont(path)
    try:
        name_table = font["name"]
        _drop_name_records(name_table, {13, 14})
        _append_name(name_table, 13, license_description)
        _append_name(name_table, 14, license_url)
        font.save(path, reorderTables=True)
    finally:
        font.close()


def main() -> int:
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
        patch_font(fp, LICENSE_DESCRIPTION, LICENSE_URL)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

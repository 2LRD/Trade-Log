#!/usr/bin/env python3
"""
Build the Windows distribution zip for Trade Log.

Produces: dist/Trade Log <MM-DD-YYYY>.zip

The zip contains a single top-level folder "Trade Log" with exactly
these items (nothing else — no .venv, no stale zips, no dev files):

  Trade Log/
    app.py
    db.py
    ib_client.py
    requirements.txt
    launch.vbs
    INSTALL - Double-Click This First.bat
    PLEASE_READ_THIS_FIRST.txt
    DIAGNOSE - Run If Trade Log Won't Open.bat
    .streamlit/
      config.toml
    _uv/
      uv.exe
      uvw.exe
      uvx.exe

Usage:
    python build_windows_distribution.py
"""

import zipfile
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DIST_SRC   = SCRIPT_DIR / "dist" / "Trade Log"

# Files copied from the project root (not from dist/)
ROOT_FILES = [
    "app.py",
    "db.py",
    "ib_client.py",
    "requirements.txt",
]

# Files that live only in dist/Trade Log/
DIST_FILES = [
    "launch.vbs",
    "INSTALL - Double-Click This First.bat",
    "PLEASE_READ_THIS_FIRST.txt",
    "DIAGNOSE - Run If Trade Log Won't Open.bat",
]

# Folders copied recursively from dist/Trade Log/
DIST_FOLDERS = [
    ".streamlit",
    "_uv",
]


def build() -> None:
    output  = SCRIPT_DIR / "dist" / f"Trade Log {date.today().strftime('%#m-%#d-%Y')}.zip"

    print("=" * 60)
    print("  Trade Log — Windows Distribution Builder")
    print("=" * 60)
    print()

    missing = []

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ── Root-level source files ──────────────────────────────────────────
        for name in ROOT_FILES:
            src = SCRIPT_DIR / name
            if src.exists():
                zf.write(src, f"Trade Log/{name}")
                print(f"  + {name}")
            else:
                missing.append(name)
                print(f"  ! {name} — NOT FOUND (skipped)")

        # ── Dist-only flat files ─────────────────────────────────────────────
        for name in DIST_FILES:
            src = DIST_SRC / name
            if src.exists():
                zf.write(src, f"Trade Log/{name}")
                print(f"  + {name}")
            else:
                missing.append(name)
                print(f"  ! {name} — NOT FOUND (skipped)")

        # ── Dist folders (recursive) ─────────────────────────────────────────
        for folder in DIST_FOLDERS:
            folder_path = DIST_SRC / folder
            if not folder_path.exists():
                missing.append(folder)
                print(f"  ! {folder}/ — NOT FOUND (skipped)")
                continue
            for file in sorted(folder_path.rglob("*")):
                if file.is_file():
                    arc = "Trade Log/" + file.relative_to(DIST_SRC).as_posix()
                    zf.write(file, arc)
                    print(f"  + {arc}")

    size_kb = output.stat().st_size // 1024
    print()
    print(f"Done!  {output.name}  ({size_kb:,} KB)")

    if missing:
        print()
        print("  WARNING — these items were missing:")
        for m in missing:
            print(f"    - {m}")

    print()


if __name__ == "__main__":
    build()

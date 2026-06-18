#!/usr/bin/env python3
"""
Build the Mac distribution for Trade Log.

Produces: dist/Trade Log Mac.tar.gz

Bundles a universal uv binary (arm64 + x86_64) so end-users do NOT
need Python pre-installed.  uv downloads Python 3.12 and all
dependencies automatically on first launch.

Run this from Windows OR Mac — Python's tarfile module sets Unix
execute permissions correctly so the .app bundle works on Mac.

The uv binary is downloaded once and cached in dist/_uv_mac/.
Subsequent builds reuse the cache (no re-download needed).

Usage:
    python build_mac_distribution.py
"""

import io
import tarfile
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DIST_DIR   = SCRIPT_DIR / "dist"
OUTPUT     = DIST_DIR / "Trade Log Mac.tar.gz"
TOP        = "Trade Log Mac"
BUNDLE     = f"{TOP}/Trade Log.app/Contents"

# Separate binaries for Apple Silicon (arm64) and Intel (x86_64)
UV_MAC_URLS = {
    "arm64":  "https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-apple-darwin.tar.gz",
    "x86_64": "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-apple-darwin.tar.gz",
}
UV_MAC_CACHE = DIST_DIR / "_uv_mac"   # local cache dir (dist/ is gitignored)

# ── Launcher shell script ────────────────────────────────────────────────────
# Placed at: Trade Log.app/Contents/MacOS/launcher  (mode 0o755)
#
# What it does on FIRST launch:
#   1. Uses the bundled uv to install Python 3.12 (no system Python needed)
#   2. Creates a venv inside the .app bundle
#   3. Installs pip dependencies from requirements.txt
#
# On SUBSEQUENT launches:
#   • venv already exists → skips straight to starting Streamlit
#   • Kills any stale Streamlit on port 8502 first (safe to re-launch)
LAUNCHER = r"""#!/bin/bash
# Trade Log — Mac launcher
MACOS_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$(cd "$MACOS_DIR/../Resources" && pwd)"
VENV_DIR="$RESOURCES_DIR/.venv"
# Pick the right binary for this Mac's CPU
ARCH=$(uname -m)   # arm64 on Apple Silicon, x86_64 on Intel
UV_BIN="$RESOURCES_DIR/_uv/$ARCH/uv"
PORT=8502

alert() {
    osascript -e "display alert \"Trade Log\" message \"$*\" as critical \
        buttons {\"OK\"} default button \"OK\"" 2>/dev/null \
        || echo "ERROR: $*" >&2
}

# ── First-run setup ─────────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/python" ]; then

    if [ ! -f "$UV_BIN" ]; then
        alert "Setup tools are missing.\n\nPlease re-download Trade Log and try again."
        exit 1
    fi

    chmod +x "$UV_BIN"

    osascript -e 'display notification "Setting up Trade Log for the first time — this takes 1–2 minutes..." with title "Trade Log"' 2>/dev/null

    # Install Python 3.12 (downloaded by uv, no system Python needed)
    "$UV_BIN" python install 3.12 || {
        alert "Could not install Python 3.12.\n\nPlease check your internet connection and try again."
        exit 1
    }

    # Create virtual environment
    "$UV_BIN" venv --python 3.12 "$VENV_DIR" || {
        alert "Could not create a Python environment.\n\nPlease try again."
        exit 1
    }

    # Install Trade Log dependencies
    "$UV_BIN" pip install -r "$RESOURCES_DIR/requirements.txt" \
        --python "$VENV_DIR/bin/python" || {
        alert "Could not install dependencies.\n\nPlease check your internet connection and try again."
        rm -rf "$VENV_DIR"
        exit 1
    }

fi

# ── Kill any stale Streamlit on this port ───────────────────────────────────
lsof -ti ":$PORT" | xargs kill -9 2>/dev/null || true

# ── Launch Streamlit via the supervisor (background) ─────────────────────────
# launch.py picks a light/dark theme base matching the saved theme and relaunches
# Streamlit when the app requests a restart. On Quit we send it SIGTERM (below)
# and it tears down its Streamlit child.
"$VENV_DIR/bin/python" "$RESOURCES_DIR/launch.py" --port "$PORT" --no-browser &
STREAMLIT_PID=$!

# ── Open browser once Streamlit is ready ─────────────────────────────────────
sleep 5
open "http://localhost:$PORT"

# ── Show Quit dialog (keeps app "running" so user knows how to stop it) ───────
osascript -e 'display dialog "Trade Log is running in your browser.\n\nClick Quit to stop the app." \
    with title "Trade Log" buttons {"Quit"} default button "Quit" with icon note' 2>/dev/null \
    || read -r -p "Press Enter to quit Trade Log..." _

# ── Cleanup ──────────────────────────────────────────────────────────────────
kill "$STREAMLIT_PID" 2>/dev/null
wait "$STREAMLIT_PID" 2>/dev/null
"""

# ── Info.plist — identifies this as a macOS app bundle ──────────────────────
INFO_PLIST = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.tradelog.app</string>
    <key>CFBundleName</key>
    <string>Trade Log</string>
    <key>CFBundleDisplayName</key>
    <string>Trade Log</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
"""

SOURCE_FILES = [
    "app.py",
    "db.py",
    "ib_client.py",
    "updater.py",
    "launch.py",
    "requirements.txt",
    "VERSION",
]


# ── Tar helpers ──────────────────────────────────────────────────────────────

def add_str(tf: tarfile.TarFile, arcname: str, content: str, mode: int = 0o644) -> None:
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mode = mode
    tf.addfile(info, io.BytesIO(data))


def add_file(tf: tarfile.TarFile, arcname: str, src: Path, mode: int = 0o644) -> None:
    data = src.read_bytes()
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mode = mode
    tf.addfile(info, io.BytesIO(data))


def add_bytes(tf: tarfile.TarFile, arcname: str, data: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mode = mode
    tf.addfile(info, io.BytesIO(data))


# ── uv download / cache ──────────────────────────────────────────────────────

def get_uv_binary(arch: str) -> bytes:
    """Return the uv binary for the given arch, downloading and caching if needed."""
    cached = UV_MAC_CACHE / arch / "uv"
    if cached.exists():
        size_kb = cached.stat().st_size // 1024
        print(f"  [cached]   uv/{arch}/uv ({size_kb:,} KB)")
        return cached.read_bytes()

    url = UV_MAC_URLS[arch]
    print(f"  [download] uv for {arch} (one-time, ~15 MB)...")
    with urllib.request.urlopen(url) as resp:
        gz_data = resp.read()

    # Extract the 'uv' binary from the downloaded tar.gz
    import tarfile as _tf
    with _tf.open(fileobj=io.BytesIO(gz_data), mode="r:gz") as inner:
        for member in inner.getmembers():
            if member.name.split("/")[-1] == "uv" and not member.isdir():
                f = inner.extractfile(member)
                if f:
                    data = f.read()
                    cached.parent.mkdir(parents=True, exist_ok=True)
                    cached.write_bytes(data)
                    size_kb = len(data) // 1024
                    print(f"  [cached]   -> dist/_uv_mac/{arch}/uv ({size_kb:,} KB)")
                    return data

    raise RuntimeError(f"Could not find 'uv' binary inside {url}")


# ── Main build ───────────────────────────────────────────────────────────────

def build() -> None:
    DIST_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("  Trade Log — Mac Distribution Builder")
    print("=" * 60)
    print()

    print("Step 1: Fetching uv binaries (cached after first download):")
    uv_binaries = {arch: get_uv_binary(arch) for arch in UV_MAC_URLS}
    print()

    print("Step 2: Building tar.gz:")
    missing = []

    with tarfile.open(OUTPUT, "w:gz") as tf:

        # Launcher — executable
        add_str(tf, f"{BUNDLE}/MacOS/launcher", LAUNCHER, mode=0o755)
        print("  + MacOS/launcher")

        # App metadata
        add_str(tf, f"{BUNDLE}/Info.plist", INFO_PLIST)
        print("  + Info.plist")

        # Source files
        for name in SOURCE_FILES:
            src = SCRIPT_DIR / name
            if src.exists():
                add_file(tf, f"{BUNDLE}/Resources/{name}", src)
                print(f"  + Resources/{name}")
            else:
                missing.append(name)
                print(f"  ! {name} — NOT FOUND (skipped)")

        # Streamlit config
        config = SCRIPT_DIR / ".streamlit" / "config.toml"
        if config.exists():
            add_file(tf, f"{BUNDLE}/Resources/.streamlit/config.toml", config)
            print("  + Resources/.streamlit/config.toml")
        else:
            missing.append(".streamlit/config.toml")
            print("  ! .streamlit/config.toml — NOT FOUND (skipped)")

        # uv binaries — one per architecture, both executable
        for arch, data in uv_binaries.items():
            add_bytes(tf, f"{BUNDLE}/Resources/_uv/{arch}/uv", data, mode=0o755)
            print(f"  + Resources/_uv/{arch}/uv ({len(data) // 1024:,} KB)")

    size_kb = OUTPUT.stat().st_size // 1024
    print()
    print(f"Done!  {OUTPUT.name}  ({size_kb:,} KB)")

    if missing:
        print()
        print("  WARNING — these items were missing:")
        for m in missing:
            print(f"    - {m}")

    print()
    print("-" * 60)
    print("End-user install steps (share these with Mac users):")
    print()
    print("  1. Double-click 'Trade Log Mac.tar.gz' to extract")
    print("  2. Open the 'Trade Log Mac' folder")
    print("  3. Double-click 'Trade Log.app'")
    print("  4. macOS security prompt:")
    print("       macOS 12 or earlier:  right-click -> Open -> Open")
    print("       macOS 13-14:          right-click -> Open -> Open")
    print("       macOS 15 (Sequoia):   System Settings -> Privacy & Security")
    print("                             -> scroll down -> 'Open Anyway'")
    print("  5. First launch only: Trade Log installs itself (~1–2 min)")
    print("     No Python required — everything is included.")
    print("  6. Your browser opens Trade Log automatically.")
    print("  7. Click 'Quit' in the dialog to stop the app.")
    print("-" * 60)
    print()


if __name__ == "__main__":
    build()

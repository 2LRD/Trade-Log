#!/usr/bin/env bash
# Launch Trade Log (Linux). Deps installed to ~/.local via pip --user.
cd "$(dirname "$0")"
exec python3 -m streamlit run app.py --server.port 8501

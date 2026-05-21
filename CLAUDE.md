# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python -m streamlit run app.py
```

Runs on port 8502 (configured in `.streamlit/config.toml`).

## Architecture

Two-file app: `db.py` handles all persistence, `app.py` is the entire UI.

**`db.py`**
- Defines the SQLite schema inline as a `SCHEMA` string — `CREATE TABLE IF NOT EXISTS` so it's idempotent.
- `MIGRATIONS` list handles columns added after initial release. `init_db()` runs both the schema and migrations on every startup.
- `get_connection()` is a context manager: commits on success, rolls back on exception, always closes. Use it for every DB operation.
- Database file: `tradelog.db` next to the source files.

**`app.py`**
- Single-file Streamlit app. Execution flows top-to-bottom on every user interaction (Streamlit's model).
- Sidebar: tag management (add/delete tags used to categorize trades).
- Main area: Add Trade form → trade table → Edit Trade expander → Delete Trade expander.
- `euro_dates` toggle in sidebar controls date display format (MM/DD/YYYY vs DD/MM/YYYY) for the whole page via `fmt_date()`.
- Trade table is read-only (`st.dataframe`); editing is done via the separate Edit Trade expander with a selectbox to pick a trade by ticker + date + ID.
- Stop loss has two values: `opening_stop` (set at entry, never edited) and `current_stop` (editable, defaults to opening stop).
- Ctrl+Enter form submission is implemented via injected JS (`components.html(height=0)`), which intercepts keydown events on the parent document.

## Schema

```
trades: id, entry_date(TEXT ISO), ticker, quantity, entry_price, exit_date, exit_price, notes, stop_enabled, opening_stop, current_stop
tags: id, name(UNIQUE), description
trade_tags: trade_id → trades, tag_id → tags  (cascade delete)
```

Dates stored as ISO 8601 strings (`YYYY-MM-DD`). All price/quantity values stored as REAL.

## Adding schema changes

Add new columns to the `MIGRATIONS` list in `db.py` — never alter `SCHEMA` for existing columns. The migration runner checks `PRAGMA table_info` before each `ALTER TABLE`, so it's safe to run repeatedly.

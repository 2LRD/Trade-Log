"""
seed_demo.py — recreate demo/tradelog_demo.db with realistic dummy data.

Run directly:    python seed_demo.py
Run via launcher: launch_demo.bat calls this automatically before starting Streamlit.

The demo DB is committed to GitHub (it contains no real personal data).
"""
import os
import sys
import sqlite3
import random
import math
from pathlib import Path
from datetime import date, timedelta

DEMO_DB = Path(__file__).parent / "demo" / "tradelog_demo.db"
DEMO_DB.parent.mkdir(exist_ok=True)

# Point db.py at the demo database so init_db() builds the right schema
os.environ["TRADELOG_DB"] = str(DEMO_DB)

# Remove existing demo DB to start fresh every time
if DEMO_DB.exists():
    DEMO_DB.unlink()

# Import after setting the env var so DB_PATH resolves to the demo file
sys.path.insert(0, str(Path(__file__).parent))
from db import init_db, get_connection  # noqa: E402

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

def iso(d: date) -> str:
    return d.isoformat()

def bday(d: date, n: int) -> date:
    """Advance d by n business days."""
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    while remaining:
        d += timedelta(days=step)
        if d.weekday() < 5:
            remaining -= 1
    return d

TODAY = date(2026, 5, 20)
START = date(2025, 11, 3)   # ~6 months of history

random.seed(42)             # reproducible data

# ── Tags ─────────────────────────────────────────────────────────────────────

TAGS = [
    ("Breakout",       "Price breaks above a key resistance level"),
    ("Earnings Play",  "Trade around a scheduled earnings release"),
    ("Mean Reversion", "Fade an extended move back toward the average"),
    ("Swing",          "Multi-day swing trade"),
    ("Options Income", "Sell premium for income (spreads, covered calls)"),
    ("High Conviction","Thesis with multiple confirming factors"),
    ("Speculative",    "Higher-risk, smaller position size"),
    ("Sector Rotation","Capital flowing into an underweighted sector"),
]

with get_connection() as conn:
    for name, desc in TAGS:
        conn.execute("INSERT OR IGNORE INTO tags (name, description) VALUES (?,?)", (name, desc))

with get_connection() as conn:
    tag_rows = conn.execute("SELECT id, name FROM tags").fetchall()
tag_id = {row["name"]: row["id"] for row in tag_rows}

# ── Settings ──────────────────────────────────────────────────────────────────

SETTINGS = {
    "account_balance":      "185000",
    "starting_equity":      "150000",
    "starting_date":        iso(START),
    "euro_dates":           "0",
    "app_mode":             "demo",
    "native_currency":      "USD",
    "currency_mode":        "0",
    "pct_account_yellow":   "5",
    "pct_account_red":      "10",
    "stop_dist_unit":       "%",
    "stop_dist_yellow":     "5",
    "stop_dist_red":        "2",
    "row_color_enabled":    "1",
    "row_color_style":      "text",
    "color_open_profit":    "#2ecc71",
    "color_open_loss":      "#e74c3c",
    "color_closed_profit":  "#27ae60",
    "color_closed_loss":    "#c0392b",
    "default_commission":   "0",
    "options_commission":   "0.65",
    "futures_commission":   "2.25",
    "broker":               "ib",
    "ib_host":              "127.0.0.1",
    "ib_port":              "7497",
    "ib_client_id":         "1",
    "ib_use_live_prices":   "0",
    "ib_auto_sync_balance": "0",
    "ib_auto_connect":      "0",
}

with get_connection() as conn:
    for k, v in SETTINGS.items():
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, v)
        )

# ── Closed stock trades ───────────────────────────────────────────────────────

def add_trade(conn, **kw) -> int:
    cols = list(kw.keys())
    vals = list(kw.values())
    placeholders = ",".join("?" * len(cols))
    col_str = ",".join(cols)
    cur = conn.execute(
        f"INSERT INTO trades ({col_str}) VALUES ({placeholders})", vals
    )
    return cur.lastrowid


def tag_trade(conn, trade_id: int, *tag_names):
    for name in tag_names:
        tid = tag_id.get(name)
        if tid:
            conn.execute(
                "INSERT OR IGNORE INTO trade_tags (trade_id, tag_id) VALUES (?,?)",
                (trade_id, tid),
            )

CLOSED_STOCKS = [
    # (ticker, entry_date_offset_from_START, hold_days, entry, exit, qty, stop, tags, side)
    ("AAPL",  0,  18, 230.50, 248.20, 50,  220.00, ["Breakout", "High Conviction"], "long"),
    ("MSFT",  5,  12, 415.00, 398.50, 30,  400.00, ["Swing"],                       "long"),
    ("NVDA",  8,  25, 875.00, 940.00, 20,  840.00, ["Breakout", "High Conviction"], "long"),
    ("META",  15, 10, 580.00, 605.00, 25,  555.00, ["Swing"],                       "long"),
    ("AMZN",  20, 30, 220.00, 215.00, 40,  208.00, ["Swing"],                       "long"),
    ("TSLA",  22, 8,  350.00, 310.00, 30,  325.00, ["Speculative"],                 "long"),
    ("GOOG",  30, 20, 195.00, 208.00, 35,  185.00, ["Breakout"],                    "long"),
    ("AMD",   35, 15, 155.00, 170.00, 60,  145.00, ["Breakout", "Sector Rotation"], "long"),
    ("JPM",   40, 22, 235.00, 248.00, 45,  225.00, ["Swing", "High Conviction"],    "long"),
    ("XOM",   42, 14, 118.00, 112.00, 70,  112.00, ["Sector Rotation"],             "long"),
    ("NFLX",  50, 18, 890.00, 945.00, 12,  855.00, ["Earnings Play"],               "long"),
    ("CRM",   55, 12, 310.00, 335.00, 32,  295.00, ["Breakout"],                    "long"),
    ("LLY",   60, 30, 760.00, 810.00, 15,  735.00, ["High Conviction"],             "long"),
    ("UNH",   65, 25, 520.00, 498.00, 20,  498.00, ["Swing"],                       "long"),
    ("GS",    70, 10, 578.00, 598.00, 22,  560.00, ["Swing"],                       "long"),
    ("SHOP",  75, 20, 115.00, 128.00, 80,  108.00, ["Breakout"],                    "long"),
    ("COIN",  80, 12, 280.00, 255.00, 35,  258.00, ["Speculative"],                 "long"),
    ("PLTR",  85, 15, 82.00,  95.00,  100, 76.00,  ["Breakout", "High Conviction"], "long"),
    ("MU",    90, 18, 108.00, 118.00, 55,  100.00, ["Sector Rotation"],             "long"),
    ("UBER",  95, 22, 82.00,  90.00,  75,  76.00,  ["Swing"],                       "long"),
    # A couple of short sells
    ("RIVN", 100, 14, 15.50,  12.80,  200, 17.00,  ["Speculative"],                 "short"),
    ("BYND",  110, 10, 7.50,   5.20,  300, 9.00,   ["Mean Reversion"],              "short"),
]

with get_connection() as conn:
    for row in CLOSED_STOCKS:
        ticker, offset, hold, ep, xp, qty, stop, tags, side = row
        ed = bday(START, offset)
        xd = bday(ed, hold)
        commission = round(qty * 0.005, 2)
        pnl_dir = 1 if side == "long" else -1
        tid = add_trade(
            conn,
            entry_date=iso(ed),
            ticker=ticker,
            quantity=qty,
            entry_price=ep,
            exit_date=iso(xd),
            exit_price=xp,
            instrument_type="stock",
            side=side,
            opening_stop=stop,
            current_stop=stop,
            stop_enabled=1,
            commission=commission,
            notes=f"Demo trade — {ticker}",
        )
        tag_trade(conn, tid, *tags)

# ── Open stock positions ──────────────────────────────────────────────────────

OPEN_STOCKS = [
    ("AAPL",  -30, 195.00, 50,  185.00, 190.00, ["Breakout", "High Conviction"], "long"),
    ("NVDA",  -25, 1050.0, 15, 1000.00, 1020.00, ["High Conviction"],            "long"),
    ("META",  -20, 600.00, 20,  580.00, 595.00, ["Swing"],                       "long"),
    ("AMZN",  -18, 225.00, 40,  215.00, 220.00, ["Breakout"],                    "long"),
    ("MSFT",  -15, 430.00, 25,  415.00, 425.00, ["High Conviction"],             "long"),
    ("PLTR",  -12, 95.00, 100,   88.00, 92.00,  ["Breakout"],                    "long"),
    ("GS",    -10, 590.00, 18,  570.00, 585.00, ["Swing"],                       "long"),
    ("TSLA",   -8, 330.00, 30,  318.00, 325.00, ["Speculative"],                 "long"),
]

with get_connection() as conn:
    for ticker, offset, ep, qty, stop, cur_stop, tags, side in OPEN_STOCKS:
        ed = bday(TODAY, offset)
        commission = round(qty * 0.005, 2)
        tid = add_trade(
            conn,
            entry_date=iso(ed),
            ticker=ticker,
            quantity=qty,
            entry_price=ep,
            instrument_type="stock",
            side=side,
            opening_stop=stop,
            current_stop=cur_stop,
            stop_enabled=1,
            commission=commission,
            notes=f"Demo open position — {ticker}",
        )
        tag_trade(conn, tid, *tags)

# ── Closed options trades (two spreads + two single-leg) ─────────────────────

def add_option_leg(conn, ticker, ed, xd, side, qty, ep, xp, strike, expiry, opt_type, leg_group, leg_label, mult=100):
    commission = round(qty * 0.65, 2)
    return add_trade(
        conn,
        entry_date=iso(ed),
        ticker=ticker,
        quantity=qty,
        entry_price=ep,
        exit_date=iso(xd),
        exit_price=xp,
        instrument_type="option",
        side=side,
        opening_stop=None,
        current_stop=None,
        stop_enabled=0,
        strike=strike,
        expiration=iso(expiry),
        option_type=opt_type,
        multiplier=mult,
        leg_group=leg_group,
        leg_label=leg_label,
        commission=commission,
        notes="Demo options trade",
    )

import uuid

# Bull call spread: AAPL
grp1 = str(uuid.uuid4())[:8]
spread_ed = bday(START, 60)
spread_xd = bday(spread_ed, 20)
expiry1 = bday(spread_ed, 30)
with get_connection() as conn:
    id1 = add_option_leg(conn, "AAPL", spread_ed, spread_xd, "long",  5, 4.50, 8.20, 230.0, expiry1, "call", grp1, "Long Call $230")
    id2 = add_option_leg(conn, "AAPL", spread_ed, spread_xd, "short", 5, 1.80, 0.30, 240.0, expiry1, "call", grp1, "Short Call $240")
    tag_trade(conn, id1, "Options Income", "Breakout")
    tag_trade(conn, id2, "Options Income", "Breakout")

# Bear put spread: SPY
grp2 = str(uuid.uuid4())[:8]
spread_ed2 = bday(START, 90)
spread_xd2 = bday(spread_ed2, 15)
expiry2 = bday(spread_ed2, 25)
with get_connection() as conn:
    id3 = add_option_leg(conn, "SPY", spread_ed2, spread_xd2, "long",  10, 3.20, 5.80, 590.0, expiry2, "put", grp2, "Long Put $590")
    id4 = add_option_leg(conn, "SPY", spread_ed2, spread_xd2, "short", 10, 1.10, 0.20, 580.0, expiry2, "put", grp2, "Short Put $580")
    tag_trade(conn, id3, "Mean Reversion")
    tag_trade(conn, id4, "Mean Reversion")

# Single-leg calls: earnings plays
single_ed1 = bday(START, 45)
single_xd1 = bday(single_ed1, 5)
expiry_s1 = bday(single_ed1, 10)
with get_connection() as conn:
    id5 = add_option_leg(conn, "NFLX", single_ed1, single_xd1, "long", 3, 12.50, 28.00, 900.0, expiry_s1, "call", None, None)
    tag_trade(conn, id5, "Earnings Play", "High Conviction")

single_ed2 = bday(START, 110)
single_xd2 = bday(single_ed2, 5)
expiry_s2 = bday(single_ed2, 10)
with get_connection() as conn:
    id6 = add_option_leg(conn, "META", single_ed2, single_xd2, "long", 4, 8.00, 3.50, 620.0, expiry_s2, "put", None, None)
    tag_trade(conn, id6, "Speculative")

# ── Open options (bull call spread on MSFT) ───────────────────────────────────

grp3 = str(uuid.uuid4())[:8]
opt_ed = bday(TODAY, -10)
opt_exp = bday(TODAY, 20)
with get_connection() as conn:
    id7 = add_trade(
        conn,
        entry_date=iso(opt_ed),
        ticker="MSFT",
        quantity=8,
        entry_price=5.20,
        instrument_type="option",
        side="long",
        opening_stop=None,
        current_stop=None,
        stop_enabled=0,
        strike=440.0,
        expiration=iso(opt_exp),
        option_type="call",
        multiplier=100,
        leg_group=grp3,
        leg_label="Long Call $440",
        commission=round(8 * 0.65, 2),
        notes="Demo open option",
    )
    id8 = add_trade(
        conn,
        entry_date=iso(opt_ed),
        ticker="MSFT",
        quantity=8,
        entry_price=2.10,
        instrument_type="option",
        side="short",
        opening_stop=None,
        current_stop=None,
        stop_enabled=0,
        strike=450.0,
        expiration=iso(opt_exp),
        option_type="call",
        multiplier=100,
        leg_group=grp3,
        leg_label="Short Call $450",
        commission=round(8 * 0.65, 2),
        notes="Demo open option",
    )
    tag_trade(conn, id7, "Options Income", "High Conviction")
    tag_trade(conn, id8, "Options Income", "High Conviction")

# ── Equity curve (daily NAV for ~6 months) ───────────────────────────────────

def generate_equity_curve(start: date, end: date, start_balance: float) -> list[tuple]:
    """Simulate a realistic equity curve with growth, drawdowns, and contributions."""
    rows = []
    balance = start_balance
    d = start
    prev_peak = balance
    in_drawdown = False
    drawdown_dur = 0

    while d <= end:
        if d.weekday() >= 5:
            d += timedelta(days=1)
            continue

        # Monthly contribution on the 1st of each month
        contributions = 2500.0 if d.day == 1 else 0.0
        withdrawals   = 0.0

        # Gentle upward drift with noise
        daily_return = random.gauss(0.0008, 0.012)

        # Occasional drawdown periods
        if not in_drawdown and random.random() < 0.04:
            in_drawdown = True
            drawdown_dur = random.randint(5, 20)
        if in_drawdown:
            daily_return -= 0.008
            drawdown_dur -= 1
            if drawdown_dur <= 0:
                in_drawdown = False

        balance = balance * (1 + daily_return) + contributions - withdrawals
        balance = max(balance, start_balance * 0.7)  # floor

        rows.append((iso(d), round(balance, 2), contributions, withdrawals))
        d += timedelta(days=1)

    return rows

equity_rows = generate_equity_curve(START, TODAY, 150_000.0)

with get_connection() as conn:
    conn.executemany(
        "INSERT OR REPLACE INTO equity_entries (date, balance, contributions, withdrawals) VALUES (?,?,?,?)",
        equity_rows,
    )

# ── Cash transactions ─────────────────────────────────────────────────────────

cash_txns = []
d = START
while d <= TODAY:
    if d.day == 1 and d.weekday() < 5:
        cash_txns.append((iso(d), "deposit", 2500.0, "Monthly contribution", "manual"))
    d += timedelta(days=1)

# A couple of manual deposits
cash_txns.append((iso(bday(START, 5)), "deposit", 10000.0, "Initial transfer", "manual"))
cash_txns.append((iso(bday(START, 90)), "deposit", 5000.0, "Extra contribution", "manual"))

with get_connection() as conn:
    conn.executemany(
        "INSERT INTO cash_transactions (date, type, amount, description, source) VALUES (?,?,?,?,?)",
        cash_txns,
    )

# ── Trading plans ─────────────────────────────────────────────────────────────

PLANS = [
    {
        "ticker": "AAPL", "sentiment": "Bullish",
        "rationale": "Breaking out of a 3-month base on high volume. iPhone cycle upgrade expected to drive earnings beat.",
        "fundamentals": "P/E 28x, services segment growing 15% YoY, $100B buyback program intact.",
        "technicals": "Weekly close above $228 resistance. RSI 58 — room to run. 50-day MA trending up.",
        "trade_type": "Swing", "hold_time": "2–4 weeks",
        "entry_signal": "Daily close above $230 on volume > 20-day avg",
        "confirm1": "SPY holding above 200-day MA",
        "confirm2": "No major macro events in hold period",
        "entry_price": 230.50, "profit_target": 255.00, "stop_loss": 220.00, "rr_ratio": 2.4,
    },
    {
        "ticker": "NVDA", "sentiment": "Bullish",
        "rationale": "AI infrastructure spending accelerating. Blackwell GPU demand exceeding supply.",
        "fundamentals": "Revenue +78% YoY, data center segment now 80% of revenue. Forward P/E 35x.",
        "technicals": "Tight consolidation at all-time highs. Bollinger Bands squeezing. Cup-and-handle forming.",
        "trade_type": "Momentum", "hold_time": "3–6 weeks",
        "entry_signal": "Break and hold above $880 on daily close",
        "confirm1": "SOX semiconductor index trending up",
        "confirm2": "No negative guidance from major hyperscalers",
        "entry_price": 875.00, "profit_target": 980.00, "stop_loss": 840.00, "rr_ratio": 3.0,
    },
    {
        "ticker": "SPY", "sentiment": "Bearish",
        "rationale": "Market extended after 12-week rally. VIX compression + overbought conditions.",
        "fundamentals": "S&P 500 forward P/E 22x — above 10-year average. Earnings growth slowing.",
        "technicals": "RSI 72 on weekly. Prior resistance at 600. Volume declining on up days.",
        "trade_type": "Options Play", "hold_time": "2–3 weeks",
        "entry_signal": "Daily close below 20-day MA",
        "confirm1": "Yield curve widening",
        "confirm2": "Put/call ratio rising",
        "entry_price": 595.00, "profit_target": 570.00, "stop_loss": 605.00, "rr_ratio": 2.5,
    },
    {
        "ticker": "MSFT", "sentiment": "Bullish",
        "rationale": "Azure cloud growth re-accelerating. Copilot monetization beginning to show in numbers.",
        "fundamentals": "Revenue +16% YoY, operating margin 45%. AI integration across all products.",
        "technicals": "Breakout above $430 on weekly chart. Prior ATH becomes support.",
        "trade_type": "Swing", "hold_time": "3–5 weeks",
        "entry_signal": "Hold above $430 for 3 days on daily",
        "confirm1": "Tech sector (XLK) holding 50-day MA",
        "confirm2": "No Fed rate shock",
        "entry_price": 430.00, "profit_target": 475.00, "stop_loss": 415.00, "rr_ratio": 3.0,
    },
]

import datetime as _dt
with get_connection() as conn:
    for i, plan in enumerate(PLANS):
        saved = _dt.datetime.combine(
            bday(START, i * 20), _dt.time(9, 30)
        ).isoformat(sep=" ")
        conn.execute(
            """INSERT INTO trading_plans
               (saved_at, ticker, sentiment, rationale, fundamentals, technicals,
                trade_type, hold_time, entry_signal, confirm1, confirm2,
                entry_price, profit_target, stop_loss, rr_ratio)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (saved, plan["ticker"], plan["sentiment"], plan["rationale"],
             plan["fundamentals"], plan["technicals"], plan["trade_type"],
             plan["hold_time"], plan["entry_signal"], plan["confirm1"],
             plan["confirm2"], plan["entry_price"], plan["profit_target"],
             plan["stop_loss"], plan["rr_ratio"]),
        )

# ── Done ──────────────────────────────────────────────────────────────────────

with get_connection() as conn:
    n_trades   = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    n_equity   = conn.execute("SELECT COUNT(*) FROM equity_entries").fetchone()[0]
    n_plans    = conn.execute("SELECT COUNT(*) FROM trading_plans").fetchone()[0]
    n_tags     = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    n_cash     = conn.execute("SELECT COUNT(*) FROM cash_transactions").fetchone()[0]

print(f"Demo DB seeded: {n_trades} trades | {n_equity} equity entries | "
      f"{n_plans} plans | {n_tags} tags | {n_cash} cash transactions")
print(f"  -> {DEMO_DB}")

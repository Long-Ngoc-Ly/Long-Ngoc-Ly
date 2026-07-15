"""
HPG Thesis — RIGHT-side data fetch
Symbols : HPG, HSG, NKG, TVN (peer), VNINDEX (benchmark)
Output  : Console tables  +  hpg_thesis_data.xlsx
Run on LOCAL machine (cloud proxy blocks VN financial APIs)
"""

import os, sys, warnings, time
from datetime import date
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

try:
    from vnstock import Market, register_user
except ImportError:
    os.system(f"{sys.executable} -m pip install -U vnstock -q")
    from vnstock import Market, register_user

register_user(api_key="vnstock_3197cb8f57617c4bea9e114349132d30")
market = Market()

# ─── CONFIG ───────────────────────────────────────────────────────────────────
START      = "2022-07-01"      # ~3 years → đủ MA200 + đỉnh/đáy dài hạn
END        = date.today().isoformat()
EQUITY_SYM = ["HPG", "HSG", "NKG", "TVN"]
INDEX_SYM  = "VNINDEX"
WINDOWS    = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}

# ─── HELPERS — column detection ───────────────────────────────────────────────
def _col(df, keyword):
    return next((c for c in df.columns if keyword.lower() in c.lower()), None)

def _get(df, keyword):
    c = _col(df, keyword)
    return df[c] if c else None

def _close(df):  return _get(df, "close") or df.iloc[:, 4]
def _volume(df): return _get(df, "volume") or df.iloc[:, 5]
def _dates(df):
    c = _col(df, "time") or _col(df, "date")
    s = df[c] if c else df.iloc[:, 0]
    return s.astype(str).str[:10]

# ─── HELPERS — indicators ─────────────────────────────────────────────────────
def calc_rsi(cl, p=14):
    d = cl.diff()
    g = d.clip(lower=0).ewm(com=p-1, min_periods=p).mean()
    l = (-d.clip(upper=0)).ewm(com=p-1, min_periods=p).mean()
    rsi = 100 - 100 / (1 + g / l.replace(0, np.nan))
    return rsi, rsi.rolling(p).mean()

def calc_macd(cl, fast=12, slow=26, sig=9):
    line   = cl.ewm(span=fast, adjust=False).mean() - cl.ewm(span=slow, adjust=False).mean()
    signal = line.ewm(span=sig, adjust=False).mean()
    return line, signal, line - signal

def calc_bb(cl, p=20, k=2):
    mid = cl.rolling(p).mean()
    std = cl.rolling(p).std()
    return mid - k*std, mid, mid + k*std

def zscore_last(cl, w):
    m = cl.rolling(w).mean(); s = cl.rolling(w).std()
    return round(((cl - m) / s).iloc[-1], 2)

def pct_chg(series, n):
    if len(series) < n + 1:
        return None
    return round((series.iloc[-1] / series.iloc[-(n+1)] - 1) * 100, 2)

def week52(df):
    cl = _close(df); dt = _dates(df)
    sub_cl = cl.tail(252); sub_dt = dt.tail(252)
    hi = sub_cl.idxmax(); lo = sub_cl.idxmin()
    return (round(sub_cl[hi], 1), sub_dt[hi],
            round(sub_cl[lo], 1), sub_dt[lo])

def align_series(df_a, df_b):
    """Return two pd.Series aligned on common dates."""
    da = _dates(df_a); db = _dates(df_b)
    ca = _close(df_a).rename("a"); cb = _close(df_b).rename("b")
    ta = pd.concat([da.rename("d"), ca], axis=1).set_index("d")
    tb = pd.concat([db.rename("d"), cb], axis=1).set_index("d")
    merged = ta.join(tb, how="inner").sort_index()
    return merged["a"].reset_index(drop=True), merged["b"].reset_index(drop=True)

# ─── FETCH ────────────────────────────────────────────────────────────────────
raw = {}
print(f"\n{'='*62}")
print(f"  Fetching OHLCV  {START} → {END}")
print(f"{'='*62}")

for sym in EQUITY_SYM:
    try:
        df = market.equity(sym).ohlcv(start=START, end=END, count=900)
        df = df.sort_values(df.columns[0]).reset_index(drop=True)
        raw[sym] = df
        print(f"  [OK]   {sym:8s}  {len(df):>4} bars   last={_dates(df).iloc[-1]}")
    except Exception as e:
        print(f"  [FAIL] {sym}: {str(e)[:80]}")
    time.sleep(0.5)

# VNINDEX — try index API first, fall back to equity
for method in ("index", "equity"):
    try:
        fn  = getattr(market, method)
        df  = fn(INDEX_SYM).ohlcv(start=START, end=END, count=900)
        df  = df.sort_values(df.columns[0]).reset_index(drop=True)
        raw[INDEX_SYM] = df
        print(f"  [OK]   {INDEX_SYM:8s}  {len(df):>4} bars   last={_dates(df).iloc[-1]}  (via {method})")
        break
    except Exception as e:
        if method == "equity":
            print(f"  [FAIL] {INDEX_SYM}: {str(e)[:80]}")
    time.sleep(0.5)

if not raw:
    print("\n[ERROR] No data fetched — run on local machine.")
    sys.exit(1)

# ─── SECTION C — HPG Technical Indicators ────────────────────────────────────
print(f"\n{'='*62}")
print("  SECTION C  —  HPG Technical Indicators")
print(f"{'='*62}")

df_c = pd.DataFrame()
if "HPG" in raw:
    h   = raw["HPG"]
    cl  = _close(h).reset_index(drop=True)
    vol = _volume(h).reset_index(drop=True)
    last_date  = _dates(h).iloc[-1]
    last_close = round(cl.iloc[-1], 1)

    rsi_s, rsi_sma = calc_rsi(cl)
    ml, ms, mh     = calc_macd(cl)
    ma20           = cl.rolling(20).mean()
    ma50           = cl.rolling(50).mean()
    ma200          = cl.rolling(200).mean()
    bbl, bbm, bbu  = calc_bb(cl)
    vol_sma20      = vol.rolling(20).mean()
    hi52, hd, lo52, ld = week52(h)

    above = lambda ma: "above" if last_close > ma.iloc[-1] else "below"
    bb_pct = round((last_close - bbl.iloc[-1]) / (bbu.iloc[-1] - bbl.iloc[-1]) * 100, 1)
    bb_pos = ("ABOVE upper band" if last_close > bbu.iloc[-1] else
              "BELOW lower band" if last_close < bbl.iloc[-1] else "within bands")
    vol_ratio = round(vol.iloc[-1] / vol_sma20.iloc[-1], 2)
    macd_trend = "rising" if ml.iloc[-1] > ml.iloc[-5] else "falling"

    rows = [
        # ── RSI
        ("RSI(14)",             round(rsi_s.iloc[-1], 2),           last_date),
        ("RSI SMA(14)",         round(rsi_sma.iloc[-1], 2),         last_date),
        # ── MACD
        ("MACD line (12,26)",   round(ml.iloc[-1], 2),              last_date),
        ("MACD signal (9)",     round(ms.iloc[-1], 2),              last_date),
        ("MACD histogram",      round(mh.iloc[-1], 2),              last_date),
        ("MACD 5-bar trend",    macd_trend,                         last_date),
        # ── MA
        ("MA20",                round(ma20.iloc[-1], 1),            last_date),
        ("MA50",                round(ma50.iloc[-1], 1),            last_date),
        ("MA200",               round(ma200.iloc[-1], 1),           last_date),
        ("Price vs MA20",       above(ma20),                        last_date),
        ("Price vs MA50",       above(ma50),                        last_date),
        ("Price vs MA200",      above(ma200),                       last_date),
        # ── Bollinger Bands
        ("BB lower (20,2)",     round(bbl.iloc[-1], 1),             last_date),
        ("BB mid",              round(bbm.iloc[-1], 1),             last_date),
        ("BB upper",            round(bbu.iloc[-1], 1),             last_date),
        ("BB position",         bb_pos,                             last_date),
        ("BB %B",               f"{bb_pct}%",                       last_date),
        # ── Volume
        ("Volume (last bar)",   f"{int(vol.iloc[-1]):,}",           last_date),
        ("Volume SMA20",        f"{int(vol_sma20.iloc[-1]):,}",     last_date),
        ("Volume vs SMA20",     f"{vol_ratio}x",                    last_date),
        # ── 52-week
        ("52w High",            f"{hi52:,.0f}",                     hd),
        ("52w Low",             f"{lo52:,.0f}",                     ld),
        # ── Z-score
        ("Z-score (60d)",       zscore_last(cl, 60),                last_date),
        ("Z-score (120d)",      zscore_last(cl, 120),               last_date),
        ("Z-score (252d)",      zscore_last(cl, 252),               last_date),
        # ── meta
        ("Close",               last_close,                         last_date),
        ("Total bars",          len(h),                             "—"),
    ]
    df_c = pd.DataFrame(rows, columns=["Indicator", "Value", "Data date"])
    print(df_c.to_string(index=False))

# ─── SECTION D — Relative Strength ───────────────────────────────────────────
print(f"\n{'='*62}")
print("  SECTION D  —  Relative Strength")
print(f"{'='*62}")

def rs_block(sa, sb, label_a, label_b):
    rows = []
    for tag, n in WINDOWS.items():
        pa = pct_chg(sa, n); pb = pct_chg(sb, n)
        diff = round(pa - pb, 2) if (pa is not None and pb is not None) else None
        rows.append({
            "Window":              tag,
            label_a:              (f"{pa:+.2f}%" if pa is not None else "n/a"),
            label_b:              (f"{pb:+.2f}%" if pb is not None else "n/a"),
            f"Alpha ({label_a}-{label_b})": (f"{diff:+.2f}pp" if diff is not None else "n/a"),
        })
    return pd.DataFrame(rows)

# D1 — HPG vs VNINDEX
print("\n  D1.  HPG vs VNINDEX")
if "HPG" in raw and INDEX_SYM in raw:
    sa, sb = align_series(raw["HPG"], raw[INDEX_SYM])
    print(rs_block(sa, sb, "HPG", "VNINDEX").to_string(index=False))
else:
    print("  skipped — missing HPG or VNINDEX data")

# D2 — HPG vs peers
for peer in ["HSG", "NKG", "TVN"]:
    print(f"\n  D2.  HPG vs {peer}")
    if "HPG" in raw and peer in raw:
        sa, sb = align_series(raw["HPG"], raw[peer])
        print(rs_block(sa, sb, "HPG", peer).to_string(index=False))
    else:
        print(f"  skipped — {peer} not fetched (UPCoM cảnh báo hoặc API không có)")

# ─── SECTION B — Snapshot last bar ───────────────────────────────────────────
print(f"\n{'='*62}")
print("  SECTION B  —  Latest OHLCV bar per symbol")
print(f"{'='*62}")

snap = []
for sym, df in raw.items():
    r = df.iloc[-1]
    snap.append({
        "Symbol":  sym,
        "Date":    _dates(df).iloc[-1],
        "Open":    round(float(r.get(_col(df,"open"),  0)), 1),
        "High":    round(float(r.get(_col(df,"high"),  0)), 1),
        "Low":     round(float(r.get(_col(df,"low"),   0)), 1),
        "Close":   round(float(r.get(_col(df,"close"), 0)), 1),
        "Volume":  int(r.get(_col(df,"volume"), 0)),
        "Bars":    len(df),
        "Source":  "vnstock KBS (end-of-day, T+0 close)",
    })

df_snap = pd.DataFrame(snap)
print(df_snap.to_string(index=False))

# ─── EXPORT Excel ─────────────────────────────────────────────────────────────
out = "hpg_thesis_data.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as xl:
    df_snap.to_excel(xl, sheet_name="B_snapshot",     index=False)
    if not df_c.empty:
        df_c.to_excel(xl,  sheet_name="C_HPG_indicators", index=False)
    for sym, df in raw.items():
        df.to_excel(xl, sheet_name=sym[:31], index=False)

print(f"\n[DONE] Exported → {out}")
print(f"Run timestamp: {date.today().isoformat()}")

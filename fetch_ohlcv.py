import os
import sys
import time
from datetime import date

# pip install -U vnstock
try:
    from vnstock import Market, register_user
except ImportError:
    os.system(f"{sys.executable} -m pip install -U vnstock")
    from vnstock import Market, register_user

register_user(api_key="vnstock_3197cb8f57617c4bea9e114349132d30")

market = Market()

symbols = [
    "HPG","SSI","SHB","VPB","FPT","VIX","VHM","SHS","TCB","VIC",
    "MBB","STB","VND","MSN","NVL","CII","TPB","VCB","MWG","BSR",
    "DIG","CTG","VSC","CEO","GEX","PDR","HDB","EIB","DXG","VCI",
    "VRE","FLC","HCM","PVS","BID","VCG","DGC","ACB","VNM","DPM",
    "PLX","EVF","VIB","KBC","GAS","PVT","HAG","DCM","POW","PVD",
    "NKG","MSB","VJC","DBC","HAH","HHV","FTS","TCH","GEL","HSG",
    "PC1","GVR","MBS","HBC","NLG","LDG","KDH","VPI","HUT","ITA",
    "HQC","GMD","HDC","VCK","SCR","HDG","IDC","PNJ","APH","OIL",
    "HHS","VGI","BAF","BCG","DGW","LPB","HNG","GEE","VGC","MSR",
    "DPG","BVB","ORS","ACV","OCB","ANV","CTS","VHC","FCN","CTD",
    "VPL","ASM","HPX","CTR","ABB","TCM","TSC","TTF","KHG","LCG",
    "BSI","HVN","PET","BVH","NBB","MCH","SZC","VDS","VEA","KDC",
    "FRT","CMG","TCX","AAA","FUEVFVND","VHG","VTP","SAB","BCM","KSB",
    "YEG","CSV","IJC","VGT","VOS","PVC","IDI","FIT","C4G","REE",
    "SBT","DDV","DXS","PAN","HAX","JVC","VPX","OGC","NTL","VFS",
    "TAR","THD","TNG","DLG","CTI","KLF","TVC","HT1","VGS","FOX",
    "ART","PHR","BVS","SBS","APG","ELC","APS","CMX","GEG","L14",
    "QNS","VPG","AMD","NT2","AGR","BFC","MIG","IDJ","ST8","SIP",
    "TIG","DPR","NAB","PSH","AAS","SAM","DRH","PAS","EVG",
]

START = "2018-01-01"
END   = date.today().isoformat()
COUNT = 366 * 9

os.makedirs("CSV", exist_ok=True)

success, failed = [], []

print(f"\n{'#':<4} {'Symbol':<14} {'Rows':>6}  Status")
print("-" * 45)

for i, sym in enumerate(symbols, 1):
    try:
        df = market.equity(sym).ohlcv(start=START, end=END, count=COUNT)
        df.to_csv(f"CSV/{sym}.csv", index_label='seq')
        rows = len(df)
        success.append((sym, rows))
        print(f"{i:<4} {sym:<14} {rows:>6}  OK")
        sys.stdout.flush()
    except Exception as e:
        failed.append((sym, str(e)[:70]))
        print(f"{i:<4} {sym:<14}   FAIL  {str(e)[:70]}")
        sys.stdout.flush()
    time.sleep(0.4)   # stay within 60 req/min free tier

print("\n" + "=" * 55)
print(f"Done: {len(success)}/{len(symbols)} saved  |  {len(failed)} failed")

if failed:
    print("\nFailed symbols:")
    for sym, err in failed:
        print(f"  {sym:14} {err}")

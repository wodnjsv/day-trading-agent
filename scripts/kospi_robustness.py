"""KOSPI 대형주 종가베팅 다년 강건성 검증 (2022~2025).
V1 = 수급(기관·외국인 둘다>0, t-1) + 추세(close>MA20) + 끝물회피(0<당일등락률<10%), top20.
연도별 GROSS/net/승률/t/p 출력. (데이터: KRX OpenAPI KOSPI 일봉 + pykrx KOSPI 수급, 캐시·재실행 안전.)
"""
import time
import yaml
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

from jongga.config import Config
from jongga.data.krx_provider import KrxProvider
from jongga.data.pykrx_supply import PykrxSupply
from jongga.run_backtest import load_panels
from jongga.universe import build_universe, EXCLUDE_SECT

key = yaml.safe_load(Path("secrets.yaml").read_text(encoding="utf-8"))["krx_api_key"]
t0 = time.time()
cal = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2021-10-01", "2025-12-31")]
dates, p = load_panels(KrxProvider("data/krx", key, market="KOSPI"), cal,
                       PykrxSupply("data/krx", market="KOSPI"))
print(f"KOSPI 거래일 {len(dates)} ({dates[0]}~{dates[-1]}) load={time.time()-t0:.0f}s", flush=True)
close, open_, value, mcap, sect = p["close"], p["open"], p["value"], p["mcap"], p["sect"]
inst, foreign = p["inst_net"], p["foreign_net"]
IC, FC = set(inst.columns), set(foreign.columns)
cfg = Config()
K = 20

rows = []  # (date, v0_ret, v1_ret)
for i in range(60, len(dates) - 1):
    tm1, d, dp1 = dates[i - 1], dates[i], dates[i + 1]
    dly = pd.DataFrame({"value": value.loc[tm1], "marketcap": mcap.loc[tm1],
                        "sect": sect.loc[tm1]}).dropna(subset=["value"])
    uni = [s for s in build_universe(dly, K, cfg.universe.min_marketcap, EXCLUDE_SECT)
           if s in close.columns]
    ov = ((open_.loc[dp1, uni] - close.loc[d, uni]) / close.loc[d, uni]).replace([np.inf, -np.inf], np.nan)
    v1 = []
    for s in uni:
        c = close.loc[dates[:i + 1], s].dropna()
        if len(c) < 25 or pd.isna(ov[s]):
            continue
        ma20 = c.tail(20).mean()
        px, pxm1 = close.loc[d, s], close.loc[tm1, s]
        if pd.isna(px) or pd.isna(pxm1) or pxm1 == 0:
            continue
        retd = (px - pxm1) / pxm1
        sup = (s in IC and s in FC and inst.loc[tm1, s] > 0 and foreign.loc[tm1, s] > 0)
        if sup and px > ma20 and 0 < retd < 0.10:
            v1.append(s)
    v0r = ov[uni].dropna().mean()
    v1r = ov[v1].dropna().mean() if v1 else np.nan
    rows.append((d, v0r, v1r))

df = pd.DataFrame(rows, columns=["date", "v0", "v1"])
df["year"] = df["date"].str[:4]
cost = 0.0018 + 2 * 0.00014  # 세금+수수료 (슬리피지 별도)


def stat(x):
    x = x.dropna().values
    if len(x) < 3:
        return None
    t, pp = stats.ttest_1samp(x, 0)
    return len(x), x.mean(), (x > 0).mean(), t, pp


print(f"\n{'연도':>6} | {'V0(top20전체)':>28} | {'V1(수급+추세+끝물회피)':>34}")
print(f"{'':6} | {'일수 GROSS 승률 t':>28} | {'일수 GROSS 승률 t p  net@슬0/0.05%':>34}")
for y in ["2022", "2023", "2024", "2025", "ALL"]:
    sub = df if y == "ALL" else df[df["year"] == y]
    s0, s1 = stat(sub["v0"]), stat(sub["v1"])
    if s0:
        a = f"{s0[0]:3d} {s0[1]:+.3%} {s0[2]:.0%} t={s0[3]:+.1f}"
    else:
        a = "n/a"
    if s1:
        n,m,w,t,pp = s1
        net0 = m - cost; net5 = m - cost - 2*0.0005
        b = f"{n:3d} {m:+.3%} {w:.0%} t={t:+.1f} p={pp:.2f} net0={net0:+.3%} net.05={net5:+.3%}"
    else:
        b = "n/a"
    print(f"{y:>6} | {a:>28} | {b}")
print("\n* net@슬0 = 세금+수수료만(0.21%) 차감 / net@.05% = +편도 0.05% 슬리피지(메가캡 가정)")
print("[KOSPI 다년 강건성 검증 완료]")

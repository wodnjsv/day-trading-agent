# 재료 LLM 포워드 페이퍼 하네스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매 거래일 GPT-5.4가 웹검색으로 재료/테마 종목을 선별해 페이퍼로 진입(종가)·청산(익일시초) 기록·정산하고, 룰 baseline과 paired A/B로 "재료 선별이 비용을 넘고 baseline을 이기는가"를 판정하는 CLI 하네스.

**Architecture:** Phase 1 데이터 계층(`jongga/data/`·`universe`·`factors`)을 재사용해 후보 shortlist를 만들고, GPT-5.4(OpenAI SDK 웹검색)가 0~K종목을 선별한다. 선별·기록·정산·리포트는 SQLite 페이퍼북 하나로만 통신한다. 순수 로직(스크린 컨텍스트·페이퍼북·정산 net·리포트 통계·프롬프트 파싱)은 TDD, 라이브(KRX fetch·GPT 호출·CLI)는 통합 검증.

**Tech Stack:** Python 3.11, openai(SDK·웹검색), sqlite3(stdlib), pandas/numpy/scipy, Phase 1 `jongga` 모듈.

**참조 스펙:** `docs/superpowers/specs/2026-06-04-jongga-forward-paper-design.md` (v3) — §3 아키텍처, §5 검증(시점누수·미시구조·검정력·게이트), §8 빌드, §9 오픈이슈.

**전제:** Phase 1 완료(브랜치 `jongga-phase01`). 이 계획은 같은 브랜치(또는 그 위 새 브랜치)에서 `jongga/forward/`를 추가한다. `secrets.yaml`에 `openai_api_key`·`krx_api_key`·`krx_id`·`krx_pw` 존재.

---

## File Structure

```
jongga/forward/
  __init__.py
  cost.py          # 비용 상수(현행 매도세·수수료·슬리피지 밴드) + overnight_net 순수함수
  screen.py        # 후보 shortlist + 진입 공변량(정량 컨텍스트) — Phase1 재사용, 순수
  paperbook.py     # SQLite 페이퍼북: 스키마 + 기록(LLM·baseline) + 미정산 조회
  select.py        # GPT-5.4 웹검색 재료 선별: 프롬프트 빌드·응답 파싱(순수) + 실호출
  settle.py        # 익일 정산: 미정산 행 + d+1 일봉 → exit·net·settled
  report.py        # A/B 통계: paired(LLM매매일·동수)·within-market·게이트분해·겹침도·패스율
  cli.py           # jongga-forward-eve / -morn / -report 엔트리(라이브 결선)
tests/jongga/forward/
  __init__.py, test_cost.py, test_screen.py, test_paperbook.py,
  test_select_parse.py, test_settle.py, test_report.py
```

**책임 분리:** `cost`/`screen`/`paperbook`/`select(파싱)`/`settle`/`report`는 네트워크 없는 순수 로직 → TDD. `select`의 GPT 실호출, `cli`의 KRX fetch·종단은 통합 검증. 모든 컴포넌트는 페이퍼북(SQLite)으로만 통신.

**테스트 실행:** `.venv/bin/python -m pytest ...` (`.venv/bin/pytest`는 stale shebang).

---

## Task 0: 스캐폴드 — 패키지 + 의존성 + 콘솔 스크립트

**Files:**
- Modify: `pyproject.toml`
- Create: `jongga/forward/__init__.py`, `tests/jongga/forward/__init__.py`

- [ ] **Step 1: pyproject.toml — forward 패키지 + openai 의존성 + 콘솔 스크립트**

`[tool.setuptools].packages` 배열에 `"jongga.forward"` 추가. `[project].dependencies`에 `"openai>=1.40"` 추가. `[project.scripts]`에 추가(없으면 테이블 신설):
```toml
[project.scripts]
jongga-forward-eve = "jongga.forward.cli:eve"
jongga-forward-morn = "jongga.forward.cli:morn"
jongga-forward-report = "jongga.forward.cli:report_cmd"
```
(기존 `manju-collect` 등 스크립트가 있으면 보존.)

- [ ] **Step 2: 디렉터리 + `__init__.py`**

Run:
```bash
cd /Users/kimjaewon/Pluto/hybrid-trading-agent && mkdir -p jongga/forward tests/jongga/forward && touch jongga/forward/__init__.py tests/jongga/forward/__init__.py
```

- [ ] **Step 3: 설치 + import 확인 (network)**

Run (network → `dangerouslyDisableSandbox: true`):
```bash
.venv/bin/python -m pip install -e ".[dev]" && .venv/bin/python -c "import openai, jongga.forward; print('ok')"
```
Expected: 마지막 줄 `ok`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml jongga/forward tests/jongga/forward && git commit -m "chore: scaffold jongga.forward package + openai dep + console scripts"
```

---

## Task 1: 비용 모델 — `forward/cost.py`

매도세(현행 실세율)·수수료·슬리피지 밴드 상수 + 오버나잇 net 순수함수. 스펙 §5 비용.

**Files:**
- Create: `jongga/forward/cost.py`
- Test: `tests/jongga/forward/test_cost.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/jongga/forward/test_cost.py
from jongga.forward.cost import overnight_net, SELL_TAX, FEE, SLIP_BANDS


def test_overnight_net_subtracts_costs():
    # 진입 1000 → 청산 1100, gross +10%. 비용: 매도세+수수료2회+슬리피지2회
    net = overnight_net(entry=1000, exit_px=1100, slippage=0.0)
    assert abs(net - (0.10 - SELL_TAX - 2 * FEE)) < 1e-12


def test_overnight_net_slippage_band():
    net0 = overnight_net(1000, 1100, 0.0)
    net1 = overnight_net(1000, 1100, 0.001)
    assert abs((net0 - net1) - 2 * 0.001) < 1e-12   # 슬리피지 왕복


def test_slip_bands_default():
    assert SLIP_BANDS == (0.0, 0.0005, 0.001)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_cost.py -v` → FAIL (ModuleNotFound).

- [ ] **Step 3: 구현**

```python
# jongga/forward/cost.py
"""오버나잇 net 비용 모델. 매도세는 현행 실세율(2026, [사용자 확정])."""
from __future__ import annotations

SELL_TAX = 0.0020      # 매도 거래세(2026 코스피·코스닥 ~0.20%; 운영 전 현행 실세율로 확정)
FEE = 0.00014          # 편도 수수료(거래소+증권사 근사)
SLIP_BANDS = (0.0, 0.0005, 0.001)   # 편도 슬리피지 밴드 {0, 0.05%, 0.1%}


def overnight_net(entry: float, exit_px: float, slippage: float) -> float:
    """진입가→청산가 오버나잇 net 수익률. 매도세+수수료(왕복)+슬리피지(왕복) 차감."""
    gross = (exit_px - entry) / entry
    return gross - SELL_TAX - 2 * FEE - 2 * slippage
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_cost.py -v` → PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add jongga/forward/cost.py tests/jongga/forward/test_cost.py && git commit -m "feat: forward overnight_net cost model (current tax + slippage band)"
```

---

## Task 2: 진입 공변량 — `forward/screen.py`

후보 1종목의 **진입 공변량**(당일등락률·종가 일중위치·종가강도·거래대금·20일변동성)을 일봉 패널에서 계산하는 순수함수. 스펙 §5 기록 단위. (후보 shortlist 자체는 Phase1 `build_universe` 재사용 — CLI에서 결선.)

**Files:**
- Create: `jongga/forward/screen.py`
- Test: `tests/jongga/forward/test_screen.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/jongga/forward/test_screen.py
import pandas as pd
from jongga.forward.screen import entry_covariates


def test_entry_covariates():
    # 종가시리즈(과거~당일 d), 당일 OHLC, 거래대금
    closes = pd.Series([100.0, 110.0, 99.0, 105.0, 120.0])   # 마지막=당일 d 종가
    cov = entry_covariates(closes, open_d=100.0, high_d=125.0, low_d=98.0,
                           value_d=5_000_000_000, vol_window=4)
    # 당일등락률 = (120-105)/105
    assert abs(cov["ret_d"] - (120 - 105) / 105) < 1e-9
    # 종가일중위치 = (close-low)/(high-low) = (120-98)/(125-98)
    assert abs(cov["close_pos"] - (120 - 98) / (125 - 98)) < 1e-9
    # 종가강도 = (close-open)/open
    assert abs(cov["close_strength"] - (120 - 100) / 100) < 1e-9
    assert cov["trade_value"] == 5_000_000_000
    assert cov["vol20"] > 0    # 최근 vol_window 로그수익률 표준편차
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_screen.py -v` → FAIL.

- [ ] **Step 3: 구현**

```python
# jongga/forward/screen.py
"""후보 진입 공변량(정량 컨텍스트). 후보 shortlist는 CLI에서 Phase1 universe로 결선."""
from __future__ import annotations
import numpy as np
import pandas as pd


def entry_covariates(closes: pd.Series, open_d: float, high_d: float, low_d: float,
                     value_d: float, vol_window: int = 20) -> dict:
    """당일 d까지 종가시리즈 + 당일 OHLC·거래대금 → 진입 공변량."""
    c = closes.dropna()
    close_d = float(c.iloc[-1])
    prev = float(c.iloc[-2]) if len(c) >= 2 else close_d
    rng = (high_d - low_d)
    logret = np.log(c / c.shift(1)).dropna().tail(vol_window)
    return {
        "ret_d": (close_d - prev) / prev if prev else 0.0,
        "close_pos": (close_d - low_d) / rng if rng else 0.5,
        "close_strength": (close_d - open_d) / open_d if open_d else 0.0,
        "trade_value": float(value_d),
        "vol20": float(logret.std()) if len(logret) >= 2 else 0.0,
    }
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_screen.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add jongga/forward/screen.py tests/jongga/forward/test_screen.py && git commit -m "feat: entry covariates (ret/close-position/strength/value/vol)"
```

---

## Task 3: 페이퍼북 — `forward/paperbook.py`

SQLite 페이퍼북. 스키마(스펙 §5 기록 단위) + 행 기록(LLM·baseline) + 미정산 조회. tmp db로 TDD.

**Files:**
- Create: `jongga/forward/paperbook.py`
- Test: `tests/jongga/forward/test_paperbook.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/jongga/forward/test_paperbook.py
from jongga.forward.paperbook import PaperBook


def test_record_and_query_open(tmp_path):
    pb = PaperBook(tmp_path / "pb.db")
    row = dict(run_date="2026-06-05", market="KOSPI", ticker="005930", source="llm",
               k_t=2, catalyst_summary="HBM 공급", catalyst_timestamp="2026-06-05T14:50",
               theme="반도체", conviction=0.8, rationale="…", websearch_snapshot="{}",
               entry_close=80000.0, ret_d=0.03, close_pos=0.9, close_strength=0.02,
               trade_value=1e12, vol20=0.02)
    pb.record(row)
    pb.record({**row, "ticker": "000660", "source": "baseline"})
    opens = pb.open_positions("2026-06-05")
    assert len(opens) == 2
    assert {o["ticker"] for o in opens} == {"005930", "000660"}
    assert all(o["settled"] == 0 for o in opens)


def test_open_positions_excludes_settled(tmp_path):
    pb = PaperBook(tmp_path / "pb.db")
    row = dict(run_date="2026-06-05", market="KOSPI", ticker="005930", source="llm",
               k_t=1, catalyst_summary="", catalyst_timestamp="", theme="", conviction=0.5,
               rationale="", websearch_snapshot="{}", entry_close=80000.0, ret_d=0.0,
               close_pos=0.5, close_strength=0.0, trade_value=1e12, vol20=0.01)
    rid = pb.record(row)
    pb.settle(rid, exit_open=81000, exit_high=82000, exit_low=80000,
              exit_close1=81500, exit_close2=82000, nets={0.0: 0.01, 0.0005: 0.009, 0.001: 0.008})
    assert pb.open_positions("2026-06-05") == []
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_paperbook.py -v` → FAIL.

- [ ] **Step 3: 구현**

```python
# jongga/forward/paperbook.py
"""SQLite 페이퍼북: 진입 기록(LLM·baseline) + 정산 + 조회."""
from __future__ import annotations
import sqlite3
from pathlib import Path

_COLS = ["run_date", "market", "ticker", "source", "k_t", "catalyst_summary",
         "catalyst_timestamp", "theme", "conviction", "rationale", "websearch_snapshot",
         "entry_close", "ret_d", "close_pos", "close_strength", "trade_value", "vol20"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT, market TEXT, ticker TEXT, source TEXT, k_t INTEGER,
  catalyst_summary TEXT, catalyst_timestamp TEXT, theme TEXT, conviction REAL,
  rationale TEXT, websearch_snapshot TEXT,
  entry_close REAL, ret_d REAL, close_pos REAL, close_strength REAL, trade_value REAL, vol20 REAL,
  exit_open REAL, exit_high REAL, exit_low REAL, exit_close1 REAL, exit_close2 REAL,
  net_s0 REAL, net_s05 REAL, net_s10 REAL, settled INTEGER DEFAULT 0
);
"""


class PaperBook:
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def record(self, row: dict) -> int:
        cols = ", ".join(_COLS)
        ph = ", ".join("?" for _ in _COLS)
        cur = self.conn.execute(f"INSERT INTO paper ({cols}) VALUES ({ph})",
                                [row[c] for c in _COLS])
        self.conn.commit()
        return cur.lastrowid

    def open_positions(self, run_date: str) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM paper WHERE run_date=? AND settled=0", (run_date,))
        return [dict(r) for r in cur.fetchall()]

    def settle(self, rid: int, exit_open, exit_high, exit_low, exit_close1, exit_close2, nets: dict):
        self.conn.execute(
            "UPDATE paper SET exit_open=?, exit_high=?, exit_low=?, exit_close1=?, exit_close2=?, "
            "net_s0=?, net_s05=?, net_s10=?, settled=1 WHERE id=?",
            (exit_open, exit_high, exit_low, exit_close1, exit_close2,
             nets[0.0], nets[0.0005], nets[0.001], rid))
        self.conn.commit()

    def all_settled(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM paper WHERE settled=1")
        return [dict(r) for r in cur.fetchall()]
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_paperbook.py -v` → PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add jongga/forward/paperbook.py tests/jongga/forward/test_paperbook.py && git commit -m "feat: SQLite paperbook (record/settle/query, full schema)"
```

---

## Task 4: 정산 — `forward/settle.py`

미정산 행 + d+1 일봉(open/high/low/close + close[d+2]) → exit·net밴드·settled. 순수 로직(d+1 프레임 주입). 라이브 fetch는 CLI(Task 8).

**Files:**
- Create: `jongga/forward/settle.py`
- Test: `tests/jongga/forward/test_settle.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/jongga/forward/test_settle.py
import pandas as pd
from jongga.forward.paperbook import PaperBook
from jongga.forward.settle import settle_day
from jongga.forward.cost import SLIP_BANDS


def test_settle_day_fills_exit_and_nets(tmp_path):
    pb = PaperBook(tmp_path / "pb.db")
    base = dict(market="KOSPI", source="llm", k_t=1, catalyst_summary="", catalyst_timestamp="",
                theme="", conviction=0.5, rationale="", websearch_snapshot="{}",
                ret_d=0.0, close_pos=0.5, close_strength=0.0, trade_value=1e12, vol20=0.01)
    pb.record({**base, "run_date": "2026-06-05", "ticker": "005930", "entry_close": 1000.0})
    # d+1 일봉: 시가 1100 (진입 1000 → +10% gross)
    d1 = pd.DataFrame({"open": [1100.0], "high": [1150.0], "low": [1090.0], "close": [1120.0]},
                      index=["005930"])
    d2 = pd.DataFrame({"close": [1130.0]}, index=["005930"])    # d+2 종가(보조)
    n = settle_day(pb, "2026-06-05", d1, d2)
    assert n == 1
    row = pb.all_settled()[0]
    assert row["exit_open"] == 1100.0 and row["exit_close2"] == 1130.0
    # net_s0 = gross(0.10) − 비용
    from jongga.forward.cost import overnight_net
    assert abs(row["net_s0"] - overnight_net(1000.0, 1100.0, 0.0)) < 1e-9


def test_settle_skips_missing_ticker(tmp_path):
    pb = PaperBook(tmp_path / "pb.db")
    pb.record(dict(run_date="2026-06-05", market="KOSPI", ticker="999999", source="llm", k_t=1,
                   catalyst_summary="", catalyst_timestamp="", theme="", conviction=0.5,
                   rationale="", websearch_snapshot="{}", entry_close=1000.0, ret_d=0.0,
                   close_pos=0.5, close_strength=0.0, trade_value=1e12, vol20=0.01))
    d1 = pd.DataFrame({"open": [1100.0], "high": [1150.0], "low": [1090.0], "close": [1120.0]},
                      index=["005930"])    # 999999 없음
    assert settle_day(pb, "2026-06-05", d1, d1) == 0
    assert pb.open_positions("2026-06-05")  # 미정산 잔존
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_settle.py -v` → FAIL.

- [ ] **Step 3: 구현**

```python
# jongga/forward/settle.py
"""익일 정산: 미정산 행 + d+1 일봉(+d+2 종가) → exit·net밴드·settled."""
from __future__ import annotations
import pandas as pd
from jongga.forward.cost import overnight_net, SLIP_BANDS
from jongga.forward.paperbook import PaperBook


def settle_day(pb: PaperBook, run_date: str, d1: pd.DataFrame, d2: pd.DataFrame) -> int:
    """run_date의 미정산 포지션을 d1(익일 OHLC)·d2(d+2 종가)로 정산. 정산 건수 반환."""
    settled = 0
    for row in pb.open_positions(run_date):
        t = row["ticker"]
        if t not in d1.index or pd.isna(d1.loc[t, "open"]):
            continue
        exit_open = float(d1.loc[t, "open"])
        nets = {s: overnight_net(row["entry_close"], exit_open, s) for s in SLIP_BANDS}
        c2 = float(d2.loc[t, "close"]) if (d2 is not None and t in d2.index) else None
        pb.settle(row["id"], exit_open, float(d1.loc[t, "high"]), float(d1.loc[t, "low"]),
                  float(d1.loc[t, "close"]), c2, nets)
        settled += 1
    return settled
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_settle.py -v` → PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add jongga/forward/settle.py tests/jongga/forward/test_settle.py && git commit -m "feat: settle_day (overnight net bands + multi-horizon exit)"
```

---

## Task 5: A/B 리포트 — `forward/report.py`

정산 행 → paired(LLM매매일·동수 baseline)·within-market·게이트분해(상대/절대)·겹침도(Jaccard)·패스율. 순수 통계. 스펙 §5 검증.

**Files:**
- Create: `jongga/forward/report.py`
- Test: `tests/jongga/forward/test_report.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/jongga/forward/test_report.py
from jongga.forward.report import paired_by_day, overlap_jaccard


def test_paired_by_day_relative_gate():
    # 2일치 정산행(net_s0). day1: llm 평균 +0.02, baseline +0.00 / day2: llm -0.01, baseline 0.00
    rows = [
        {"run_date": "d1", "source": "llm", "net_s0": 0.02},
        {"run_date": "d1", "source": "baseline", "net_s0": 0.00},
        {"run_date": "d2", "source": "llm", "net_s0": -0.01},
        {"run_date": "d2", "source": "baseline", "net_s0": 0.00},
    ]
    res = paired_by_day(rows, band="net_s0")
    # day별 차이: d1=+0.02, d2=-0.01 → 평균 차이 +0.005
    assert abs(res["mean_diff"] - 0.005) < 1e-9
    assert res["n_days"] == 2
    assert abs(res["llm_mean"] - 0.005) < 1e-9      # llm net 평균 (절대게이트)


def test_overlap_jaccard():
    assert abs(overlap_jaccard(["A", "B", "C"], ["B", "C", "D"]) - (2 / 4)) < 1e-9
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_report.py -v` → FAIL.

- [ ] **Step 3: 구현**

```python
# jongga/forward/report.py
"""A/B 리포트: paired(day-level)·게이트분해·겹침도. 검정은 day 단위(유효 N=거래일수)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def paired_by_day(rows: list[dict], band: str = "net_s0") -> dict:
    """LLM 매매일 한정 day-level paired: day별 (llm 평균 − baseline 평균) net.
    상대게이트(mean_diff·유의)와 절대게이트(llm_mean)를 함께 반환."""
    df = pd.DataFrame(rows)
    days = []
    for d, g in df.groupby("run_date"):
        llm = g[g["source"] == "llm"][band]
        base = g[g["source"] == "baseline"][band]
        if len(llm) == 0:        # LLM 패스일 → 1차 paired 제외
            continue
        days.append((float(llm.mean()), float(base.mean()) if len(base) else np.nan))
    if not days:
        return {"n_days": 0, "mean_diff": float("nan"), "llm_mean": float("nan"), "p_rel": 1.0}
    llm_d = np.array([x[0] for x in days])
    base_d = np.array([x[1] for x in days])
    diff = llm_d - base_d
    p = stats.ttest_1samp(diff, 0.0).pvalue if len(diff) >= 2 else 1.0
    return {"n_days": len(days), "mean_diff": float(np.nanmean(diff)),
            "llm_mean": float(llm_d.mean()), "p_rel": float(p)}


def overlap_jaccard(llm_tickers: list[str], baseline_tickers: list[str]) -> float:
    a, b = set(llm_tickers), set(baseline_tickers)
    u = a | b
    return len(a & b) / len(u) if u else 0.0
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_report.py -v` → PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add jongga/forward/report.py tests/jongga/forward/test_report.py && git commit -m "feat: A/B report (day-level paired relative+absolute gate, jaccard)"
```

---

## Task 6: LLM 선별 — 프롬프트·파싱 (순수) — `forward/select.py`

GPT-5.4 응답(structured) 파싱·검증. **≤15:20 정보 제약·catalyst_timestamp 요구**(스펙 §5 #1). 실호출은 Task 7.

**Files:**
- Create: `jongga/forward/select.py`
- Test: `tests/jongga/forward/test_select_parse.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/jongga/forward/test_select_parse.py
from jongga.forward.select import parse_selection, SELECTION_SCHEMA


def test_parse_selection_valid():
    raw = {"picks": [
        {"ticker": "005930", "catalyst_summary": "HBM 공급 확대", "catalyst_timestamp": "2026-06-05T13:10",
         "theme": "반도체", "conviction": 0.8, "rationale": "…"},
    ], "regime_read": "강세"}
    picks = parse_selection(raw, candidate_tickers={"005930", "000660"})
    assert len(picks) == 1 and picks[0]["ticker"] == "005930"
    assert 0 <= picks[0]["conviction"] <= 1


def test_parse_selection_pass_is_empty():
    assert parse_selection({"picks": [], "regime_read": "약세-패스"}, {"005930"}) == []


def test_parse_selection_drops_offlist_ticker():
    raw = {"picks": [{"ticker": "111111", "catalyst_summary": "x", "catalyst_timestamp": "t",
                      "theme": "t", "conviction": 0.5, "rationale": "r"}], "regime_read": "-"}
    assert parse_selection(raw, candidate_tickers={"005930"}) == []   # 후보 밖 종목 거부
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_select_parse.py -v` → FAIL.

- [ ] **Step 3: 구현 (파싱·검증 + 프롬프트·스키마 상수)**

```python
# jongga/forward/select.py
"""GPT-5.4 웹검색 재료 선별: 프롬프트·structured 스키마 + 응답 파싱·검증(순수) + 실호출."""
from __future__ import annotations

# OpenAI structured output 스키마(picks: 0~K, 패스=빈 배열)
SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "regime_read": {"type": "string"},
        "picks": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "catalyst_summary": {"type": "string"},
                "catalyst_timestamp": {"type": "string"},   # ≤15:20 공개 시각
                "theme": {"type": "string"},
                "conviction": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["ticker", "catalyst_summary", "catalyst_timestamp",
                         "theme", "conviction", "rationale"],
        }},
    },
    "required": ["regime_read", "picks"],
}

SYSTEM_PROMPT = (
    "너는 한국 주식 종가베팅 트레이더다. 주어진 후보(정량 컨텍스트 포함) 중, "
    "그날 15:20(종가 동시호가) 이전에 공개된 재료/뉴스/테마가 강한 종목만 0~K개 고른다. "
    "재료가 약하면 빈 배열로 패스한다. 각 픽에 재료 발표시각(catalyst_timestamp, ≤15:20)을 반드시 단다. "
    "15:20 이후(장 마감 후) 공시·뉴스는 사용 금지."
)


def parse_selection(raw: dict, candidate_tickers: set[str]) -> list[dict]:
    """응답 dict → 검증된 픽 리스트. 후보 밖 종목·필드 누락은 제외. 패스=[]."""
    out = []
    for p in raw.get("picks", []):
        if not isinstance(p, dict) or p.get("ticker") not in candidate_tickers:
            continue
        if not all(k in p for k in ("catalyst_summary", "catalyst_timestamp", "theme",
                                    "conviction", "rationale")):
            continue
        c = max(0.0, min(1.0, float(p["conviction"])))
        out.append({**p, "conviction": c})
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/jongga/forward/test_select_parse.py -v` → PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add jongga/forward/select.py tests/jongga/forward/test_select_parse.py && git commit -m "feat: LLM selection schema + parse/validate (<=15:20 catalyst, off-list reject)"
```

---

## Task 7: GPT-5.4 웹검색 실호출 — `forward/select.py` 보강 (통합)

후보+컨텍스트 → GPT-5.4 웹검색 호출 → SELECTION_SCHEMA structured output. 실호출 통합 검증.

**Files:**
- Modify: `jongga/forward/select.py`

- [ ] **Step 1: 호출 함수 추가**

`select.py`에 추가(OpenAI SDK; 모델 ID·웹검색 도구·structured output 형식은 Step 2 실호출로 확정):
```python
def build_user_prompt(candidates: list[dict]) -> str:
    """후보(ticker·name·정량 컨텍스트) → 프롬프트 텍스트."""
    lines = ["오늘 후보(거래대금·수급·추세·끝물회피 통과). 재료가 강한 종목만 고르세요:"]
    for c in candidates:
        lines.append(
            f"- {c['ticker']} {c.get('name','')} | 시장 {c['market']} | 등락률 {c['ret_d']:.1%} "
            f"| 종가위치 {c['close_pos']:.2f} | 거래대금 {c['trade_value']/1e8:.0f}억 | 수급 {c.get('supply_note','')}")
    return "\n".join(lines)


def select_with_gpt(candidates: list[dict], api_key: str, model: str = "gpt-5.4") -> dict:
    """GPT-5.4 웹검색으로 재료 선별. raw dict(SELECTION_SCHEMA) 반환."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    cand_ix = {c["ticker"] for c in candidates}
    resp = client.responses.create(            # ← Step 2에서 정확한 API 형태 확정
        model=model,
        tools=[{"type": "web_search"}],
        input=[{"role": "system", "content": SYSTEM_PROMPT},
               {"role": "user", "content": build_user_prompt(candidates)}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "selection", "schema": SELECTION_SCHEMA}},
    )
    import json
    return json.loads(resp.output_text)
```

- [ ] **Step 2: 실호출 통합 검증 (network)**

`secrets.yaml`의 `openai_api_key`로 소수 후보에 실호출(network → `dangerouslyDisableSandbox: true`):
```bash
.venv/bin/python - <<'PY'
import yaml
from pathlib import Path
from jongga.forward.select import select_with_gpt, parse_selection
key = yaml.safe_load(Path("secrets.yaml").read_text())["openai_api_key"]
cands = [{"ticker":"005930","name":"삼성전자","market":"KOSPI","ret_d":0.02,"close_pos":0.8,
          "trade_value":8e11,"supply_note":"외/기 순매수"},
         {"ticker":"000660","name":"SK하이닉스","market":"KOSPI","ret_d":0.03,"close_pos":0.9,
          "trade_value":5e11,"supply_note":"외인 순매수"}]
raw = select_with_gpt(cands, key)
print("regime:", raw.get("regime_read"))
picks = parse_selection(raw, {c["ticker"] for c in cands})
print("picks:", [(p["ticker"], p["catalyst_timestamp"], round(p["conviction"],2)) for p in picks])
PY
```
Expected: regime 문자열 + picks(0~2개, 각 catalyst_timestamp 포함). **실패 시 OpenAI SDK 버전의 정확한 웹검색 도구·structured output 호출 형태(`responses.create` vs `chat.completions` + `response_format`)를 SDK 문서로 확정해 `select_with_gpt` 수정.** 모델 ID `gpt-5.4`가 거부되면 사용가능 ID로 교체(스펙 §6 모델핀 — 확정 ID를 주석에 고정).

- [ ] **Step 3: 회귀 + Commit**

Run: `.venv/bin/python -m pytest tests/jongga/forward -q` → 전부 PASS.
```bash
git add jongga/forward/select.py && git commit -m "feat: GPT-5.4 web-search selection call (structured output)"
```

---

## Task 8: CLI 결선 — `forward/cli.py` (통합)

`jongga-forward-eve`(스크린→선별→기록) / `-morn`(정산) / `-report`. Phase 1 `KrxProvider`·`PykrxSupply`·`build_universe` 재사용. 라이브 종단.

**Files:**
- Create: `jongga/forward/cli.py`

- [ ] **Step 1: cli.py 작성**

```python
# jongga/forward/cli.py
"""포워드 페이퍼 CLI: eve(선별·기록) / morn(정산) / report. 라이브 결선.

eve: 오늘(거래일) 마감 후 실행. KOSPI+KOSDAQ 후보 shortlist(거래대금 상위 + 수급(t-1 양수)
     + 추세(close>MA20) + 끝물회피(0<당일등락<10%)) → GPT-5.4 재료 선별(0~K) →
     LLM 바스켓 + 같은 후보풀 baseline 동수 K_t(정량 상위) 페이퍼 기록(진입=close[d]).
morn: 익일 시초 후 실행. d+1 일봉으로 전일 미정산 정산.
report: 누적 정산행 → paired·게이트·겹침도·패스율.
"""
from __future__ import annotations
import logging
import sys
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)
DB = Path("data/forward/paperbook.db")
SHORTLIST_N = 30        # 시장별 거래대금 상위 후보 수


def _secrets():
    return yaml.safe_load(Path("secrets.yaml").read_text(encoding="utf-8"))


def eve(argv=None):
    """오늘 d(인자 없으면 최근 거래일) 후보 스크린 → GPT 선별 → 페이퍼 기록."""
    # 1) Phase1로 KOSPI+KOSDAQ 일봉·수급 로드(최근 ~130 거래일: MA·공변량 룩백)
    # 2) 시장별 build_universe로 거래대금 상위 + 수급·추세·끝물회피 통과 후보 shortlist + entry_covariates
    # 3) select_with_gpt → parse_selection (≤15:20 재료)
    # 4) PaperBook.record: LLM 바스켓(K_t) + baseline 동수 K_t(정량 상위) — 진입=close[d]
    raise NotImplementedError("Step 2 통합검증에서 결선")


def morn(argv=None):
    """전일 미정산 → d+1 일봉(+d+2 종가) 정산."""
    raise NotImplementedError("Step 2 통합검증에서 결선")


def report_cmd(argv=None):
    """누적 정산행 → paired(시장별)·게이트분해·겹침도·패스율 출력."""
    from jongga.forward.paperbook import PaperBook
    from jongga.forward.report import paired_by_day
    pb = PaperBook(DB)
    rows = pb.all_settled()
    for mkt in ("KOSPI", "KOSDAQ"):
        sub = [r for r in rows if r["market"] == mkt]
        for band in ("net_s0", "net_s05", "net_s10"):
            res = paired_by_day(sub, band)
            print(f"[{mkt} {band}] n_days={res['n_days']} mean_diff={res['mean_diff']:+.4%} "
                  f"llm_mean={res['llm_mean']:+.4%} p_rel={res['p_rel']:.3f}")
```

- [ ] **Step 2: eve/morn 결선 + 종단 통합 검증 (network, 장 마감 후)**

`eve`/`morn`의 `NotImplementedError`를 Task 1~7 함수로 결선한다(스크린=Phase1 `load_panels`+`build_universe`+`entry_covariates`, 선별=`select_with_gpt`+`parse_selection`, 기록=`PaperBook.record`, 정산=`settle_day` + `KrxProvider(market).daily(d+1)`). 거래일 장 마감 후 실행:
```bash
.venv/bin/jongga-forward-eve         # 후보·선별·기록 (network, 마감 후)
# (익일 시초 후) .venv/bin/jongga-forward-morn
.venv/bin/jongga-forward-report
```
Expected: eve가 후보 수·LLM 픽·baseline 기록 로그 출력, `data/forward/paperbook.db` 생성. morn이 정산 건수 출력. report가 시장별 라인 출력. (장 마감 전이면 그날 일봉 미확정 → 마감 후 실행.)

- [ ] **Step 3: 회귀 + Commit**

Run: `.venv/bin/python -m pytest tests/jongga/forward -q` → 전부 PASS.
```bash
git add jongga/forward/cli.py && git commit -m "feat: forward CLI (eve/morn/report) live wiring"
```

---

## Task 9: 운영 사전등록 문서 + 개시

스펙 §9 동결 항목을 운영 전 사전등록 문서로 박고, 매 거래일 수동 실행 개시.

**Files:**
- Create: `docs/superpowers/prereg/2026-06-05-forward-paper-prereg.md`

- [ ] **Step 1: 사전등록 문서 작성**

아래를 데이터 누적 *전* 확정·동결(스펙 §9):
- **검정력분석:** day-level 차이 분산 가정 → 필요 거래일수 N 역산. 단일 1차 추정량(시장구성비 고정 pooled 또는 1개 시장), 고정-N(또는 α-spending), 체크포인트=모니터링 전용. α 값.
- **시점누수:** 재료 ≤15:20 + catalyst_timestamp 필터.
- **미시구조:** 바스켓 유동성·거래대금·변동성 매칭 + 겹침도 보고.
- **비용:** 현행 매도세 실세율 확인·동결.
- **모델핀:** GPT-5.4 정확한 ID 고정.
- **baseline 정의:** 수급(t-1)+추세(>MA20)+끝물회피(0<등락<10%) 상위 K. **LLM 후보풀 = baseline 풀 동일(MVP)**(over-filter 긴장은 운영 후 재검토).
- K, SHORTLIST_N.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/prereg/2026-06-05-forward-paper-prereg.md && git commit -m "docs: forward paper pre-registration (frozen before data)"
```

- [ ] **Step 3: 운영 개시** — 매 거래일 마감 후 `jongga-forward-eve`, 익일 시초 후 `jongga-forward-morn`, 주간 `jongga-forward-report`(모니터링)로 사전등록 N까지 누적.

---

## 완료 기준 (Definition of Done)

- [ ] 순수 단위테스트 전부 통과(`.venv/bin/python -m pytest tests/jongga/forward -q`): cost·screen·paperbook·settle·report·select_parse.
- [ ] GPT-5.4 웹검색 선별 실호출이 SELECTION_SCHEMA로 0~K 픽(catalyst_timestamp 포함) 반환.
- [ ] `eve`→`morn`→`report` 종단이 실데이터 1사이클 동작, 페이퍼북에 LLM·baseline 양쪽 기록·정산.
- [ ] 사전등록 문서 동결(검정력 N·단일 추정량·고정-N·시점누수·미시구조·세율·모델핀).
- [ ] 진입 ≤15:20 재료 제약·다중호라이즌·진입공변량이 스키마에 기록됨(영구손실 방지).

---

## Self-Review 메모

- **스펙 커버리지:** §3 컴포넌트=Task2~6, CLI=Task8 / §5 비용=Task1·시점누수(catalyst_timestamp·≤15:20)=Task6·진입공변량=Task2·다중호라이즌=Task4·paired게이트=Task5 / §6 모델핀=Task7·9 / §9 사전등록=Task9. 모두 매핑.
- **순수/통합 분리:** cost·screen·paperbook·settle·report·select_parse는 네트워크 없는 TDD. GPT 실호출(Task7)·KRX fetch·CLI 종단(Task8)은 통합 검증(추정→실호출 확정 경로).
- **타입 일관성:** `PaperBook.record/settle/open_positions/all_settled` ↔ `settle_day` ↔ `paired_by_day`(band 키 net_s0/s05/s10) ↔ cost `SLIP_BANDS`(0/0.0005/0.001) 일치. `parse_selection(raw, candidate_tickers)` ↔ `select_with_gpt` 반환 dict 일치.
- **YAGNI:** 스케줄 자동화·실주문·비중정교화 제외(스펙 비목표). 검정력 N·세율·모델ID는 사전등록(Task9)·실호출(Task7)에서 확정(추정→검증).
- **오픈 결선:** Task7 Step2(OpenAI 웹검색 API 정확 형태·모델ID), Task8 Step2(CLI eve/morn 결선)는 통합검증에서 확정 — 플레이스홀더가 아니라 "라이브 형태 확정" 절차로 명시.

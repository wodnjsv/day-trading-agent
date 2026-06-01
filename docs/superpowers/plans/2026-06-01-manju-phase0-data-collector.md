# ManjuAgent Phase 0 — 데이터 수집기 + KIS 어댑터 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KIS 실시간 체결·호가 스트림을 거래대금 상위 종목 대상으로 구독해 parquet으로 녹음하고, 그 데이터를 시간순으로 재생(ReplayFeed)할 수 있는 데이터 수집기를 만든다.

**Architecture:** 단일 프로세스 Python/asyncio. `kis/`(인증·REST순위·WebSocket·파싱) 어댑터 위에 `collector/`(Universe선정 → rotating 구독 → parquet 녹음)를 얹고, `replay/`가 녹음 데이터를 동일 스키마 이벤트로 재생한다. LiveFeed↔ReplayFeed의 공통 계약은 `models.py`의 `Trade`/`OrderBook`. 토큰·approval_key 발급은 직접 구현(POST 2개), 필드 레이아웃·구독 메시지·프레임 디멀티플렉싱은 `koreainvestment/open-trading-api`에서 검증된 형식을 차용.

**Tech Stack:** Python 3.11, asyncio, `websockets`, `requests`, `pyarrow`(parquet), `pyyaml`, `pytest`.

**참조 스펙:** `docs/superpowers/specs/2026-06-01-manju-trading-agent-design.md` (§8 데이터 수집기 동작, §12 참고구현)

---

## File Structure

```
ManjuAgent/
  pyproject.toml                  # 프로젝트 메타 + 의존성
  manju/
    __init__.py
    config.py                     # 설정(appkey/secret/account/경로/universe크기) 로드
    models.py                     # Trade, OrderBook (+ to_row/from_row 플래트닝) — 공통 스키마
    kis/
      __init__.py
      constants.py                # TR ID, URL, PRICE_COLUMNS(체결), 호가 인덱스
      auth.py                     # access_token + approval_key 발급
      rest.py                     # volume-rank: 거래대금 상위 N 종목
      ws.py                       # async WebSocket: 연결/구독/수신/PINGPONG/재연결
      parse.py                    # 실시간 raw 프레임 → Trade/OrderBook (순수함수)
    collector/
      __init__.py
      subscriber.py               # 구독 등록 한도 내 universe diff → 등록/해지
      recorder.py                 # parquet 녹음(ticks/quotes, date/symbol, raw 동반)
      runner.py                   # asyncio 오케스트레이션(수집기 main)
    replay/
      __init__.py
      feed.py                     # ReplayFeed: parquet 시간순 재생
  tests/
    __init__.py
    fixtures.py                   # 실시간 프레임 샘플 문자열
    test_models.py
    test_parse.py
    test_auth.py
    test_rest.py
    test_ws.py
    test_subscriber.py
    test_recorder.py
    test_replay.py
```

**책임 분리:** `parse.py`/`subscriber.py`/`recorder.py`/`feed.py`는 네트워크 없이 단위 테스트(TDD). 네트워크가 필요한 `auth.py`/`rest.py`/`ws.py`는 (a) 요청·프레임 구성 같은 순수 부분만 단위 테스트, (b) 실접속은 통합 검증 단계(실제 명령+기대 출력)로 확인.

---

## Task 0: 프로젝트 스캐폴드 + git init

**Files:**
- Create: `pyproject.toml`
- Create: `manju/__init__.py`, `manju/kis/__init__.py`, `manju/collector/__init__.py`, `manju/replay/__init__.py`, `tests/__init__.py`
- Create: `manju/config.py`

- [ ] **Step 1: git 저장소 초기화**

Run:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && git init && printf '%s\n' '__pycache__/' '*.pyc' '.venv/' 'data/' 'secrets.yaml' '*.parquet' > .gitignore
```
Expected: `Initialized empty Git repository ...`

- [ ] **Step 2: pyproject.toml 작성**

```toml
[project]
name = "manju"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = [
    "websockets>=12.0",
    "requests>=2.31",
    "pyarrow>=15.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: 패키지 디렉터리 + 빈 `__init__.py` 생성**

Run:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && mkdir -p manju/kis manju/collector manju/replay tests && \
touch manju/__init__.py manju/kis/__init__.py manju/collector/__init__.py manju/replay/__init__.py tests/__init__.py
```

- [ ] **Step 4: config.py 작성**

```python
# manju/config.py
"""수집기 설정. secrets.yaml(비밀) + 기본값으로 구성."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

REAL_BASE = "https://openapi.koreainvestment.com:9443"
PAPER_BASE = "https://openapivts.koreainvestment.com:29443"
REAL_WS = "ws://ops.koreainvestment.com:21000"
PAPER_WS = "ws://ops.koreainvestment.com:31000"


@dataclass
class Config:
    app_key: str
    app_secret: str
    account_no: str
    is_paper: bool = False
    data_dir: Path = Path("data")
    universe_size: int = 20          # 동시 구독 종목 수(체결+호가 = 종목당 등록 2건)
    max_registrations: int = 40      # 세션당 실시간 등록 한도(~41), 종목당 2건
    poll_interval_sec: int = 30      # universe 재선정 주기

    @property
    def base_url(self) -> str:
        return PAPER_BASE if self.is_paper else REAL_BASE

    @property
    def ws_url(self) -> str:
        return PAPER_WS if self.is_paper else REAL_WS

    @classmethod
    def load(cls, path: str = "secrets.yaml") -> "Config":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            app_key=raw["app_key"],
            app_secret=raw["app_secret"],
            account_no=str(raw["account_no"]),
            is_paper=bool(raw.get("is_paper", False)),
            data_dir=Path(raw.get("data_dir", "data")),
            universe_size=int(raw.get("universe_size", 20)),
            max_registrations=int(raw.get("max_registrations", 40)),
            poll_interval_sec=int(raw.get("poll_interval_sec", 30)),
        )
```

- [ ] **Step 5: secrets.yaml 템플릿 작성 (값은 사용자가 채움, git 무시됨)**

```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && cat > secrets.example.yaml <<'EOF'
app_key: "발급받은_appkey"
app_secret: "발급받은_appsecret"
account_no: "12345678"
is_paper: false
data_dir: "data"
universe_size: 20
EOF
```

- [ ] **Step 6: 의존성 설치 + import 확인**

Run:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/python -c "import manju.config; print('ok')"
```
Expected: 마지막 줄 `ok`

- [ ] **Step 7: Commit**

```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && git add -A && git commit -m "chore: scaffold manju phase0 package"
```

---

## Task 1: 공통 스키마 — `models.py`

LiveFeed/ReplayFeed가 공유하는 `Trade`(체결)·`OrderBook`(호가). parquet 저장을 위해 `to_row()`(플래트닝)·`from_row()`(복원) 제공.

**Files:**
- Create: `manju/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_models.py
from datetime import datetime
from manju.models import Trade, OrderBook


def test_trade_row_roundtrip():
    t = Trade(
        symbol="005930", market_ts=datetime(2026, 6, 1, 9, 0, 1),
        recv_ts=datetime(2026, 6, 1, 9, 0, 1), price=70000, change_rate=12.5,
        volume=10, cum_volume=1000, cum_value=70_000_000, strength=180.5,
        ccld_dvsn="1", ask1=70100, bid1=70000, ask1_qty=50, bid1_qty=80,
        total_ask_qty=500, total_bid_qty=900, vi_std_price=73500, raw="raw^string",
    )
    row = t.to_row()
    assert row["symbol"] == "005930"
    assert row["ccld_dvsn"] == "1"
    assert Trade.from_row(row) == t


def test_orderbook_row_roundtrip():
    ob = OrderBook(
        symbol="005930", market_ts=datetime(2026, 6, 1, 9, 0, 1),
        recv_ts=datetime(2026, 6, 1, 9, 0, 1),
        asks=[70100 + i * 100 for i in range(10)],
        bids=[70000 - i * 100 for i in range(10)],
        ask_qtys=[i + 1 for i in range(10)],
        bid_qtys=[i + 11 for i in range(10)],
        total_ask_qty=55, total_bid_qty=155, raw="raw^string",
    )
    row = ob.to_row()
    assert row["ask1"] == 70100
    assert row["bid10"] == 70000 - 900
    assert OrderBook.from_row(row) == ob
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manju.models'`

- [ ] **Step 3: 최소 구현**

```python
# manju/models.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """실시간 체결(H0STCNT0) 정규화 레코드."""
    symbol: str
    market_ts: datetime      # 장 시간(체결시각)
    recv_ts: datetime        # 수신 벽시계 시각
    price: int               # 현재가 STCK_PRPR
    change_rate: float       # 등락률 PRDY_CTRT
    volume: int              # 체결량 CNTG_VOL
    cum_volume: int          # 누적거래량 ACML_VOL
    cum_value: int           # 누적거래대금 ACML_TR_PBMN
    strength: float          # 체결강도 CTTR
    ccld_dvsn: str           # 체결구분 CCLD_DVSN (1:매수,3:장전,5:매도)
    ask1: int
    bid1: int
    ask1_qty: int
    bid1_qty: int
    total_ask_qty: int       # TOTAL_ASKP_RSQN
    total_bid_qty: int       # TOTAL_BIDP_RSQN
    vi_std_price: int        # VI 기준가 VI_STND_PRC
    raw: str

    def to_row(self) -> dict:
        d = self.__dict__.copy()
        d["market_ts"] = self.market_ts.isoformat()
        d["recv_ts"] = self.recv_ts.isoformat()
        return d

    @classmethod
    def from_row(cls, row: dict) -> "Trade":
        d = dict(row)
        d["market_ts"] = datetime.fromisoformat(d["market_ts"])
        d["recv_ts"] = datetime.fromisoformat(d["recv_ts"])
        return cls(**d)


@dataclass
class OrderBook:
    """실시간 호가(H0STASP0) 정규화 레코드. 10호가."""
    symbol: str
    market_ts: datetime
    recv_ts: datetime
    asks: list[int]          # 매도호가 1..10
    bids: list[int]          # 매수호가 1..10
    ask_qtys: list[int]      # 매도호가 잔량 1..10
    bid_qtys: list[int]      # 매수호가 잔량 1..10
    total_ask_qty: int
    total_bid_qty: int
    raw: str

    def to_row(self) -> dict:
        d = {
            "symbol": self.symbol,
            "market_ts": self.market_ts.isoformat(),
            "recv_ts": self.recv_ts.isoformat(),
            "total_ask_qty": self.total_ask_qty,
            "total_bid_qty": self.total_bid_qty,
            "raw": self.raw,
        }
        for i in range(10):
            d[f"ask{i+1}"] = self.asks[i]
            d[f"bid{i+1}"] = self.bids[i]
            d[f"ask{i+1}_qty"] = self.ask_qtys[i]
            d[f"bid{i+1}_qty"] = self.bid_qtys[i]
        return d

    @classmethod
    def from_row(cls, row: dict) -> "OrderBook":
        return cls(
            symbol=row["symbol"],
            market_ts=datetime.fromisoformat(row["market_ts"]),
            recv_ts=datetime.fromisoformat(row["recv_ts"]),
            asks=[row[f"ask{i+1}"] for i in range(10)],
            bids=[row[f"bid{i+1}"] for i in range(10)],
            ask_qtys=[row[f"ask{i+1}_qty"] for i in range(10)],
            bid_qtys=[row[f"bid{i+1}_qty"] for i in range(10)],
            total_ask_qty=row["total_ask_qty"],
            total_bid_qty=row["total_bid_qty"],
            raw=row["raw"],
        )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add manju/models.py tests/test_models.py && git commit -m "feat: Trade/OrderBook shared schema with row roundtrip"
```

---

## Task 2: KIS 상수 — `kis/constants.py`

`open-trading-api`에서 검증한 체결 컬럼·TR ID. 호가는 선두 45필드 인덱스를 직접 정의.

**Files:**
- Create: `manju/kis/constants.py`

- [ ] **Step 1: 작성 (테스트 불필요한 상수 모듈)**

```python
# manju/kis/constants.py
"""KIS TR ID 및 실시간 필드 레이아웃.

PRICE_COLUMNS는 open-trading-api(koreainvestment/open-trading-api)의
websocket.py에서 검증된 H0STCNT0 체결 필드 순서.
"""

TRADE_TR = "H0STCNT0"   # 실시간 체결가
QUOTE_TR = "H0STASP0"   # 실시간 호가

# REST: 거래량/거래대금 순위
VOLUME_RANK_TR = "FHPST01710000"
VOLUME_RANK_PATH = "/uapi/domestic-stock/v1/quotations/volume-rank"

# 인증
TOKEN_PATH = "/oauth2/tokenP"
APPROVAL_PATH = "/oauth2/Approval"

# H0STCNT0 체결 필드 순서 (^ 구분)
PRICE_COLUMNS = [
    "MKSC_SHRN_ISCD", "STCK_CNTG_HOUR", "STCK_PRPR", "PRDY_VRSS_SIGN",
    "PRDY_VRSS", "PRDY_CTRT", "WGHN_AVRG_STCK_PRC", "STCK_OPRC",
    "STCK_HGPR", "STCK_LWPR", "ASKP1", "BIDP1", "CNTG_VOL", "ACML_VOL",
    "ACML_TR_PBMN", "SELN_CNTG_CSNU", "SHNU_CNTG_CSNU", "NTBY_CNTG_CSNU",
    "CTTR", "SELN_CNTG_SMTN", "SHNU_CNTG_SMTN", "CCLD_DVSN", "SHNU_RATE",
    "PRDY_VOL_VRSS_ACML_VOL_RATE", "OPRC_HOUR", "OPRC_VRSS_PRPR_SIGN",
    "OPRC_VRSS_PRPR", "HGPR_HOUR", "HGPR_VRSS_PRPR_SIGN", "HGPR_VRSS_PRPR",
    "LWPR_HOUR", "LWPR_VRSS_PRPR_SIGN", "LWPR_VRSS_PRPR", "BSOP_DATE",
    "NEW_MKOP_CLS_CODE", "TRHT_YN", "ASKP_RSQN1", "BIDP_RSQN1",
    "TOTAL_ASKP_RSQN", "TOTAL_BIDP_RSQN", "VOL_TNRT",
    "PRDY_SMNS_HOUR_ACML_VOL", "PRDY_SMNS_HOUR_ACML_VOL_RATE",
    "HOUR_CLS_CODE", "MRKT_TRTM_CLS_CODE", "VI_STND_PRC",
]

# H0STASP0 호가 선두 필드 인덱스 (^ 구분). 선두 45필드만 확정 사용, 나머지는 raw 보관.
# 0:종목 1:영업시간 2:시간구분 | 3~12:매도호가1~10 13~22:매수호가1~10
# 23~32:매도잔량1~10 33~42:매수잔량1~10 | 43:총매도잔량 44:총매수잔량
QUOTE_IDX = {
    "symbol": 0, "hour": 1,
    "ask": slice(3, 13), "bid": slice(13, 23),
    "ask_qty": slice(23, 33), "bid_qty": slice(33, 43),
    "total_ask_qty": 43, "total_bid_qty": 44,
}
```

- [ ] **Step 2: import 확인**

Run: `.venv/bin/python -c "from manju.kis.constants import PRICE_COLUMNS, QUOTE_IDX; print(len(PRICE_COLUMNS), QUOTE_IDX['total_bid_qty'])"`
Expected: `46 44`

- [ ] **Step 3: Commit**

```bash
git add manju/kis/constants.py && git commit -m "feat: KIS TR ids and realtime field layouts"
```

---

## Task 3: 실시간 프레임 파서 — `kis/parse.py`

KIS 실시간 프레임(`0|tr_id|count|^payload`)을 `Trade`/`OrderBook` 리스트로. **순수함수 — TDD 핵심.**

**Files:**
- Create: `manju/kis/parse.py`
- Create: `tests/fixtures.py`
- Test: `tests/test_parse.py`

- [ ] **Step 1: 픽스처 작성**

체결 46필드, 호가는 선두 45필드 + 꼬리 더미. (필드값은 형식 검증용 합성 데이터)

```python
# tests/fixtures.py
# H0STCNT0 체결: PRICE_COLUMNS 순서대로 46개 필드
_TRADE_FIELDS = [
    "005930", "090001", "70000", "2",        # 종목 시각 현재가 부호
    "5000", "12.5", "69000", "63000",          # 전일대비 등락률 가중평균 시가
    "71000", "62500", "70100", "70000",        # 고가 저가 매도1 매수1
    "10", "1000", "70000000", "400",           # 체결량 누적량 누적대금 매도체결수
    "600", "200", "180.5", "300", "700",       # 매수체결수 순매수 체결강도 매도합 매수합
    "1", "57.1", "120.0", "090000", "2",       # 체결구분 매수비율 거래량대비 시가시각 시가부호
    "7000", "090030", "2", "8000",             # 시가대비 고가시각 고가부호 고가대비
    "085900", "5", "500", "20260601",          # 저가시각 저가부호 저가대비 영업일자
    "0", "N", "50", "80",                      # 마감코드 거래정지 매도잔량1 매수잔량1
    "500", "900", "1.5",                       # 총매도잔량 총매수잔량 거래회전율
    "0", "0", "0", "0", "73500",               # 전일동시간 전일비율 시간코드 장운영 VI기준가
]
TRADE_FRAME = "0|H0STCNT0|001|" + "^".join(_TRADE_FIELDS)

# H0STASP0 호가: 선두 45필드(인덱스 0~44) + 꼬리 더미 5개
_QUOTE_HEAD = (
    ["005930", "090001", "0"]                         # 0 종목 / 1 시각 / 2 시간구분
    + [str(70100 + i * 100) for i in range(10)]        # 3~12 매도호가1~10
    + [str(70000 - i * 100) for i in range(10)]        # 13~22 매수호가1~10
    + [str(i + 1) for i in range(10)]                  # 23~32 매도잔량1~10
    + [str(i + 11) for i in range(10)]                 # 33~42 매수잔량1~10
    + ["55", "155"]                                    # 43 총매도잔량 / 44 총매수잔량
)
QUOTE_FRAME = "0|H0STASP0|001|" + "^".join(_QUOTE_HEAD + ["0", "0", "0", "0", "0"])
```

- [ ] **Step 2: 실패하는 테스트 작성**

```python
# tests/test_parse.py
from datetime import datetime
from manju.kis.parse import parse_frame
from manju.models import Trade, OrderBook
from tests.fixtures import TRADE_FRAME, QUOTE_FRAME

RECV = datetime(2026, 6, 1, 9, 0, 1)


def test_parse_trade_frame():
    events = parse_frame(TRADE_FRAME, RECV)
    assert len(events) == 1
    t = events[0]
    assert isinstance(t, Trade)
    assert t.symbol == "005930"
    assert t.price == 70000
    assert t.change_rate == 12.5
    assert t.strength == 180.5
    assert t.ccld_dvsn == "1"
    assert t.total_bid_qty == 900
    assert t.vi_std_price == 73500
    assert t.market_ts == datetime(2026, 6, 1, 9, 0, 1)


def test_parse_quote_frame():
    events = parse_frame(QUOTE_FRAME, RECV)
    assert len(events) == 1
    ob = events[0]
    assert isinstance(ob, OrderBook)
    assert ob.symbol == "005930"
    assert ob.asks[0] == 70100
    assert ob.bids[9] == 70000 - 900
    assert ob.ask_qtys[0] == 1
    assert ob.total_bid_qty == 155


def test_parse_system_frame_returns_empty():
    # JSON 시스템 메시지(구독확인/PINGPONG)는 이벤트 없음
    assert parse_frame('{"header":{"tr_id":"PINGPONG"}}', RECV) == []


def test_parse_multi_count_trade():
    # count=2 → 두 레코드(46필드*2)
    head, _, payload = TRADE_FRAME.partition("001|")
    frame = "0|H0STCNT0|002|" + payload + "^" + payload
    events = parse_frame(frame, RECV)
    assert len(events) == 2
    assert all(isinstance(e, Trade) for e in events)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_parse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manju.kis.parse'`

- [ ] **Step 4: 최소 구현**

```python
# manju/kis/parse.py
"""KIS 실시간 프레임 파서. 순수함수 (네트워크 없음)."""
from __future__ import annotations
from datetime import datetime
from manju.models import Trade, OrderBook
from manju.kis.constants import TRADE_TR, QUOTE_TR, PRICE_COLUMNS, QUOTE_IDX


def _ts(date_str: str, hms: str, recv: datetime) -> datetime:
    """BSOP_DATE(YYYYMMDD) + 시각(HHMMSS) → datetime. date 없으면 recv 날짜 사용."""
    hms = (hms or "").zfill(6)
    if date_str and len(date_str) == 8:
        d = datetime.strptime(date_str, "%Y%m%d").date()
    else:
        d = recv.date()
    return datetime(d.year, d.month, d.day,
                    int(hms[0:2]), int(hms[2:4]), int(hms[4:6]))


def _to_int(v: str) -> int:
    return int(float(v)) if v not in ("", None) else 0


def _trade(fields: list[str], recv: datetime) -> Trade:
    f = dict(zip(PRICE_COLUMNS, fields))
    return Trade(
        symbol=f["MKSC_SHRN_ISCD"],
        market_ts=_ts(f.get("BSOP_DATE", ""), f["STCK_CNTG_HOUR"], recv),
        recv_ts=recv,
        price=_to_int(f["STCK_PRPR"]),
        change_rate=float(f["PRDY_CTRT"] or 0),
        volume=_to_int(f["CNTG_VOL"]),
        cum_volume=_to_int(f["ACML_VOL"]),
        cum_value=_to_int(f["ACML_TR_PBMN"]),
        strength=float(f["CTTR"] or 0),
        ccld_dvsn=f["CCLD_DVSN"],
        ask1=_to_int(f["ASKP1"]), bid1=_to_int(f["BIDP1"]),
        ask1_qty=_to_int(f["ASKP_RSQN1"]), bid1_qty=_to_int(f["BIDP_RSQN1"]),
        total_ask_qty=_to_int(f["TOTAL_ASKP_RSQN"]),
        total_bid_qty=_to_int(f["TOTAL_BIDP_RSQN"]),
        vi_std_price=_to_int(f["VI_STND_PRC"]),
        raw="^".join(fields),
    )


def _quote(fields: list[str], recv: datetime) -> OrderBook:
    return OrderBook(
        symbol=fields[QUOTE_IDX["symbol"]],
        market_ts=_ts("", fields[QUOTE_IDX["hour"]], recv),
        recv_ts=recv,
        asks=[_to_int(x) for x in fields[QUOTE_IDX["ask"]]],
        bids=[_to_int(x) for x in fields[QUOTE_IDX["bid"]]],
        ask_qtys=[_to_int(x) for x in fields[QUOTE_IDX["ask_qty"]]],
        bid_qtys=[_to_int(x) for x in fields[QUOTE_IDX["bid_qty"]]],
        total_ask_qty=_to_int(fields[QUOTE_IDX["total_ask_qty"]]),
        total_bid_qty=_to_int(fields[QUOTE_IDX["total_bid_qty"]]),
        raw="^".join(fields),
    )


def parse_frame(raw: str, recv: datetime) -> list:
    """실시간 프레임 → [Trade|OrderBook]. 시스템 메시지(JSON)는 []."""
    if not raw or raw[0] not in ("0", "1"):
        return []  # 시스템 메시지(구독확인/PINGPONG)
    parts = raw.split("|")
    if len(parts) < 4:
        return []
    tr_id, count, payload = parts[1], int(parts[2]), parts[3]
    fields = payload.split("^")
    if tr_id == TRADE_TR:
        n = len(PRICE_COLUMNS)
        return [_trade(fields[i * n:(i + 1) * n], recv) for i in range(count)]
    if tr_id == QUOTE_TR:
        n = 45  # 선두 45필드 단위(꼬리 더미 포함 count>1은 균등 분할)
        chunk = len(fields) // count
        return [_quote(fields[i * chunk:(i + 1) * chunk], recv) for i in range(count)]
    return []
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_parse.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add manju/kis/parse.py tests/fixtures.py tests/test_parse.py && git commit -m "feat: parse KIS realtime trade/quote frames"
```

---

## Task 4: 인증 — `kis/auth.py`

`access_token`(REST)과 `approval_key`(WS) 발급. POST 2개. 순수 요청 구성은 단위 테스트, 실발급은 통합 검증.

**Files:**
- Create: `manju/kis/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: 실패하는 테스트 작성 (requests를 monkeypatch)**

```python
# tests/test_auth.py
import manju.kis.auth as auth
from manju.config import Config

CFG = Config(app_key="AK", app_secret="AS", account_no="12345678", is_paper=False)


class _Resp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def test_issue_token_posts_correct_payload(monkeypatch):
    captured = {}
    def fake_post(url, json=None, timeout=None):
        captured["url"] = url; captured["json"] = json
        return _Resp({"access_token": "TOK", "expires_in": 86400})
    monkeypatch.setattr(auth.requests, "post", fake_post)

    tok = auth.issue_access_token(CFG)
    assert tok == "TOK"
    assert captured["url"] == "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    assert captured["json"] == {
        "grant_type": "client_credentials", "appkey": "AK", "appsecret": "AS"}


def test_issue_approval_uses_secretkey_field(monkeypatch):
    captured = {}
    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _Resp({"approval_key": "APPR"})
    monkeypatch.setattr(auth.requests, "post", fake_post)

    key = auth.issue_approval_key(CFG)
    assert key == "APPR"
    # Approval 엔드포인트는 appsecret이 아니라 secretkey 필드 사용
    assert captured["json"]["secretkey"] == "AS"
    assert "appsecret" not in captured["json"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manju.kis.auth'`

- [ ] **Step 3: 최소 구현**

```python
# manju/kis/auth.py
"""KIS OAuth: access_token(REST), approval_key(WebSocket) 발급."""
from __future__ import annotations
import requests
from manju.config import Config
from manju.kis.constants import TOKEN_PATH, APPROVAL_PATH


def issue_access_token(cfg: Config) -> str:
    r = requests.post(
        cfg.base_url + TOKEN_PATH,
        json={"grant_type": "client_credentials",
              "appkey": cfg.app_key, "appsecret": cfg.app_secret},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def issue_approval_key(cfg: Config) -> str:
    # 주의: Approval 엔드포인트는 'secretkey' 필드명을 사용 (tokenP의 appsecret과 다름)
    r = requests.post(
        cfg.base_url + APPROVAL_PATH,
        json={"grant_type": "client_credentials",
              "appkey": cfg.app_key, "secretkey": cfg.app_secret},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["approval_key"]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_auth.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 통합 검증 (실제 발급 — secrets.yaml 필요)**

`secrets.yaml`에 실제 키를 채운 뒤 실행:
```bash
.venv/bin/python -c "from manju.config import Config; from manju.kis import auth; c=Config.load(); print('token', auth.issue_access_token(c)[:8], '...'); print('approval', auth.issue_approval_key(c)[:8], '...')"
```
Expected: `token <8자> ...` 와 `approval <8자> ...` 가 출력(빈 문자열/예외 없음). 401/403이면 키·is_paper(실전/모의 base가 다름) 확인.

- [ ] **Step 6: Commit**

```bash
git add manju/kis/auth.py tests/test_auth.py && git commit -m "feat: KIS access_token and approval_key issuance"
```

---

## Task 5: 거래대금 순위 — `kis/rest.py`

`volume-rank`로 거래대금 상위 N 종목코드. 순수 파싱은 단위 테스트, 실호출은 통합 검증(파라미터·필드명 확인).

**Files:**
- Create: `manju/kis/rest.py`
- Test: `tests/test_rest.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_rest.py
import manju.kis.rest as rest
from manju.config import Config

CFG = Config(app_key="AK", app_secret="AS", account_no="12345678", is_paper=False)


class _Resp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def test_top_symbols_extracts_codes_in_rank_order(monkeypatch):
    payload = {"output": [
        {"mksc_shrn_iscd": "111111", "data_rank": "1"},
        {"mksc_shrn_iscd": "222222", "data_rank": "2"},
        {"mksc_shrn_iscd": "333333", "data_rank": "3"},
    ]}
    def fake_get(url, headers=None, params=None, timeout=None):
        assert headers["tr_id"] == "FHPST01710000"
        assert params["FID_BLNG_CLS_CODE"] == "3"   # 거래대금순
        return _Resp(payload)
    monkeypatch.setattr(rest.requests, "get", fake_get)

    codes = rest.top_symbols_by_value("TOK", CFG, n=2)
    assert codes == ["111111", "222222"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_rest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manju.kis.rest'`

- [ ] **Step 3: 최소 구현**

```python
# manju/kis/rest.py
"""KIS REST: 거래대금 상위 종목 조회."""
from __future__ import annotations
import requests
from manju.config import Config
from manju.kis.constants import VOLUME_RANK_TR, VOLUME_RANK_PATH


def top_symbols_by_value(token: str, cfg: Config, n: int) -> list[str]:
    """거래대금 상위 n개 종목코드(순위순)."""
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
        "tr_id": VOLUME_RANK_TR,
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",        # 0000:전체
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "3",        # 3:거래대금순
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "",
        "FID_VOL_CNT": "",
        "FID_INPUT_DATE_1": "",
    }
    r = requests.get(cfg.base_url + VOLUME_RANK_PATH, headers=headers,
                     params=params, timeout=10)
    r.raise_for_status()
    rows = r.json().get("output", [])
    return [row["mksc_shrn_iscd"] for row in rows[:n]]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_rest.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 통합 검증 (실호출 — 응답 필드명 확인)**

```bash
.venv/bin/python -c "from manju.config import Config; from manju.kis import auth, rest; c=Config.load(); t=auth.issue_access_token(c); print(rest.top_symbols_by_value(t, c, 20))"
```
Expected: 6자리 종목코드 20개 리스트. 빈 리스트/KeyError면 KIS 포털의 volume-rank 문서로 `output` 필드명(`mksc_shrn_iscd`)·파라미터를 대조해 수정.

- [ ] **Step 6: Commit**

```bash
git add manju/kis/rest.py tests/test_rest.py && git commit -m "feat: volume-rank top symbols by trading value"
```

---

## Task 6: WebSocket 클라이언트 — `kis/ws.py`

연결·구독메시지 구성·수신·PINGPONG·재연결. 메시지 구성은 순수 단위 테스트, 실접속은 통합 검증.

**Files:**
- Create: `manju/kis/ws.py`
- Test: `tests/test_ws.py`

- [ ] **Step 1: 실패하는 테스트 작성 (순수 메시지 빌더)**

```python
# tests/test_ws.py
import json
from manju.kis.ws import build_sub_message


def test_build_register_message():
    msg = build_sub_message("APPR", "H0STCNT0", "005930", register=True)
    d = json.loads(msg)
    assert d["header"]["approval_key"] == "APPR"
    assert d["header"]["tr_type"] == "1"        # 등록
    assert d["header"]["custtype"] == "P"
    assert d["body"]["input"] == {"tr_id": "H0STCNT0", "tr_key": "005930"}


def test_build_unregister_message():
    msg = build_sub_message("APPR", "H0STASP0", "000660", register=False)
    assert json.loads(msg)["header"]["tr_type"] == "2"   # 해지
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_ws.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manju.kis.ws'`

- [ ] **Step 3: 최소 구현**

```python
# manju/kis/ws.py
"""KIS 실시간 WebSocket 클라이언트.

연결 → 구독메시지 송신 → 프레임 수신(async iterator) → PINGPONG 응답.
연결 끊기면 백오프 재연결 후 현재 구독을 자동 재등록.
실시간 데이터(0/1로 시작)는 호출측에 그대로 yield, 시스템 메시지(JSON)는 내부 처리.
"""
from __future__ import annotations
import asyncio
import json
import logging
from collections.abc import AsyncIterator

import websockets

logger = logging.getLogger(__name__)


def build_sub_message(approval_key: str, tr_id: str, tr_key: str,
                      register: bool = True) -> str:
    return json.dumps({
        "header": {"approval_key": approval_key, "custtype": "P",
                   "tr_type": "1" if register else "2", "content-type": "utf-8"},
        "body": {"input": {"tr_id": tr_id, "tr_key": tr_key}},
    })


class KISWebSocket:
    def __init__(self, ws_url: str, approval_key: str):
        self._url = ws_url
        self._approval = approval_key
        self._ws = None
        self._subs: set[tuple[str, str]] = set()   # (tr_id, symbol)

    async def connect(self) -> None:
        self._ws = await websockets.connect(self._url, ping_interval=None)
        # 재연결이면 기존 구독 복원
        for tr_id, sym in list(self._subs):
            await self._ws.send(build_sub_message(self._approval, tr_id, sym, True))
        logger.info("WS connected: %s (resubscribed %d)", self._url, len(self._subs))

    async def register(self, tr_id: str, symbol: str) -> None:
        self._subs.add((tr_id, symbol))
        await self._ws.send(build_sub_message(self._approval, tr_id, symbol, True))

    async def unregister(self, tr_id: str, symbol: str) -> None:
        self._subs.discard((tr_id, symbol))
        await self._ws.send(build_sub_message(self._approval, tr_id, symbol, False))

    async def frames(self) -> AsyncIterator[str]:
        """실시간 데이터 프레임만 yield. PINGPONG은 자동 응답. 끊기면 재연결."""
        while True:
            try:
                raw = await self._ws.recv()
            except websockets.ConnectionClosed:
                logger.warning("WS closed, reconnecting...")
                await self._reconnect()
                continue
            if raw and raw[0] in ("0", "1"):
                yield raw
            else:
                # 시스템 메시지: PINGPONG이면 pong
                try:
                    if json.loads(raw)["header"]["tr_id"] == "PINGPONG":
                        await self._ws.pong(raw)
                except (json.JSONDecodeError, KeyError):
                    pass

    async def _reconnect(self) -> None:
        delay = 1
        while True:
            try:
                await self.connect()
                return
            except Exception as e:               # noqa: BLE001 - 재연결은 모든 예외 재시도
                logger.warning("reconnect failed (%s), retry in %ds", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_ws.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 통합 검증 (실접속 — 장중에 1종목 30초 수신)**

```bash
.venv/bin/python - <<'PY'
import asyncio
from manju.config import Config
from manju.kis import auth
from manju.kis.ws import KISWebSocket

async def main():
    c = Config.load()
    ws = KISWebSocket(c.ws_url, auth.issue_approval_key(c))
    await ws.connect()
    await ws.register("H0STCNT0", "005930")
    await ws.register("H0STASP0", "005930")
    n = 0
    async for raw in ws.frames():
        print(raw[:80]); n += 1
        if n >= 5: break

asyncio.run(asyncio.wait_for(main(), timeout=60))
PY
```
Expected (장중): `0|H0STCNT0|001|005930^...` / `0|H0STASP0|001|005930^...` 형태 프레임 5개. 장마감/주말이면 프레임이 안 올 수 있으니 장중에 실행.

- [ ] **Step 6: Commit**

```bash
git add manju/kis/ws.py tests/test_ws.py && git commit -m "feat: async KIS websocket with subscribe/pingpong/reconnect"
```

---

## Task 7: 구독 관리 — `collector/subscriber.py`

universe(원하는 종목 집합)와 현재 구독을 비교해 등록/해지 액션을 산출. **종목당 등록 2건(체결+호가), max_registrations 한도 준수.** 순수 로직 — TDD.

**Files:**
- Create: `manju/collector/subscriber.py`
- Test: `tests/test_subscriber.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_subscriber.py
from manju.collector.subscriber import plan_changes


def test_initial_registration_respects_limit():
    # 한도 4건 = 종목 2개 (종목당 체결+호가 2건)
    to_reg, to_unreg, active = plan_changes(
        current=set(), desired=["A", "B", "C"], max_reg=4)
    assert active == ["A", "B"]                       # 한도 내 상위 2종목만
    assert set(to_reg) == {("H0STCNT0", "A"), ("H0STASP0", "A"),
                           ("H0STCNT0", "B"), ("H0STASP0", "B")}
    assert to_unreg == []


def test_rotation_unregisters_dropped_and_registers_new():
    to_reg, to_unreg, active = plan_changes(
        current={"A", "B"}, desired=["B", "C"], max_reg=4)
    assert set(active) == {"B", "C"}
    assert set(to_unreg) == {("H0STCNT0", "A"), ("H0STASP0", "A")}
    assert set(to_reg) == {("H0STCNT0", "C"), ("H0STASP0", "C")}


def test_no_change_when_universe_stable():
    to_reg, to_unreg, active = plan_changes(
        current={"A", "B"}, desired=["A", "B"], max_reg=10)
    assert to_reg == [] and to_unreg == []
    assert set(active) == {"A", "B"}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_subscriber.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

```python
# manju/collector/subscriber.py
"""universe 변경 → WS 등록/해지 액션 산출. 종목당 체결+호가 2건."""
from __future__ import annotations
from manju.kis.constants import TRADE_TR, QUOTE_TR

_PER_SYMBOL = (TRADE_TR, QUOTE_TR)   # 종목당 등록 TR 2개


def plan_changes(current: set[str], desired: list[str], max_reg: int):
    """
    Args:
        current: 현재 구독 중인 종목 집합
        desired: 원하는 종목(순위순)
        max_reg: 세션 실시간 등록 한도(건수). 종목당 2건.
    Returns:
        (to_register, to_unregister, active_symbols)
        to_*: [(tr_id, symbol), ...]
    """
    max_symbols = max_reg // len(_PER_SYMBOL)
    active = desired[:max_symbols]
    active_set = set(active)

    to_unreg = [(tr, s) for s in current - active_set for tr in _PER_SYMBOL]
    to_reg = [(tr, s) for s in active if s not in current for tr in _PER_SYMBOL]
    return to_reg, to_unreg, active
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_subscriber.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add manju/collector/subscriber.py tests/test_subscriber.py && git commit -m "feat: subscription planner with registration limit"
```

---

## Task 8: 녹음 — `collector/recorder.py`

`Trade`/`OrderBook`를 버퍼링 후 parquet로 flush. `data/ticks/{date}/{symbol}-{seq}.parquet`, `data/quotes/{date}/{symbol}-{seq}.parquet`. raw 컬럼 포함. (parquet in-place append는 피하고 flush마다 새 파일 — ReplayFeed가 전부 읽어 시간순 정렬)

**Files:**
- Create: `manju/collector/recorder.py`
- Test: `tests/test_recorder.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_recorder.py
from datetime import datetime
import pyarrow.parquet as pq
from manju.collector.recorder import Recorder
from manju.models import Trade, OrderBook


def _trade(sym, sec):
    ts = datetime(2026, 6, 1, 9, 0, sec)
    return Trade(symbol=sym, market_ts=ts, recv_ts=ts, price=70000, change_rate=1.0,
                 volume=1, cum_volume=1, cum_value=1, strength=100.0, ccld_dvsn="1",
                 ask1=70100, bid1=70000, ask1_qty=1, bid1_qty=1,
                 total_ask_qty=1, total_bid_qty=1, vi_std_price=0, raw="r")


def _quote(sym, sec):
    ts = datetime(2026, 6, 1, 9, 0, sec)
    return OrderBook(symbol=sym, market_ts=ts, recv_ts=ts,
                     asks=[1]*10, bids=[1]*10, ask_qtys=[1]*10, bid_qtys=[1]*10,
                     total_ask_qty=10, total_bid_qty=10, raw="r")


def test_recorder_writes_partitioned_parquet(tmp_path):
    rec = Recorder(tmp_path)
    rec.record(_trade("005930", 1))
    rec.record(_trade("005930", 2))
    rec.record(_quote("005930", 1))
    rec.flush()

    tick_files = list((tmp_path / "ticks" / "2026-06-01").glob("005930-*.parquet"))
    quote_files = list((tmp_path / "quotes" / "2026-06-01").glob("005930-*.parquet"))
    assert len(tick_files) == 1 and len(quote_files) == 1

    t = pq.read_table(tick_files[0]).to_pylist()
    assert len(t) == 2
    assert t[0]["symbol"] == "005930" and t[0]["ccld_dvsn"] == "1"


def test_flush_clears_buffer(tmp_path):
    rec = Recorder(tmp_path)
    rec.record(_trade("000660", 1))
    rec.flush()
    rec.flush()   # 두 번째 flush는 빈 버퍼 → 추가 파일 없음
    files = list((tmp_path / "ticks" / "2026-06-01").glob("000660-*.parquet"))
    assert len(files) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_recorder.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

```python
# manju/collector/recorder.py
"""Trade/OrderBook → parquet 녹음 (date/symbol 파티셔닝, flush마다 새 파일)."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from manju.models import Trade, OrderBook


class Recorder:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._seq = 0
        # (kind, date, symbol) -> list[dict rows]
        self._buf: dict[tuple, list[dict]] = defaultdict(list)

    def record(self, event) -> None:
        kind = "ticks" if isinstance(event, Trade) else "quotes"
        date = event.market_ts.strftime("%Y-%m-%d")
        self._buf[(kind, date, event.symbol)].append(event.to_row())

    def flush(self) -> None:
        if not self._buf:
            return
        self._seq += 1
        for (kind, date, symbol), rows in self._buf.items():
            out_dir = self.data_dir / kind / date
            out_dir.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pylist(rows)
            pq.write_table(table, out_dir / f"{symbol}-{self._seq:06d}.parquet")
        self._buf.clear()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_recorder.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add manju/collector/recorder.py tests/test_recorder.py && git commit -m "feat: parquet recorder partitioned by date/symbol"
```

---

## Task 9: 재생 — `replay/feed.py`

녹음된 parquet(ticks+quotes)을 읽어 `market_ts`(동률 시 `recv_ts`) 순으로 `Trade`/`OrderBook`를 yield. **녹음 데이터가 동일 스키마로 재생 가능함을 증명.**

**Files:**
- Create: `manju/replay/feed.py`
- Test: `tests/test_replay.py`

- [ ] **Step 1: 실패하는 테스트 작성 (Recorder 출력을 직접 재생)**

```python
# tests/test_replay.py
from datetime import datetime
from manju.collector.recorder import Recorder
from manju.replay.feed import ReplayFeed
from manju.models import Trade, OrderBook


def _trade(sym, sec):
    ts = datetime(2026, 6, 1, 9, 0, sec)
    return Trade(symbol=sym, market_ts=ts, recv_ts=ts, price=70000, change_rate=1.0,
                 volume=1, cum_volume=1, cum_value=1, strength=100.0, ccld_dvsn="1",
                 ask1=70100, bid1=70000, ask1_qty=1, bid1_qty=1,
                 total_ask_qty=1, total_bid_qty=1, vi_std_price=0, raw="r")


def _quote(sym, sec):
    ts = datetime(2026, 6, 1, 9, 0, sec)
    return OrderBook(symbol=sym, market_ts=ts, recv_ts=ts,
                     asks=[1]*10, bids=[1]*10, ask_qtys=[1]*10, bid_qtys=[1]*10,
                     total_ask_qty=10, total_bid_qty=10, raw="r")


def test_replay_yields_time_ordered_events(tmp_path):
    rec = Recorder(tmp_path)
    rec.record(_trade("005930", 3))
    rec.record(_quote("005930", 1))
    rec.record(_trade("005930", 2))
    rec.flush()

    events = list(ReplayFeed(tmp_path, "2026-06-01").events())
    secs = [e.market_ts.second for e in events]
    assert secs == [1, 2, 3]                      # 시간순
    assert isinstance(events[0], OrderBook)        # 1초=호가
    assert isinstance(events[1], Trade)            # 2초=체결
    assert events[1].price == 70000               # 스키마 복원 확인


def test_replay_empty_date_yields_nothing(tmp_path):
    assert list(ReplayFeed(tmp_path, "2099-01-01").events()) == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/test_replay.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 최소 구현**

```python
# manju/replay/feed.py
"""ReplayFeed: 녹음 parquet을 시간순으로 재생. LiveFeed와 동일한 Trade/OrderBook 산출."""
from __future__ import annotations
from pathlib import Path
from collections.abc import Iterator
import pyarrow.parquet as pq
from manju.models import Trade, OrderBook


class ReplayFeed:
    def __init__(self, data_dir: Path, date: str):
        self.data_dir = Path(data_dir)
        self.date = date

    def _load(self, kind: str, cls) -> list:
        d = self.data_dir / kind / self.date
        if not d.exists():
            return []
        out = []
        for f in d.glob("*.parquet"):
            for row in pq.read_table(f).to_pylist():
                out.append(cls.from_row(row))
        return out

    def events(self) -> Iterator:
        merged = self._load("ticks", Trade) + self._load("quotes", OrderBook)
        merged.sort(key=lambda e: (e.market_ts, e.recv_ts))
        yield from merged
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/test_replay.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add manju/replay/feed.py tests/test_replay.py && git commit -m "feat: ReplayFeed time-ordered playback of recorded parquet"
```

---

## Task 10: 오케스트레이션 — `collector/runner.py`

asyncio로 (1) universe 폴링 루프 + (2) 프레임 수신→파싱→녹음 루프 + (3) 주기적 flush를 묶는다. 통합 컴포넌트라 실행 가능한 main + 통합 검증.

**Files:**
- Create: `manju/collector/runner.py`
- Modify: `pyproject.toml` (콘솔 스크립트 등록)

- [ ] **Step 1: runner.py 작성**

```python
# manju/collector/runner.py
"""수집기 메인: universe 폴링 + 프레임 수신/파싱/녹음 + 주기 flush."""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime

from manju.config import Config
from manju.kis import auth, rest
from manju.kis.ws import KISWebSocket
from manju.kis.parse import parse_frame
from manju.kis.constants import TRADE_TR, QUOTE_TR
from manju.collector.subscriber import plan_changes
from manju.collector.recorder import Recorder

logger = logging.getLogger(__name__)
_TR = {TRADE_TR, QUOTE_TR}


async def _universe_loop(cfg: Config, token: str, ws: KISWebSocket, state: dict):
    """주기적으로 거래대금 상위 재선정 → 구독 등록/해지."""
    while True:
        try:
            desired = rest.top_symbols_by_value(token, cfg, cfg.universe_size)
            to_reg, to_unreg, active = plan_changes(
                state["subscribed"], desired, cfg.max_registrations)
            for tr_id, sym in to_unreg:
                await ws.unregister(tr_id, sym)
            for tr_id, sym in to_reg:
                await ws.register(tr_id, sym)
            state["subscribed"] = set(active)
            logger.info("universe: %d active", len(active))
        except Exception as e:                       # noqa: BLE001
            logger.warning("universe loop error: %s", e)
        await asyncio.sleep(cfg.poll_interval_sec)


async def _recv_loop(ws: KISWebSocket, recorder: Recorder):
    async for raw in ws.frames():
        for event in parse_frame(raw, datetime.now()):
            recorder.record(event)


async def _flush_loop(recorder: Recorder, interval: int = 10):
    while True:
        await asyncio.sleep(interval)
        recorder.flush()


async def run(cfg: Config) -> None:
    token = auth.issue_access_token(cfg)
    ws = KISWebSocket(cfg.ws_url, auth.issue_approval_key(cfg))
    await ws.connect()
    recorder = Recorder(cfg.data_dir)
    state = {"subscribed": set()}
    try:
        await asyncio.gather(
            _universe_loop(cfg, token, ws, state),
            _recv_loop(ws, recorder),
            _flush_loop(recorder),
        )
    finally:
        recorder.flush()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run(Config.load()))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: pyproject.toml에 콘솔 스크립트 추가**

`pyproject.toml`의 `[project]` 테이블 바로 뒤(예: `dependencies` 배열 다음)에 아래 테이블을 추가:

```toml
[project.scripts]
manju-collect = "manju.collector.runner:main"
```

- [ ] **Step 3: 재설치 후 import/엔트리 확인**

Run:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && .venv/bin/pip install -e ".[dev]" && .venv/bin/python -c "from manju.collector.runner import run, main; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: 전체 단위 테스트 통과 확인 (회귀)**

Run: `.venv/bin/pytest -v`
Expected: 모든 테스트 PASS (parse 4 + models 2 + auth 2 + rest 1 + ws 2 + subscriber 3 + recorder 2 + replay 2)

- [ ] **Step 5: Commit**

```bash
git add manju/collector/runner.py pyproject.toml && git commit -m "feat: collector runner orchestration + console script"
```

---

## Task 11: 종단 통합 검증 (장중 실행 → 재생)

수집기를 장중 몇 분 돌려 실제 데이터를 녹음하고, ReplayFeed로 재생해 스키마·시간순·건수를 확인한다. (단위 테스트 아님 — 수동 검증 절차)

- [ ] **Step 1: 장중 2~3분 녹음 실행**

`secrets.yaml` 채운 상태로, 장중(09:00~15:30)에 실행 후 2~3분 뒤 Ctrl+C:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && .venv/bin/manju-collect
```
Expected 로그: `universe: 20 active` 출력, 이후 에러 없이 동작. (`data/` 아래 parquet 생성)

- [ ] **Step 2: 녹음 결과 확인**

Run:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && find data -name '*.parquet' | head && \
.venv/bin/python -c "import glob,pyarrow.parquet as pq; fs=glob.glob('data/ticks/*/*.parquet'); print('tick files', len(fs)); print('rows', sum(pq.read_table(f).num_rows for f in fs))"
```
Expected: tick 파일 여러 개, rows > 0.

- [ ] **Step 3: 재생 검증 (시간순 단조 증가 + 스키마 복원)**

Run:
```bash
cd /Users/kimjaewon/Pluto/ManjuAgent && .venv/bin/python - <<'PY'
import datetime, glob, os
from manju.replay.feed import ReplayFeed
date = sorted(os.path.basename(d) for d in glob.glob('data/ticks/*'))[-1]
evs = list(ReplayFeed('data', date).events())
print('events', len(evs))
ts = [e.market_ts for e in evs]
assert ts == sorted(ts), "시간순 정렬 위반"
print('first', type(evs[0]).__name__, evs[0].symbol, evs[0].market_ts)
print('ok: monotonic, schema restored')
PY
```
Expected: `events <N>` (N>0), 마지막 줄 `ok: monotonic, schema restored`.

- [ ] **Step 4: 재연결 동작 확인 (네트워크 차단 시뮬레이션)**

수집기 실행 중 Wi-Fi를 잠깐 껐다 켜고 로그 관찰:
Expected: `WS closed, reconnecting...` → `reconnect failed ... retry` → 복구 후 `WS connected ... (resubscribed N)`. 프로세스가 죽지 않고 녹음 재개.

- [ ] **Step 5: 검증 결과 기록 + Commit**

`docs/superpowers/plans/phase0-verification.md`에 실행일·녹음 건수·재생 결과·재연결 동작을 기록하고:
```bash
git add docs/superpowers/plans/phase0-verification.md && git commit -m "docs: phase0 end-to-end verification results"
```

---

## Phase 0 완료 기준 (Definition of Done)

- [ ] 단위 테스트 전부 통과 (`.venv/bin/pytest`)
- [ ] 장중 실행 시 거래대금 상위 ~20종목의 체결+호가가 `data/{ticks,quotes}/{date}/{symbol}-*.parquet`에 적재됨
- [ ] ReplayFeed가 녹음 데이터를 `market_ts` 단조 증가로, 동일 `Trade`/`OrderBook` 스키마로 재생
- [ ] WS 끊김 시 자동 재연결 + 구독 복원, 프로세스 생존
- [ ] raw 필드가 모든 레코드에 보관됨(향후 재파싱 대비)

---

## Self-Review 메모 (작성자 점검 결과)

- **스펙 커버리지(§8 수집기 동작):** [0]인증 Task4, [1]UniverseSelector Task5+runner, [2]Subscriber Task6(WS)+Task7(planner), [3]Recorder Task8, ReplayFeed Task9, 오케스트레이션 Task10, 검증 Task11. 모두 매핑됨.
- **YAGNI:** 다중 세션/계좌 확장·VI가격 계산·일봉 fetch는 Phase 0 범위 외로 제외(스펙 §8/§10 후속). 추상 인터페이스(LiveFeed 추상클래스) 미도입 — ReplayFeed와 runner의 수신 루프가 동일하게 `parse_frame`을 쓰므로 공통 계약은 `models.py`로 충분.
- **타입 일관성:** `Trade`/`OrderBook`(models) ↔ `parse_frame`(parse) ↔ `Recorder.record`/`to_row` ↔ `ReplayFeed.from_row` 명칭·필드 일치 확인. `plan_changes` 반환 `(to_reg,to_unreg,active)`를 runner가 동일 순서로 사용. WS 메서드 `register/unregister/frames/connect`를 runner·subscriber 액션과 일치 사용.
- **플레이스홀더 스캔:** 없음. volume-rank 파라미터/필드명은 Task5 Step5 통합검증에서 실응답 대조하도록 명시(추정→검증 경로).

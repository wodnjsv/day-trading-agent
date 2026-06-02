# 만쥬 트레이딩 에이전트 — 설계 문서

- 작성일: 2026-06-01
- 대상: 단타(스켈핑·스윙) 성향의 국내주식 자동매매 에이전트
- 출처 지식: `/Users/kimjaewon/Pluto/ManjuAgent`의 7개 md (만쥬 매매법 정리)

---

## 1. 목표와 비목표

**목표**
- 만쥬님의 단타 매매 철학(시황 판단 → 테마/주도주 발굴 → 종목선정 → 진입/청산 → 주문실행 → 복기)을 자동매매 에이전트로 구현한다.
- "꾸준한 수익"을 위해 **규율(손절·비중 관리)을 기계로 강제**한다. 만쥬님이 꼽은 최대 손실 원인이 "손절 타이밍 놓침(심리 붕괴)"이었던 점이 자동화의 핵심 명분이다.

**비목표 (YAGNI)**
- MVP에서 분산 인프라(메시지버스/멀티서비스) 도입하지 않음 — 단일 프로세스로 충분.
- 소수점/금액단위 매매 (KIS API 미지원 + 단타 부적합, §8 참조).
- 만쥬님 기법의 100% 모사 — 인코딩 가능한 규칙 중심으로 시작, 감각 영역은 점진 확장.

---

## 2. 핵심 결정사항

| # | 결정 | 선택 | 이유 |
|---|---|---|---|
| 1 | 두뇌 구조 | **하이브리드** (룰 실행 엔진 + LLM 분석 레이어) | 스켈핑은 ms~초 실행 필요(룰), 시황·테마·뉴스는 맥락 판단 필요(LLM) |
| 2 | 증권사 API | **한국투자증권 KIS** (REST + WebSocket) | macOS 크로스플랫폼, 실시간 호가/체결, 문서 양호 |
| 3 | 전략 구조 | **프레임워크 우선** (전략 플러그인) | 짝꿍·낙주·상따 등을 공통 인터페이스로 |
| 4 | 자율성 | **완전자동 + 강한 가드레일** | 리스크 거버너가 모든 주문 위에서 거부권 |
| 5 | 검증 경로 | **백테스트 → 소액 실거래** (모의투자 스킵) | 모의투자는 체결 현실 괴리가 커 단타 검증 부정확 |
| 6 | 두뇌↔엔진 경계 | **사이드루프 + "LLM은 Plan만, 방아쇠는 룰만"** | B의 적응성 + A의 결정론·백테스트 가능성 |
| 7 | 복기 학습 반영 | **소프트 + 제한적 하드** (N회 누적 + 범위제한) | 자기개선 + 과적합/드리프트 방어 |
| 8 | 백테스트 데이터 | **직접 실시간 수집 먼저** | 호가창 전략엔 과거 틱+호가 필수, 무료 API 미제공 |
| 9 | 체결강도 정의 | **직접 계산** (KIS 누적값 미사용) | 틱으로 우리가 정의·튜닝, 백테스트 재현 정확, '찰나의 가속' 포착 |
| 10 | 익절 규칙 | **대장주 연동 중심** | 만쥬 원래 방식에 충실 — 매수이유(대장주 상한가) 유지 동안 홀딩 |
| 11 | 전략 검증 방식 | **여러 전략 동시 비교** (단일 전략 베팅 X) | 짝꿍은 사례 빈도가 낮음 → 같은 데이터에 여러 detector를 돌려 realized 엣지로 비교. §13 |

---

## 3. 아키텍처 & 컴포넌트

세 개의 동시 실행 영역 + 공유 상태.

```
🧠 두뇌 루프 (LLM, 느림: 분~일)  =  "Strategist"
  • RegimeAnalyzer   시황 등급 → 비중 배수 (코스닥 거래대금)
  • ThemeCurator     테마 분류 + 대장-후속 페어 + 종목 선정 (LearningStore 참조)
  • NewsInterpreter  속보/뉴스 → 해지테마 시나리오
  • Reviewer         장 마감 후 복기 → TradeJournal + LearningStore

        │ writes Plan                  ▲ wakes on event
        ▼                             │
  📋 SHARED STATE (TradingPlan + Positions + PnL + EventQueue)
        │ reads Plan                  │ pushes event
        ▼                             │
⚡ 실행 루프 (룰, 빠름: ms~초)  =  "Executor"
  • MarketFeed       KIS WebSocket: 10호가 / 체결틱 / VI
  • EventDetector    5개 정량 트리거 감지 → 두뇌 깨움
  • SignalEngine     armed 전략들의 진입/청산 트리거 평가
  • OrderManager     IOC 스위핑 / 지정가 받치기 / 타임아웃 취소
  • PositionManager  보유·청산·페어연동 손절

        │ every order request
        ▼
🛡️ RiskGovernor (룰, 항상 ON) — 모든 주문의 게이트키퍼 (거부권)
        │ approved only
        ▼
🔌 KIS Broker Adapter (REST 주문 + WebSocket 실시간)
```

### 핵심 데이터 객체 — `TradingPlan`
두뇌가 쓰고 실행 루프가 읽는 단 하나의 계약:
- `regime`: 시황 등급 + 비중 배수 (BULL ×1.0 / NEUTRAL ×0.5 / BEAR ×0.2 / HALT ×0)
- `pairs[]`: 무장된 대장-후속 페어 (종목코드, 역할, 전략명, 파라미터)
- `watchlist[]`: 감시 종목 + 호가두께 후보 여부
- `scenarios[]`: 뉴스 대기 시나리오 (조건 → 행동)
- `risk_limits`: 그날의 한도값

### 학습 루프 (복기 → 다음날 반영)
```
복기(Reviewer) ─→ 📓 TradeJournal (raw, 사람이 읽음, 큰 건 위주)
               └─→ 🧠 LearningStore (structured: {패턴, 근거매매, 반복횟수, 제안})
                          │
   다음날 08:30 RegimeAnalyzer/ThemeCurator가 LearningStore + 최근 N일 Journal을
               *컨텍스트로 읽고* → TradingPlan 생성 (편향·제외·파라미터 반영)
```

**학습 반영 강도 (과적합 방어):**
- **소프트 학습**(편향/맥락): Strategist 프롬프트에 컨텍스트 주입 → watchlist·페어·테마 선정 영향. 실행 파라미터 불변.
- **하드 조정**(파라미터/블랙리스트): 손절폭·비중·종목제외 등 수치 변경. **동일 패턴 N회(예: 3회) 이상 누적** + **범위 제한(±일정%)** + 변경 로그 강조 시에만 발동.

### 컴포넌트 분리 원칙
- 두뇌·실행은 `TradingPlan` 하나로만 통신 → 독립 이해/테스트 가능.
- `RiskGovernor`는 실행 루프와 분리된 게이트 → 전략이 뭘 하든 손실 한도 강제.
- `MarketFeed`·`OrderManager`가 KIS에 묶이는 유일한 곳 → 증권사 교체 시 어댑터만 교체.

---

## 4. 데이터 흐름 (하루 사이클)

```
══ 장 마감 후 (15:30~)  🧠 두뇌 ══
  Reviewer: 당일 체결 → TradeJournal + LearningStore 갱신

══ 장 시작 전 (08:00~09:00)  🧠 두뇌 ══
  ① RegimeAnalyzer  코스닥 거래대금 추이 → 시황 등급 + 비중 배수
  ② ThemeCurator    테마+신규상장+LearningStore → 대장-후속 페어 + watchlist
  ③ NewsInterpreter 예정 이벤트 → 대기 시나리오
        ▼  📋 TradingPlan v0 → SHARED STATE

══ 장중 (09:00~15:30)  ⚡ 실행 (ms~초) ══
  MarketFeed → SignalEngine (페어 트리거 평가)
            → 🛡️ RiskGovernor (비중·한도) → OrderManager (IOC/지정가)
            → PositionManager (익절: 충분상승+시간 / 손절: ★대장주 상한가 붕괴 즉시★)
            → EventDetector (5개 트리거) → EventQueue.push → 🧠 두뇌 깨움
                  → TradingPlan v1 → SHARED STATE 원자적 교체
            → 🛡️ RiskGovernor 상시: 일일 손실한도 → HALT (전면 정지+청산)
```

### 3가지 핵심 규칙
1. **두뇌는 실행을 막지 않는다 (논블로킹).** LLM이 v1을 만드는 동안에도 실행은 v0로 계속. 새 Plan은 원자적 교체.
2. **방아쇠는 항상 룰.** LLM은 장 전/후 + 이벤트 시 Plan 갱신만. 진입/청산/손절은 전부 룰.
3. **HALT는 모든 것 위에 있다.** 일일 손실 한도·시황 서킷브레이커 발동 시 즉시 정지.

### 사이드루프 트리거 (LLM을 언제 깨우나)
**스케줄**: 장전(계획 수립) / 장중 5~10분(시황·테마 재평가) / 장후(복기).
**이벤트(룰이 감지 → 두뇌 호출)** — "애매한/새로운 상황"의 구체적 정의:

| # | 룰이 감지하는 정량 조건 | LLM에게 묻는 것 |
|---|---|---|
| 1 | watchlist 외 종목이 거래대금/등락률 임계치 돌파 | 새 테마? 어느 페어? 무장? |
| 2 | 뉴스피드 속보/키워드 감지 | 어느 해지테마·관련주? 시나리오? |
| 3 | 코스닥 거래대금/지수 급변(임계치) | 시황 등급·비중 배수 조정? |
| 4 | 현재 페어 대장주가 순위/거래대금 밀림 | 페어 재구성·대장주 교체? |
| 5 | armed 전략 어디에도 안 맞는 강한 신호 | 무시 vs 새 전략 무장? |

---

## 5. 전략 플러그인 인터페이스

전략은 순수 함수에 가깝게 — 시장 데이터를 받아 **의도 시그널**만 내보내고 주문/증권사는 모른다. (백테스트·단위테스트 용이)

```python
class Strategy(Protocol):
    name: str
    def required_symbols(self, armed: ArmedStrategy) -> list[Symbol]: ...
    def evaluate(self, ctx: MarketContext, armed: ArmedStrategy,
                 position: Position | None) -> list[Signal]: ...

@dataclass
class MarketContext:
    quotes: dict[Symbol, OrderBook]      # 10호가 잔량
    last_trades: dict[Symbol, Trade]     # 체결가·체결강도
    change_pct: dict[Symbol, float]      # 등락률
    vi_prices: dict[Symbol, ViLevels]    # 상승/하락 VI 발동가
    upper_limit: dict[Symbol, int]       # 상한가

@dataclass
class Signal:
    action: Literal["ENTER", "EXIT", "CANCEL"]
    symbol: Symbol
    style: Literal["IOC_SWEEP", "LIMIT_GRID"]   # 돌파=스위핑 / 눌림=받치기
    reason: str                                  # 복기·일지용
    urgency: Literal["NORMAL", "IMMEDIATE"]      # 손절은 IMMEDIATE
```

**분리**: 전략은 `Signal`(의도)만 → `OrderManager`가 호가창 보고 실제 주문으로 번역 → `RiskGovernor`가 통과시킴.

### 짝꿍매매 플러그인 (`PairFollowStrategy`)
params = `{leader, follower, surge_pct=25, accel_min, follower_max_gap, take_profit_hold_s=(60,300)}`. 상태기계: `WATCHING → ENTERED`.

```python
def evaluate(self, ctx, armed, position):
    L, F = armed.params.leader, armed.params.follower
    if position is None:                                   # 진입
        leader_surging = (ctx.change_pct[L] >= armed.params.surge_pct
                          and accel(ctx.last_trades[L]) >= armed.params.accel_min
                          and near_upper_limit(ctx, L))
        follower_not_yet = ctx.change_pct[F] <= ctx.change_pct[L] - armed.params.follower_max_gap
        if leader_surging and follower_not_yet:
            return [Signal("ENTER", F, "IOC_SWEEP", "대장주 상한가 돌진", "IMMEDIATE")]
        return []
    if leader_limit_broken(ctx, L):                        # ★손절: 매수이유 훼손
        return [Signal("EXIT", F, "IOC_SWEEP", "대장주 상한가 붕괴", "IMMEDIATE")]
    if held_long_enough(position) and follower_rallied(ctx, F):  # 익절
        return [Signal("EXIT", F, "IOC_SWEEP", "후속주 충분상승 익절", "NORMAL")]
    return []
```

진입 = `대장주 25%+ & 체결강도 급증 & 상한가 근접` + `후속주 덜 오름` / 손절 = `대장주 상한가 붕괴` 즉시(손익무관) / 익절 = `보유 1~5분 & 후속주 랠리`. **새 전략 = 이 인터페이스 구현체 추가.**

### 5.1 짝꿍매매 정밀 정의 (MVP 전략 — 초기값은 추정, 데이터로 튜닝)

모든 정량 트리거. `surge_pct/near_pct/...`는 파라미터(ArmedStrategy.params), 초기값은 첫 가동용 추정치.

**진입① — 대장주 돌진 판정**
- 등락률: `change_pct[L] ≥ surge_pct` (초기 24%)
- 상한가 근접: `(상한가 − 현재가)/상한가 ≤ near_pct` (초기 2%)
- 체결강도(**직접 계산**): 최근 `W`초(초기 5s) 윈도우에서
  - 체결 방향 판정(tick rule): 체결가 ≥ 직전 최우선 매도호가 → **매수주도**, ≤ 매수호가 → 매도주도
  - 매수주도비율 `BV/(BV+SV) ≥ buy_ratio_min` (초기 0.65)
  - **AND** 단기 가속 `(현재가 − W초전가)/W초전가 ≥ accel_min` (초기 +1.5%/5s)

**진입② — 후속주 자격**
- `change_pct[F] ≤ change_pct[L] − gap_min` (초기 8%; 만쥬 사례 ~12%)
- 호가두께 충분 (RiskGovernor가 진입 직전 재확인)

**진입 실행**
- `IOC_SWEEP`: 후속주 최우선 매도호가 ~ +`N`틱(초기 2틱) 시장가성 즉시 체결, 미체결분 `order_timeout`(초기 1.5s) 경과 시 취소

**손절(L1) — 대장주 상한가 붕괴 (최우선, 손익무관)**
- 대장주 상한가 매수잔량이 관측 peak 대비 `≤ break_ratio`(초기 50%)로 급감, **또는** 상한가 아래로 체결 발생
- → 후속주 즉시 `EXIT(IOC_SWEEP, IMMEDIATE)`

**익절 — 대장주 연동 중심**
- 대장주 상한가 유지(매수잔량 형성)되는 동안 후속주 홀딩
- 익절 발화: `보유 ≥ hold_min`(초기 60s) **AND** 다음 중 하나
  - 목표 도달: 후속주가 대장주 등락률에 근접(gap 축소 ≤ `gap_close`) 또는 `+tp_pct`(초기 +5%)
  - 상승 둔화: 후속주 최근 `W`초 체결강도 < `neutral` 또는 고점 대비 되돌림 ≥ `pullback`(초기 −1.5%)
- `hold_max`(초기 300s) 도달 시 무조건 청산 (단타 1일 사이클)

**백스톱(L2, 거버너)**: 종목당 `≤ −stop_pct`(초기 −2.5%) 무조건 청산 — 전략이 손절 못 내도

> 정의된 함수: `near_upper_limit`, `accel`/체결강도(직접계산), `leader_limit_broken`, 익절 판정. `orderbook_thick_enough`는 §6 거버너에서 정의. 초기값은 모두 백테스트로 튜닝 대상.

### 5.2 상따·돌파 정밀 정의 (`LimitChaseStrategy`) — 범위: 상한가 lock 집중

상한가로 강하게 달리는 **대장주 본인**에 올라타 상한가 안착(lock)을 노림. §5.1의 "대장주 돌진 판정"을 *진입*에, "대장주 상한가 상태"를 *청산*에 재사용. 단 천장 근처를 사는 거라 더 위험 → 더 타이트한 손절.

| 트리거 | 정량 정의 | 초기값 |
|---|---|---|
| 진입 윈도우 | 등락률이 진입대 (너무 이르지도 늦지도) | 22%~29.5% |
| 상한가 근접 | `(상한가−현재가)/상한가 ≤ near_pct` AND 아직 미lock(현재가<상한가) | near 4% |
| 가속(체결강도) | §5.1 직접계산: 최근 5s 매수주도비율 ≥ `buy_ratio_min` AND `+accel_min` | 0.65 / +1.5%/5s |
| 끝물 차단 | 상한가까지 여유 ≥ `min_room` (코앞이면 추격 금지) | 0.3% |
| 진입 실행 | 최우선 매도호가~+N틱 IOC 스위핑, 미체결 타임아웃 취소 | N=2틱 / 1.5s |
| 익절(성공) | 상한가 안착(매수잔량 형성) → 홀딩, **상한가 잔량 붕괴 시 즉시 청산** | break_ratio 50% |
| 손절(실패) | 상한가 도달 실패 + 모멘텀 소멸(체결강도 약화 OR 고점대비 되돌림 ≥ `pullback`) → 즉시 | pullback −1.5% |
| 최대 보유 | `hold_max` 도달 시 무조건 청산 | 180s |
| 백스톱(L2) | 종목당 ≤ `−stop_pct` (짝꿍 −2.5%보다 타이트, 천장 매수라 위험) | **−2.0%** |

핵심 차이: **짝꿍=대장주 보고 후속주 산다 / 상따=대장주 자체를 천장 직전에 산다.** `min_room`으로 끝물 추격 차단.

### 5.3 낙주 정밀 정의 (`OversoldBounceStrategy`) — 진입: 반등 확인 후

당일 고점 대비 급락한 종목의 강한 반등을 짧게 먹는 **역추세** 전략. 만쥬 핵심 경고: 끝없이 빠지는 종목이 있으니 **손절을 훨씬 타이트하게**.

| 트리거 | 정량 정의 | 초기값 |
|---|---|---|
| 낙폭 과대 | `(당일고점−현재가)/당일고점 ≥ drop_pct` | −15% |
| 반등 확인 | 최근 5s 체결강도 매수우위(`buy_ratio ≥ rev_ratio`) AND 직전 저점 대비 반등 시작(`+rebound_min`) | 0.60 / +0.5% |
| 진입 실행 | 최우선 매수호가 근처 IOC/지정가, 미체결 타임아웃 취소 | 1.5s |
| 익절 | 반등 목표 `tp_pct` 도달 OR 반등 둔화(체결강도 약화) | +3% |
| 손절(★타이트) | 진입가 `−stop_pct` OR 직전 저점 이탈 → 즉시 | **−1.5%** |
| 최대 보유 | `hold_max` 도달 시 청산 (낙주 반등은 빨라야 함) | 120s |

핵심 차이: 짝꿍·상따는 "강한 상승에 올라타기", 낙주는 "급락 후 반등 받기" → **타이트 손절 + 빠른 회전**이 생명.

> **데이터 메모:** 낙주의 "당일 고점"은 KIS 체결 프레임의 `STCK_HGPR`. 현재 `Trade` 스키마엔 typed 컬럼이 없지만 **`raw`(전체 프레임)에 보존**되므로 데이터 손실 없음 — 낙주 빌드 시 `raw`에서 `high_price` 컬럼으로 surface하면 됨. (소스 확정은 §5.4 O4)

### 5.4 정의 확정 (2026-06-02 §14 검토 반영 — Phase 1 코드화 차단 해소)

§14 검토에서 나온 "정의 미비로 코드화 불가" 항목들을 여기서 확정한다. 이 절이 §5.1~5.3의 모호 표현에 대해 **권위 있는 정의**다. (해소 항목: C3 C4 C9 C16, P1 P2 P3 P6, S1 S3, O1 O2 O4 / C10은 §7)

**[공통] 체결강도 (C3 해소 — tick rule 폐기):** "직전 호가" 재구성 대신 KIS 체결프레임 `CCLD_DVSN`(체결구분: `1`=매수주도, `5`=매도주도, `3`=장전)을 직접 사용. 최근 `W`초(5s) 윈도우에서 `buy_ratio = Σ(CCLD_DVSN=1 체결량) / Σ(전체 체결량)`. spread 내부 체결·직전호가 시점·스트림 머지 모호성이 전부 사라져 결정론적. (결정 #9와 무모순 — 윈도우·비율은 우리가 직접 계산, KIS의 누적 CTTR은 여전히 미사용.) 단일가(VI) 구간 틱은 계산에서 제외(C2 후속, 안전 tier).

**[공통] 청산측 체결강도 약화 'neutral' (C9):** `buy_ratio < neutral`(초기 **0.50**). 진입(0.65/0.60) ↔ 청산(0.50) 히스테리시스로 채터링 방지. 각 전략 params에 등재.

**[공통] pullback 기준 '고점' (C16):** "포지션 진입 이후 관측 체결가 running max". 되돌림 = `(현재가 − run_max)/run_max ≤ pullback`(음수). 진입 시 `run_max = 진입가`로 초기화. 전 전략 동일.

**[짝꿍/상따] 상한가 '안착(locked)' 정량 (P3):** `locked = (현재가 == 상한가) AND (상한가 매수잔량 ≥ lock_qty_min, 초기 50,000주) AND (위 상태 ≥ lock_dwell_s 유지, 초기 3s)`. 익절 홀딩(§5.1 익절·§5.2 익절)의 "안착" 판정 기준.

**[짝꿍/상따] break_ratio 분모 'peak' (P2):** peak = "locked 성립 이후 상한가 매수잔량의 running max"(locked 성립 시 트래커 리셋). 붕괴 = `현재 상한가 잔량 ≤ break_ratio × peak`(0.50) **OR** 상한가 아래 체결.

**[짝꿍] gap_close 초기값 (P6):** `4%p`(gap_min 8%의 절반). gap = `change_pct[L] − change_pct[F]`(단위 %p, 진입②의 gap_min과 동일).

**[비중] position_size 시그니처 (C4):** `position_size(regime, account, armed)`로 수정(전략 인자 추가). `ArmedStrategy.params.base_weight`(전략별 기본비중) 신설. 비중 = `자본 × 시황배수 × base_weight`, cap by 종목당상한·EXPOSURE_CAP. 전략별 stop_pct 상이(−2.5/−2.0/−1.5%) → 향후 risk-parity(`base_weight ∝ 1/stop_pct`) 옵션. (§6 비중식이 이 정의를 따름)

**[상따] '상한가 도달 실패' 시간게이트 (S1):** 진입 후 `fail_s`(초기 30s) 내 locked 미성립 시 "모멘텀 소멸"(§5.2 손절: 체결강도<neutral OR pullback) 평가를 활성화. 진입 직후부터 즉시 손절 평가하지 않음(찰나의 흔들림 허용). fail_s를 params에 등재.

**[상따] 진입 결합 논리식 (S3):** `등락률 ∈ [22%, 29.5%] AND (상한가−현재가)/상한가 ∈ [min_room 0.3%, near_pct 4%] AND NOT locked AND buy_ratio ≥ 0.65`. (상한가 거리는 [하한 0.3%, 상한 4%] 단일 밴드.)

**[낙주] 낙폭 기준 drop_pct (O1 — 원문 충실 + 스윕):** 1차 기준 **−35%**(만쥬 '반토막' 정신), 백테스트로 **−25%~−50%** 스윕해 최적화. (−15%는 폐기 — 일상 조정 오인 위험.) 데이터로 최적 낙폭 결정.

**[낙주] '직전 저점' 정의 (O2 — 용도 분리):** 반등확인용 = 최근 `lookback_s`(초기 30s) 롤링 min(갱신). 손절용 = **진입 시 고정한 swing low**(불변, 이탈 시 즉시 손절). 둘은 별개 값.

**[낙주] 당일고가/저점 소스 (O4):** 라이브·백테스트 모두 **"수집 시작 이후 자체 관측 체결가 running max/min"을 단일 소스**로 사용(STCK_HGPR/STCK_LWPR은 교차검증·보조). 장 초반 공백은 REST 일중 고가 1회로 시드. `Trade`에 `high_price`/`low_price` typed 컬럼 추가(raw idx 8/9) — Phase 1 작업. 단, 종목이 급락 도중 top20 진입 시 진입 전 고점 미관측 가능 → §13 낙주 평가에 정확도 저하 단서.

**[백테스트] 짝꿍 페어 식별 PairBuilder (P1 — 결정론적):** Phase 2 비교 백테스트는 LLM이 없으므로 결정론적 `PairBuilder`로 페어 자동 생성:
- 대장 후보 = 같은 시간대 `near_pct`(상한가 근접) 충족 + 거래대금 최상위 종목
- 후속 = 같은 시간대 동반 상승 중이나 `gap_min` 이상 덜 오른 동시수집 종목 (가격대·가능하면 섹터 근접)
- 한 대장에 후속 N개 페어링 허용, 각 페어를 짝꿍 armed로 백테스트
근사 페어링이라 노이즈 존재 → 백테스트 짝꿍 결과는 "하한 추정"으로 해석, 라이브는 LLM 페어로 정밀화.

---

## 6. 리스크 거버너 (가드레일)

**대원칙: 거버너는 "리스크를 늘리는 행동"만 거부한다.**
- ENTER → 심사 통과해야 주문.
- EXIT → 무조건 통과(가속). **손절은 절대 안 막음** → "손절 타이밍 놓침"이 구조적으로 불가능.

### 4단계 손절·정지 계층
| 계층 | 발동 | 행동 | 담당 |
|---|---|---|---|
| L1 전략 손절 | 짝꿍: 대장주 상한가 붕괴 / 낙주: 지지선 이탈 | 해당 포지션 즉시 청산 | 전략 |
| L2 하드 백스톱 | 전략이 손절 못 내도 종목당 −X% 도달 | 무조건 청산(낙주는 더 타이트) | 거버너 |
| L3 일일 손실 한도 | 누적손실(실현+평가) ≥ 한도 | HALT (신규차단 + 전 포지션 청산) | 거버너 |
| L4 시황 서킷브레이커 | regime=HALT(거래대금 가뭄) 또는 N연패 | 신규진입 차단(쉬기) | 거버너 |

### 진입 게이트 (ENTER 심사)
```python
def vet_entry(self, signal, plan, account, market) -> Decision:
    if self.halted:                          return REJECT("HALT 상태")
    if plan.regime == "HALT":                return REJECT("시황 서킷브레이커")
    if self.open_positions >= MAX_CONCURRENT:return REJECT("동시보유 한도")
    if symbol_loss_cap_hit(signal.symbol):   return REJECT("종목당 손실한도")
    size = position_size(plan.regime, account, armed)   # 자본×시황배수×base_weight (정의 §5.4 C4)
    if not orderbook_thick_enough(market, signal.symbol, size):
        return REJECT("호가창 얇음 — 슬리피지 위험")    # 만쥬 '소거' 원칙
    if total_exposure + size > EXPOSURE_CAP: return REJECT("총 익스포저 한도")
    return APPROVE(size)
```
**비중** = `자본 × 시황배수(BULL 1.0 … BEAR 0.2) × base_weight(전략별)`, cap by 종목당상한·총익스포저상한 (시그니처·정의 §5.4 C4) → 만쥬님 "5억→1억" 축소가 `시황배수` 한 변수로 구현됨.
**호가두께 체크가 거버너에 있는 이유**: watchlist 선정(두뇌)은 사전 후보일 뿐, 진입 직전 실시간 호가가 주문 규모를 슬리피지 없이 감당하는지는 그 순간 확인해야 함.

---

## 7. 기술스택 · 백테스트 · 복기 · 장애대응

### 기술 스택
- **Python 3.11+ / asyncio** — 단일 프로세스, 3개 비동기 태스크(두뇌·실행·거버너), SHARED STATE는 in-memory.
- **KIS Adapter** — REST(주문·잔고) + WebSocket(실시간 호가/체결/VI).
- **두뇌 LLM** — Claude (Anthropic SDK) + 프롬프트 캐싱.
- **저장** — SQLite + Parquet (틱로그·체결로그·Journal·LearningStore). 메시지버스 생략(YAGNI).
- **제어/알림** — 텔레그램 봇 또는 로컬 대시보드 + 수동 kill switch.

### 백테스트 — `MarketFeed` 추상화가 열쇠
```
LiveFeed(KIS WS)  ─┐
                   ├─→ 동일 MarketContext 스트림 → SignalEngine + RiskGovernor
ReplayFeed(과거틱) ─┘                              (실행 코드 완전 동일)
```
백테스트 = `ReplayFeed` + **ContextAssembler** + 동일 전략·거버너 + **체결 시뮬레이터**(호가 기반 슬리피지·부분체결 모델). 실행 코드 재사용 → 백테스트/실거래 괴리 없음.

> **ContextAssembler (C10 해소):** ReplayFeed/LiveFeed 둘 다 단일 이벤트(Trade/OrderBook)만 흘리므로, 이를 받아 **종목별 최신 스냅샷(quotes·last_trades·change_pct·upper_limit·vi_prices)을 누적해 매 시점 `MarketContext`를 조립**하는 컴포넌트가 필요(§3 컴포넌트에 추가). 라이브·백테스트 공용 → 괴리 제거. **ViLevels(상·하 VI 발동가)** 산출: KRX 정적 VI(기준가 대비 규정%)·동적 VI(직전 체결 대비 규정%) 중 가까운 값으로 계산 — 정확한 % 테이블은 KRX 규정 반영해 빌드 시 확정.
- 실행 레이어(룰): Plan 고정 입력 + 과거 틱으로 결정론적 재현 → 정밀 백테스트.
- 두뇌 레이어(LLM): 프롬프트 회귀 테스트(과거 케이스에 올바른 분류·등급?) — 통계 백테스트가 아니라 의사결정 품질 평가.

### 복기 (Reviewer)
- 입력: SignalLog(왜 진입/청산) + ExecutionLog(실제 체결) + PnL.
- 출력: TradeJournal(MD, 큰 건 위주) + LearningStore 갱신(패턴 N회 카운트).

### 장애·정합성 (실거래 필수)
| 상황 | 대응 |
|---|---|
| WebSocket 끊김 | 자동 재연결 + 신규진입 동결(안전모드), 보유분은 L2 백스톱이 보호 |
| 주문-잔고 불일치 | 주기적 reconciliation (KIS 실잔고 ↔ 내부) → 불일치 시 즉시 정지+알림 |
| 프로세스 재시작 | 내부 상태 맹신 금지 — KIS 실잔고에서 동기화 후 재개 |
| 중복 주문 | 주문 ID 추적(멱등성) |
| 사람 개입 | Kill switch — 즉시 전체 정지·청산 |

### 관측성
구조화 로그(모든 시그널·주문·거부사유 = 복기 원천) + 실시간 알림(진입/청산/HALT) + 일일 요약.

---

## 8. 데이터·주문 현실 (KIS/KRX 검증 결과)

### 소수점/금액 주문 — 단타엔 불가
- KIS API는 국내주식 주문수량을 **정수 주 단위로 강제**(`ORD_QTY = str(int(qty))`). 소수점/금액 파라미터 없음.
- 한투 "소수점 거래" 서비스 자체도 **신탁·집합주문(일괄체결)** 방식 → 실시간 IOC 즉시체결 불가 → 스켈핑 부적합.
- **10만원 테스트의 역할 = 실행·체결·손절·장애대응 "배관(plumbing)" 검증.** 수익성·비중로직 검증은 **백테스트**가 담당 (10만원으론 수수료·세금 왜곡 + 통계 부족 + 고가주 매수 불가 + 비중 양자화).
- 테스트 모드: 주당 10만원 초과 종목 제외 필터, 호가두께 필터는 사실상 무력화(주문이 작아 항상 통과).

### 과거 데이터 — 일/분봉은 API로 OK, 호가창엔 부족
- 일/주/월/년봉: KIS `inquire-daily-itemchartprice`, KRX OPEN API(EOD) → 가능.
- 분봉: KIS는 **당일 1분봉 30건/호출**만, 과거 분봉 깊이 매우 얕음.
- **과거 틱 + 호가(orderbook) 스냅샷**: KIS·KRX 무료 OPEN API **미제공**(KIS는 실시간 호가만). 우리 핵심 전략(체결강도·상한가 잔량·호가 불균형·VI 잔량)은 이 데이터가 있어야 재현됨.
- 조달: KRX Data Marketplace 유료 구매 가능. **→ 결정: 지금부터 직접 실시간 수집해 로컬 DB 축적 (무료, 미래분).**

### KIS 운영 제약 (설계 반영 필요)
- REST 호출 유량 제한(초당 20건 수준).
- **WebSocket 실시간 등록 한도: 한 세션(=approval_key 1개)당 ~41건.** 한 종목당 체결(H0STCNT0)+호가(H0STASP0) 둘 다 받으면 등록 2건 → **세션당 실질 ~20종목.** 더 필요하면 다중 세션/다중 계좌로 확장.
- VI 발동가는 직접 계산/추적 필요.

### 데이터 수집기 동작 (Phase 0의 핵심)
**핵심 개념: 수집기는 "다운로더"가 아니라 "녹음기".** 과거 틱/호가는 KIS가 안 주므로, 실시간 스트림을 듣고 디스크에 받아적어 미래의 "과거 데이터"를 만든다.

```
[0] 인증(1회):  appkey/secret → access_token(OAuth) + approval_key(/oauth2/Approval)
[1] UniverseSelector (REST 폴링 ~30s):  거래대금/등락률 순위 상위 N(~20)개 선정
[2] Subscriber (WebSocket):  선정 종목 H0STCNT0(체결)+H0STASP0(호가) 등록,
                             universe 변동 시 등록해지/등록 (rotating)
[3] Recorder:  수신 ^구분 문자열 → 파싱 → 정규화 → ticks/{date}/{symbol}.parquet append (raw 동반 보관)
```
- 전 종목(코스닥 1,500+)을 다 못 받으므로 "지금 가장 핫한 상위 N개만 돌려가며 녹음" — 만쥬 '거래대금·변동성' 원칙과 일치.
- 백테스트 = ReplayFeed가 이 parquet들을 시간순으로 읽어 LiveFeed와 동일한 MarketContext로 재생.
- 일/분봉(전일종가·갭·이평선 등 컨텍스트)은 REST(`inquire-daily-itemchartprice`)로 진짜 fetch 가능. 단 호가창 정보 없음 → 호가창 전략 데이터는 녹음으로만 확보.

### 백테스트 타임라인 (수집 먼저 결정의 함의)
- 수집기는 백그라운드 데몬 → 그동안 Phase 1(실행코어)·Phase 2(하네스)·소액 실거래를 **병렬** 진행. "수집만 하는 대기 기간"은 없음.
- "충분한 데이터"의 기준은 캘린더(한 달)가 아니라 **이벤트 표본 수**(테마 터진 날·진입 사례 수십~수백). 단타는 이벤트 의존이라 표본이 천천히 쌓이는 게 본질적 한계.
- 며칠치로 하네스 검증·예비 테스트 가능, 정밀·통계 검증은 표본 쌓일수록 강화.
- **유일한 단축법 = KRX Data Marketplace 과거 틱+호가 유료 구매**(즉시 긴 기간 백테스트). 현재는 무료 수집 우선, 필요 시 전환 옵션으로 보류.

---

## 9. 단계별 빌드 순서

"직접 실시간 수집 먼저" 결정에 따라 데이터 수집기가 가장 먼저, 그동안 실행 코어를 병렬 구축.

- **Phase 0 — 데이터 수집기 + KIS 어댑터** *(즉시 시작, 데이터 축적 개시)*
  - KIS REST/WS 어댑터(토큰·approval_key·재연결 — §12 open-trading-api 재사용), UniverseSelector + Subscriber + Recorder → 틱/호가 로컬 DB 적재. 상세 §8 "데이터 수집기 동작".
- **Phase 1 — 실행 코어 + 전략 플러그인 여러 개 (10만원 plumbing 검증)**
  - SHARED STATE, SignalEngine, OrderManager, PositionManager, RiskGovernor + **여러 전략 플러그인(PairFollow 짝꿍 / 상따·돌파 / 낙주·눌림)**. 10만원 소액 실거래로 주문/체결/손절/장애 배관 검증. ※ 상따·낙주는 진입 규칙이 짝꿍(§5.1)보다 주관적이라 §5.1처럼 정밀 정의 선행 필요(§10 오픈이슈).
- **Phase 2 — 멀티 전략 백테스트 비교 하네스** (결정 #11)
  - ReplayFeed + 체결 시뮬레이터 + **메트릭 레이어**(전략별 사례수·승률·기대값·MDD). 같은 수집 데이터에 모든 전략 detector를 돌려 realized 엣지로 **비교·랭크**. 단타 백테스트는 체결/큐 시뮬 한계가 있으므로 결과는 "명백히 안 되는 것 거르기"용 — 통과 전략은 소액 실거래 포워드 테스트 + 복기로 최종 검증. 상세 §13.
- **Phase 3 — 두뇌 레이어 + 학습 루프**
  - RegimeAnalyzer/ThemeCurator/NewsInterpreter/Reviewer + TradingPlan + EventDetector + LearningStore.
- **Phase 4 — 점진 증액**
  - Phase 2에서 엣지가 검증된 전략부터 비중 증액. 추가 전략(신규상장·뉴스 등) 플러그인 확장.

---

## 10. 오픈 이슈 (구현 전 확정 필요)

- 시황 등급 임계치 구체값 (BULL/NEUTRAL/BEAR/HALT의 코스닥 거래대금 경계, 만쥬 기준: 12~13조/7~8조/5조).
- 리스크 한도 구체값 (일일 최대손실 %, 종목당 손실한도, MAX_CONCURRENT, EXPOSURE_CAP, L2 백스톱 X%).
- `orderbook_thick_enough` 정량 정의 (진입 규모 대비 N호가 누적잔량 배수). ※ 짝꿍 트리거(`near_upper_limit`·체결강도·`leader_limit_broken`·익절)는 §5.1에 초기값 확정 — 백테스트 튜닝 대상.
- **상따·돌파 / 낙주·눌림 전략의 정밀 정의** (§5.1 짝꿍처럼) — 비교 대상이므로 Phase 1 전에 필요. 상따: 대장주 상한가 돌진 진입·익절/이탈 청산. 낙주: 급락 폭·지지선(이평/피보) 판정·타이트 손절.
- 뉴스피드 소스(연합뉴스 등)와 속보 키워드/파싱 방식.
- 데이터 수집 대상 종목 universe(전 종목 vs watchlist만)와 KIS 구독 한도 내 운영 전략.
- 텔레그램 vs 로컬 대시보드 선택.

---

## 11. 만쥬 매매법 ↔ 컴포넌트 매핑 (추적성)

| 만쥬 문서 | 구현 위치 |
|---|---|
| 시황따라 매매하기 | RegimeAnalyzer + 시황배수 + L4 서킷브레이커 |
| 주도주 찾기 / 테마 분류 | ThemeCurator (대장-후속 페어, 등락률 정렬) |
| 종목 선정 (호가두께) | watchlist 후보(두뇌) + RiskGovernor 진입 직전 호가두께 체크 |
| 매수 매도 기준 (짝꿍매매) | PairFollowStrategy |
| 호가창 매매 전략 | OrderManager(IOC/지정가/타임아웃) + 체결강도·VI·호가불균형 시그널 |
| 주식 하수/고수 (복기) | Reviewer + TradeJournal + LearningStore + 학습 루프 |

---

## 12. 참고 구현 & 재사용 — `koreainvestment/open-trading-api`

공식 KIS 오픈소스. **QuantConnect Lean 엔진 기반 일봉(OHLCV) 백테스터 + Next.js UI + FastAPI + MCP 서버.** 전략은 YAML / RuleBuilder DSL / 프리셋 10종, 80개 기술지표, 샤프·MDD·승률 리포트, Grid/Random 최적화. (라이브 트레이딩 X, 검증 전용)

**⚠️ 한계: 일봉 기반이라 우리 호가창 전략(체결강도·상한가 잔량·VI) 백테스트엔 못 씀.** → 호가창 정밀 백테스트는 우리 틱/호가 Recorder + 자체 ReplayFeed로 별도 구축. 단 시황·테마·페어후보 같은 "큰 골격"의 일봉 근사 검증엔 활용 가능.

**재사용 매핑:**

| 레포 모듈 | 우리 재사용처 |
|---|---|
| `kis_auth.py`, `kis_backtest/providers/kis/{auth,data,websocket,brokerage}.py` | **Phase 0/1 KIS 어댑터** (토큰·approval_key·WS·주문) — 적극 재사용 |
| `kis_backtest/core/strategy.py`, `strategies/base.py`, `registry.py`, `dsl/` | 전략 플러그인 인터페이스 패턴 참고 |
| `kis_backtest/core/risk.py`, `strategies/risk/position_sizer.py` | RiskGovernor·비중산정 참고 |
| `kis_backtest/report/`, `portfolio/` | 복기·리포트 참고 |
| `kis_backtest/utils/korean_market.py` | 상한가·장운영시간·거래일 유틸 |
| `frontend/` (Next.js) | 관측성 대시보드 참고 |
| `kis_mcp/` | LLM 두뇌가 KIS 데이터에 접근하는 MCP 경로 참고 |

방침: **KIS 어댑터 계층은 적극 재사용, 프레임워크/리스크/리포트는 패턴 참고, 호가창 정밀 백테스트는 자체 구축.**

---

## 13. 전략 검증 전략 — 멀티 전략 비교 + 포워드 테스트 (결정 #11)

**문제:** 짝꿍매매는 이벤트 의존(테마+대장주 상한가+유효 후속주)이라 사례가 드물고, 우리 데이터는 거래대금 상위 ~20종목만이라 후속주가 누락되면 그 setup은 백테스트 불가 → 표본이 매우 느리게 쌓임. 짝꿍 하나만 백테스트하는 건 비효율.

**결정:** 한 전략에 베팅하지 않는다. 같은 수집 데이터에 **여러 전략 detector를 동시에** 돌려 realized 엣지로 비교·랭크하고, 데이터가 승자를 정하게 한다. (프레임워크 우선 설계의 본래 목적)

전략 비교 축 (어느 것도 전 축에서 우세하지 않음 → 그래서 측정으로 결정):

| 매매법 | 사례 빈도 | 데이터 적합 | 규칙 명확성 | 백테스트 신뢰도 |
|---|---|---|---|---|
| 짝꿍 | 낮음(이벤트+페어) | 부분(후속주 누락 가능) | 높음 | 중 |
| 상따·돌파(대장주) | 중 | 좋음(대장주=상위, 항상 포착) | 중 | 중 |
| 낙주·눌림 | 높음(급락 잦음) | 좋음(단일 종목) | 중(지지선 주관적) | 중 |
| 신규상장 | 매우 낮음 | 좋음 | 중 | 낮음(표본 극소) |
| 뉴스/이벤트 | 변동 | 나쁨(뉴스 미수집) | 낮음(LLM 의존) | 낮음 |

→ 낙주·상따는 단일 종목이라 데이터 100% 포착 + 사례가 자주 나와 **피드백 루프가 빠름**. 짝꿍은 규칙이 가장 명확하지만 느림. 그래서 셋 다 측정해 비교.

**백테스트의 한계 (정직성):** 스켈핑은 체결 큐 위치·슬리피지·부분체결을 과거 데이터로 완벽 시뮬레이션할 수 없음. 만쥬 본인도 백테스트가 아니라 복기를 함. 따라서 백테스트는 **"명백히 안 되는 것을 빠르게 거르는" 1차 필터**이고, 통과한 전략은 **소액 실거래 포워드 테스트 + 복기**로 최종 검증한다 (검증 경로: 백테스트 → 소액 실거래 → 복기).

---

## 14. 전략 스펙 보완 항목 (2026-06-02 6관점 검토 결과)

§5.1~5.3 3개 전략을 6관점(진입·청산/리스크·데이터실현·코드화·전략간충돌·만쥬충실성)으로 검토 → 각 발견을 스펙 전체와 대조 검증 → **39건 확인, 33개 항목으로 병합.** 이 항목들은 "구현 전/단계별로 확정"할 보완 목록이다 (대부분 초기값·세부 정의 미비 또는 안전·운영 가드 누락).

> **✅ 해소 진행 (2026-06-02):** Phase 1 코드화 차단 tier — **C3 C4 C9 C16, P1 P2 P3 P6, S1 S3, O1 O2 O4 → §5.4에서 확정.** C10(ContextAssembler)은 §7. 나머지(안전 가드 C1·C2·C5·C11~C14, Phase 2/4 C6·C7·C8·C15·C17·O5~O7 등)는 해당 단계에서 해소 예정.

### 해소 시점 (triage)
- **Phase 1 빌드 전(정의 확정 — 코드화 차단):** C3 C4 C9 C10 C16, P1 P2 P3 P6, S1 S3, O1 O2 O4
- **라이브 소액거래 전(안전 가드):** C1 C2 C5 C11 C12 C13 C14, P4 P5, S2, O3
- **Phase 2 비교 하네스:** C3 C7 C10 C15, P1
- **Phase 4 다전략 라이브:** C5 C6 C8 C17, O5 O6 O7

### TOP 5 (가장 치명적)
- **T1 = C1** 손절이 "결정"만 되고 "체결/보호"가 안 됨: IOC 미체결 시 sweep-until-flat/MARKET 에스컬 부재 + WS 단절 시 L2(가격트리거) 자기모순(피드 끊기면 관측 불가) + 장 마감 절대시각 강제청산 부재(오버나잇 위험). 자동화 핵심 명분이 3경로에서 무너짐.
- **T2 = C2** VI 발동 "상태"가 MarketContext에 없음(발동'가'만). VI 중 IOC 불가·체결강도 왜곡·재개 급변동이 전 전략 게이트를 통과.
- **T3 = C3** 체결강도 tick rule 비결정적: spread 내부 체결 미분류 + "직전 호가" 시점 정의 부재 + 체결/호가 별도 스트림 머지·동일초 순서 미보존. 전 전략 buy_ratio 의존, 결정#9 주장과 충돌.
- **T4 = C4** `position_size(plan.regime, account)` 시그니처가 비중 공식("...×전략기본비중")과 모순 — 핵심 변수 미전달, 구현 불가 명세. base_weight 미정의.
- **T5 = C5** 동일 종목 중복/충돌 진입 차단 계약 부재: Signal에 strategy_name 없음 + evaluate 종목당 단일 position + vet_entry 총량캡만(per-symbol/in-flight 락 없음).

### 공통 (C)
| ID | 심각도 | 빈틈 | 보완 |
|---|---|---|---|
| C1 | High | 손절 체결/피드단절/마감청산 미보장 | IMMEDIATE EXIT=fill-or-escalate(sweep→MARKET) / 피드단절→REST강제청산 or 사전보호주문 / L5 마감강제청산(15:18 차단,15:20 청산), hold_max=min(hold_max, 마감까지) |
| C2 | High | VI 발동 상태 미노출 | MarketContext.vi_state(NONE/STATIC/DYNAMIC+재개시각), VI중 진입 REJECT+cooldown, 단일가 체결강도 skip, ViLevels 산출식 명문화 |
| C3 | High | 체결강도 tick rule 비결정 | Lee-Ready 3분류, "직전호가"=체결ts 이하 최근 호가, 두 스트림 시간순 머지+seq번호, raw의 SHNU/SELN_CNTG_CSNU 교차검증 |
| C4 | High | position_size 시그니처 모순 | `position_size(regime,account,strategy/armed)`, params에 base_weight, stop_pct 역수 risk-parity 옵션 |
| C5 | High | 중복/충돌 진입 방지 부재 | Signal.strategy_name 추가, vet_entry per-symbol+in-flight 락, 종목 arbiter(IMMEDIATE>기대값>priority), 1종목1포지션 or 키=(symbol,strategy) |
| C6 | High | 거버너 한도 전략간 배분 없음→짝꿍 기아 | 전략별 sub-cap+전역상한 or reserved quota, vet_entry가 strategy_name으로 전략별 카운터 |
| C7 | High | 비교 백테스트 자본모델 미정 | §13에 1차=독립자본(격리) 순수엣지 / 2차=공유자본+거버너 통합시뮬 별도보고 |
| C8 | High | 광기/과열 1시간 캡·오버나잇 금지 미인코딩 | RegimeAnalyzer/ThemeCurator 광기 플래그→hold_max 1시간 강제축소, 오버나잇 0%는 C1 L5와 통합 |
| C9 | High | 청산측 체결강도 'neutral' 미정의 | neutral 파라미터화, 진입0.65↔청산neutral 히스테리시스, 전략 params 초기값 |
| C10 | High | ReplayFeed가 MarketContext 스냅샷 미조립 | Phase2에 ContextAssembler(종목별 최신 quote/trade/change/상한가/VI 누적), LiveFeed 공용 |
| C11 | Med | 거래정지·관리·경고·단기과열 가드 없음 | MarketContext.symbol_status, vet_entry REJECT/감액, ThemeCurator 1차필터 |
| C12 | Med | 장 운영 시간대 가드 없음(동시호가/시간외) | MarketContext.market_session, vet_entry CONTINUOUS에서만 ENTER+no_new_entry_after |
| C13 | Med | 손절 후 재진입 쿨다운 없음 | 종목별 쿨다운(N분/당일횟수)+연속손절 당일 블랙리스트(장중 즉시) |
| C14 | Med | 진입 부분체결 정책 없음 | 실체결수량/평단 기준 청산·백스톱, Position에 의도vs실체결 구분, reconcile 동기화 |
| C15 | Med | 비교 메트릭 거래세·수수료 net 미반영 | net 정의(세금0.18~0.23%+수수료), gross/net 병기, 평균슬리피지·회전율 메트릭 |
| C16 | Med | pullback '고점' 기준시점 미정의 | 고점=진입후 체결가 running max로 전략 통일, 부호·분모 명시 |
| C17 | Low | L4 N연패·종목손실한도 집계주체 미정 | 연패=전략별(부진전략만 휴식), 전역HALT=L3, symbol_loss_cap 전역/전략 택일 |

### 짝꿍 (P)
| ID | 심각도 | 빈틈 | 보완 |
|---|---|---|---|
| P1 | High | 백테스트 페어 식별 주체 부재(§13 LLM-free) | 결정론적 PairBuilder(대장=near_pct, 후속=gap_min+근접) or "LLM 페어 없으면 백테스트 제외, 포워드만" 명문화 |
| P2 | High | break_ratio 분모 '관측 peak' 시작점 미정의 | peak=lock 이후 상한가 매수잔량 running max, lock시 리셋 |
| P3 | High | '상한가 안착(매수잔량 형성)' 정량기준 미정의 | locked=현재가==상한가 AND 잔량≥lock_qty_min AND ≥lock_dwell_s, params 추가 |
| P4 | High | L1 손절이 대장주 피드 생존 의존, 보장경로 없음 | 무장 페어 leader를 rotation서 제외(pinned), 피드끊김→follower 즉시청산 격상 |
| P5 | Med | L의 VI/거래정지/freshness, F stale 가드 없음 | L VI/단일가면 ENTER보류·L2의존, L·F freshness 체크, required_symbols→Subscriber 배선 |
| P6 | Low | gap_close 초기값 부재 | 초기값(예 4%p)+gap 정의=|change_pct[L]−change_pct[F]| |

### 상따 (S)
| ID | 심각도 | 빈틈 | 보완 |
|---|---|---|---|
| S1 | High | '상한가 도달 실패' 확정 시점(시간게이트) 부재 | 진입후 fail_s 내 lock 미성립→모멘텀소멸 평가 활성화, fail_s params (모멘텀소멸 정의 L238은 유지) |
| S2 | Med | 진입시점 VI 상태 가드 부재(VI 직격 1순위) | 'vi_state==NONE+단일가 아닐때만 IOC', 상승VI중 보류+cooldown, 윈도우상단 동적조정 |
| S3 | Med | 진입게이트 결합논리·밴드 의도 미명시 | 명시 AND식: change_pct∈[22,29.5] AND 상한가거리∈[min_room,near_pct] AND 미lock AND 체결강도 |

### 낙주 (O)
| ID | 심각도 | 빈틈 | 보완 |
|---|---|---|---|
| O1 | High | 낙폭 임계 -15%가 원문(-50% 반토막)과 정면배치 | '원문=반토막 근접, -15%는 표본용 추정' 단서+1차기준 -35~-50% 상향검토 |
| O2 | High | '직전 저점' 정의 미정(손절·반등확인 의존) | 반등확인용=최근 lookback_s 롤링min / 손절용=진입시 고정 swing low, lookback_s params |
| O3 | Med | VI/단일가 노출 최대+'끝없이 빠지는 종목' 미구체화 | 하락VI 단일가면 반등판정 보류+재개 cooldown, high_price 미가용시 신호무효, 거래정지 차단(C11) |
| O4 | Med | 당일고가/직전저점 추적 정확도(top20 진입전 미녹음) | Trade에 high/low typed컬럼(raw idx8/9), 라이브·백테 모두 자체 running max 단일소스+REST 시드 |
| O5 | Med | LIMIT_GRID 받치기 누락+§5.3/§6 손절표현 불일치 | §5.3 진입에 LIMIT_GRID(지지선 분할) 옵션, 손절을 §6 L1(지지선 이탈)과 일치, IOC vs Grid 백테 비교 |
| O6 | Med | VI 가격 타겟팅 의사결정룰 미흡수(원문 강조) | 상따·짝꿍 진입에 'VI근접+가속' 결합, 익절에 'VI직전 매도벽→VI전 익절', MVP제외시 §10 등재 |
| O7 | Low | 무수익 횡보시 손익무관 조기청산 부재 | 무수익 타임아웃(T초내 +rebound_min 재확인 실패→본전청산) or '반등둔화' 손익무관 일반화 |

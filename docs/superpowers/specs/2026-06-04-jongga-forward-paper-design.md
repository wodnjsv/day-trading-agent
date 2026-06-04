# 재료 LLM 포워드 페이퍼 검증 — 설계 문서 (Phase 2)

- 작성일: 2026-06-04
- 대상: 종가베팅의 **재료/테마 재량 선별(GPT-5.4)**을 실시간 페이퍼로 검증하는 하네스
- 배경: Phase 1 백테스트 결론 — **시스템틱(룰) 종가베팅은 비용을 강건하게 넘는 엣지 없음**(KOSDAQ 음수, KOSPI 대형주 레짐의존·2025만 net+). 남은 유일한 미검증 레버 = **재료/뉴스/테마 기반 재량 선별**이며, 과거 뉴스 시점누수+비용 때문에 **historical 백테스트 불가 → 포워드 페이퍼로만 검증**(스펙 v4 §8.5). 메모리: `memory/jongga-backtest-findings.md`.
- 상위 설계: `docs/superpowers/specs/2026-06-03-jongga-closebet-agent-design.md`(v4) Phase 2.

---

## 1. 목표와 비목표

**목표**
- 매 거래일, GPT-5.4가 **그날의 재료/테마**를 웹검색으로 조사해 종가에 살 소수 종목을 **선별**하고, 페이퍼로 진입(종가)·청산(익일 시초)을 **기록·정산**한다.
- 누적 결과로 **"재료 선별이 비용을 넘고 룰 baseline을 이기는가"**(§8.5 A/B)를 통계적으로 판정한다.
- 실주문 없이(페이퍼), 시점누수 없이(포워드·실시간), 정직하게 검증한다.

**비목표 (YAGNI)**
- 실거래·주문·체결(페이퍼만 — 실거래는 검증 통과 후 별도 단계).
- 스케줄 자동화(MVP는 CLI 수동 일일 실행 — 자동화는 후속).
- 풀 뉴스 수집 파이프라인(MVP는 GPT-5.4 웹검색만).
- 비중 산정·리스크 거버너 정교화(페이퍼는 등가중으로 종목별 net 측정에 집중).

---

## 2. 핵심 결정사항

| # | 결정 | 선택 |
|---|---|---|
| 1 | 유니버스 | **KOSPI+KOSDAQ 둘 다**, 재료 강도로 선별. 결과는 **시장별 분리 측정** |
| 2 | 재료 소스 | **GPT-5.4 웹검색** (OpenAI SDK). 별도 뉴스 수집 인프라 없음 |
| 3 | 운영 | **CLI 수동 일일 실행** (저녁 선별·기록 + 아침 정산) |
| 4 | 성공 판정 | **net>0 AND 룰 baseline 초과**, 둘 다 통계 유의, 보수 슬리피지에서도 성립 |
| 5 | 선별성 | LLM은 **0~K종목**(좋은 날만), **패스 허용**(억지 매매 방지) |
| 6 | 진입/청산 | 진입=확정 `close[d]`, 청산=익일 `open[d+1]` (페이퍼 MTM) |
| 7 | 후보 공급 | **Phase 1 KRX 파이프라인 재사용**(거래대금·수급·추세·끝물회피로 ~20-30 후보) |

---

## 3. 아키텍처 — 하루 2-커맨드 페이퍼 하네스

```
■ 장 마감 후 (≈15:40)  CLI: jongga-forward-eve  [그날 d]
 1. CandidateScreen   KOSPI+KOSDAQ: 거래대금 상위 + 수급(외국인·기관 매수) + 추세(close>MA20)
                      + 끝물회피(0<당일등락<10%) → 후보 ~20-30 (정량 컨텍스트 동반)   [룰, Phase1 재사용]
 2. CatalystSelect    후보+컨텍스트를 GPT-5.4에 전달 → 웹검색으로 재료/테마/뉴스 조사
                      → 0~K종목 선별(패스 가능): {ticker, 재료요약, theme, conviction,
                      시황read, rationale}  (structured output)                    [LLM]
 3. PaperLog          진입=close[d]로 LLM 페이퍼 바스켓 기록 + 재료/웹검색 스냅샷 보존
                      + 같은 날 '룰 baseline' 바스켓(수급+추세+끝물회피 상위 K)도 기록   [기록]

■ 익일 시가 후 (≈09:10)  CLI: jongga-forward-morn  [d의 미정산분]
 4. Settle            open[d+1] 조회 → 종목별 오버나잇 net(−매도세−수수료−슬리피지밴드)
                      → LLM·baseline 양쪽 실현손익 기록·확정                         [정산]

■ 누적 리포트  CLI: jongga-forward-report
 5. A/B 통계: LLM net vs baseline net (paired), 시장별(KOSPI/KOSDAQ), 비용밴드별, 유의성
```

### 컴포넌트 (신규 `jongga/forward/`)
- `screen.py` — 후보 shortlist. Phase 1 `universe`/`factors`/`krx_provider`/`pykrx_supply` 재사용.
- `select.py` — GPT-5.4 웹검색 재료조사 + 선별(OpenAI SDK, structured output). 후보+컨텍스트 입력 → 0~K 바스켓.
- `paperbook.py` — SQLite 페이퍼 기록(LLM·baseline 양쪽) + 재료/근거/웹검색 스냅샷.
- `settle.py` — 익일 시초 정산(open[d+1] 조회 → net 계산 → 확정).
- `report.py` — A/B 통계(paired, 시장별, 비용밴드별, 성공 판정).
- CLI 엔트리: `jongga-forward-eve`(1·2·3), `jongga-forward-morn`(4), `jongga-forward-report`(5).

### 컴포넌트 분리 원칙
- 선별(LLM)·기록·정산·리포트는 **페이퍼북(SQLite) 하나로만 통신** → 독립 이해/테스트.
- `select.py`(LLM)만 OpenAI에 묶임 → 교체 시 어댑터만.
- 후보·가격은 Phase 1 데이터 계층 재사용 → 중복 없음.

---

## 4. 데이터 흐름 (하루 사이클)

```
저녁 d   ① KRX(가격·수급)로 후보 shortlist(정량) → ② GPT-5.4 웹검색 재료선별(0~K)
        → ③ 페이퍼북에 진입=close[d] 기록 (LLM 바스켓 + 룰 baseline 바스켓 + 재료 스냅샷)
아침 d+1 ④ KRX open[d+1] → 미정산 포지션 net 계산·확정 (LLM·baseline)
주기적   ⑤ 페이퍼북 → A/B 리포트(net>0? LLM>baseline? 시장별·비용밴드·유의성)
```

**원칙:** 진입은 확정 `close[d]`(마감 후 실행이라 누수 없음). 재료는 실시간 웹검색(forward라 시점누수 없음). LLM과 baseline은 같은 날·같은 후보풀에서 선별해 paired 비교.

---

## 5. 검증 설계 (§8.5 A/B)

**기록 단위:** `{date, market, ticker, source(llm|baseline), catalyst_summary, theme, conviction, rationale, entry_close, exit_open, gross, net@{0,0.05,0.10}, settled}` + 웹검색 원문 스냅샷.

**비용:** net = gross − 매도세 0.18% − 수수료 0.014%×2 − 2×슬리피지. 슬리피지 밴드 **{0, 0.05%, 0.1%}** 동시 보고.

**A/B 공정성:** LLM·baseline 모두 동일 후보풀·진입(close[d])·청산(open[d+1])·비용. **paired**(같은 날 비교). KOSPI/KOSDAQ 분리.

**성공 판정(사전 등록, 데이터 누적 전 동결):**
- LLM 바스켓 **net 평균 > 0** (보수 슬리피지 0.1%에서도) AND
- LLM net **>** baseline net (paired, 같은 날) AND
- 둘 다 통계 유의(paired t-test 또는 부호검정, 사전 등록 α).
- 표본: 누적 **~40-50 체결(또는 ~3개월)**, 주간 체크포인트 리포트(중간 중단/연장 판단).

**선별성:** LLM 0~K(기본 K=3~5), 패스 허용. baseline은 같은 후보풀에서 정량 상위 K(패스 없음) — "재료 선별 vs 기계적 선별" 대조.

---

## 6. 정직성 / 한계 (설계에 명시)

- **forward 전용:** historical 백테스트 불가(시점누수). 검증은 실시간 누적뿐이라 느림.
- **재료 품질 = GPT-5.4 웹검색 KR 커버리지 의존.** 검색이 놓친 재료/한국어 소스 한계 → 리포트에 커버리지 단서 기록.
- **페이퍼 ≠ 실체결:** 진입=확정 종가, 청산=실제 시초가라 갭은 현실적. 동시호가 자기주문 충격·미체결은 슬리피지 밴드로 보수 처리(실거래 시 재검증).
- **높은 바:** 약세장(2022-23)엔 baseline이 음수였음 → LLM이 **비용(0.21%) + 음의 드리프트**를 넘어야 함. 통과 못 해도 그 자체가 정직한 결론.
- **과최적화 방어:** 성공 기준·표본·α를 데이터 누적 전 동결(사후 조정 금지).

---

## 7. 기술 스택 / 재사용

- **Python 3.11**, CLI 3개(`pyproject` 콘솔 스크립트).
- **재사용(Phase 1):** `jongga/data/`(KRX·pykrx·캐시), `jongga/universe.py`, `jongga/factors/`, `jongga/secrets.py`.
- **신규:** `jongga/forward/`(screen·select·paperbook·settle·report) + OpenAI SDK.
- **저장:** SQLite 페이퍼북 + 재료 스냅샷(JSON). **secrets:** `openai_api_key`(기존) + KRX 키(기존).

---

## 8. 빌드 순서

- **F1 — 후보 스크린:** `screen.py`(Phase1 재사용으로 KOSPI+KOSDAQ 후보 shortlist + 정량 컨텍스트). 순수 로직 단위테스트.
- **F2 — 페이퍼북:** `paperbook.py`(SQLite 기록·조회, LLM/baseline, 재료 스냅샷). 단위테스트.
- **F3 — 정산·리포트:** `settle.py`(open[d+1] net 계산) + `report.py`(A/B paired·시장별·비용밴드). 순수 계산 단위테스트.
- **F4 — LLM 선별:** `select.py`(GPT-5.4 웹검색 재료조사 + structured output 선별). 스키마 검증 + 소수 실호출 검증.
- **F5 — CLI 결선:** `jongga-forward-eve/morn/report` 엔트리. 실데이터 1일 종단 스모크.
- **F6 — 운영 개시:** 매 거래일 수동 실행, 주간 체크포인트로 누적 → 성공 판정.

---

## 9. 오픈 이슈 (구현 전/운영 전 확정)

- 후보 shortlist 크기, 최종 K, conviction 사용 여부(페이퍼는 등가중 기본).
- GPT-5.4 웹검색 프롬프트(재료 질·테마·시황 read 출력 스키마)와 호출 구조(후보 일괄 vs 종목별).
- 성공 판정 α·표본수·체크포인트 주기(사전 등록 값).
- 룰 baseline 정의 고정(수급+추세(>MA20)+끝물회피(0<등락<10%), 상위 K) — Phase 1과 일치.
- 페이퍼북 스키마 최종(마이그레이션 불필요한 단순 구조).
- 거래일 캘린더(주말·공휴일 — 실행일 가드).

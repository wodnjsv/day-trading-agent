"""GPT-5 웹검색 재료 선별: 프롬프트·structured 스키마 + 응답 파싱·검증(순수)."""
from __future__ import annotations

SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "regime_read": {"type": "string"},
        "picks": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "catalyst_summary": {"type": "string"},
                "catalyst_timestamp": {"type": "string"},
                "theme": {"type": "string"},
                "conviction": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["ticker", "catalyst_summary", "catalyst_timestamp",
                         "theme", "conviction", "rationale"],
            "additionalProperties": False,
        }},
    },
    "required": ["regime_read", "picks"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "너는 한국 주식 종가베팅 트레이더다. 주어진 후보(정량 컨텍스트 포함) 중, "
    "그날 15:20(종가 동시호가) 이전에 공개된 재료/뉴스/테마가 강한 종목만 0~K개 고른다. "
    "재료가 약하면 빈 배열로 패스한다. 각 픽에 재료 발표시각(catalyst_timestamp, ≤15:20)을 반드시 단다. "
    "15:20 이후(장 마감 후) 공시·뉴스는 사용 금지."
)


def build_user_prompt(candidates: list[dict]) -> str:
    lines = ["오늘 후보(거래대금·수급·추세·끝물회피 통과). 재료가 강한 종목만 고르세요:"]
    for c in candidates:
        lines.append(
            f"- {c['ticker']} {c.get('name','')} | 시장 {c['market']} | 등락률 {c['ret_d']:.1%} "
            f"| 종가위치 {c['close_pos']:.2f} | 거래대금 {c['trade_value']/1e8:.0f}억 | 수급 {c.get('supply_note','')}"
        )
    return "\n".join(lines)


def select_with_gpt(candidates: list[dict], api_key: str, model: str = "gpt-5") -> dict:
    """GPT 웹검색으로 재료 선별. raw dict(SELECTION_SCHEMA 형태) 반환.

    모델: gpt-5 (gpt-5-2025-08-07). web_search_preview 도구 + json_schema structured output.
    gpt-5.4 는 존재하지 않음; gpt-5 가 최상위 GPT-5 tier 모델로 확인됨 (2026-06-05 기준).
    """
    import json
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        model=model,
        tools=[{"type": "web_search_preview"}],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(candidates)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "selection",
                "schema": SELECTION_SCHEMA,
                "strict": True,
            }
        },
    )
    try:
        return json.loads(resp.output_text)
    except Exception:
        return {"regime_read": "parse_error", "picks": []}


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

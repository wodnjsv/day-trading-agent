"""KRX OpenAPI 커버리지 프로브.

secrets.yaml의 krx_api_key를 읽어 '코스닥 일별매매정보'를 호출하고:
  1) 인증/요청 방식(GET+query vs POST+json, AUTH_KEY 헤더) 어느 게 먹는지
  2) 실제 응답 필드·값(시총/상장주식수/소속부 포함 검증)
  3) PIT/생존편향(과거일자에 이후 상폐 종목이 잡히는지)
  4) SECT_TP_NM(소속부)으로 관리종목 식별 가능 여부
를 확인한다. **API 키는 출력하지 않는다.**
"""
from __future__ import annotations
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import yaml

KSQ_BYDD = "https://data-dbg.krx.co.kr/svc/apis/sto/ksq_bydd_trd"  # 코스닥 일별매매정보


def load_key() -> str:
    cfg = yaml.safe_load(Path("secrets.yaml").read_text(encoding="utf-8"))
    key = (cfg.get("krx_api_key") or "").strip()
    if not key:
        sys.exit("secrets.yaml의 krx_api_key가 비어 있습니다.")
    return key


def call(date: str, key: str):
    """GET+query → 실패 시 POST+json 순으로 시도. (method_name, rows) 반환."""
    body = json.dumps({"basDd": date}).encode()
    attempts = [
        ("GET+query+AUTH_KEY",
         lambda: urllib.request.Request(
             KSQ_BYDD + "?" + urllib.parse.urlencode({"basDd": date}),
             headers={"AUTH_KEY": key})),
        ("POST+json+AUTH_KEY",
         lambda: urllib.request.Request(
             KSQ_BYDD, data=body,
             headers={"AUTH_KEY": key, "Content-Type": "application/json"})),
    ]
    for name, make in attempts:
        try:
            with urllib.request.urlopen(make(), timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
                return name, data.get("OutBlock_1", [])
        except urllib.error.HTTPError as e:
            print(f"  [{name}] HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:200]}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{name}] 오류: {e}")
    return None, []


def main() -> None:
    key = load_key()
    recent, old = "20240105", "20190102"  # 둘 다 거래일

    print(f"== 1) {recent} 코스닥 일별매매정보 ==")
    method, rows = call(recent, key)
    if not rows:
        sys.exit("응답 없음 — 인증/요청 방식 확인 필요(위 오류 참고).")
    print(f"  작동 방식: {method}")
    print(f"  종목 수: {len(rows)}")
    print(f"  필드: {list(rows[0].keys())}")
    keep = ["ISU_CD", "ISU_NM", "SECT_TP_NM", "TDD_OPNPRC", "TDD_CLSPRC",
            "ACC_TRDVAL", "MKTCAP", "LIST_SHRS"]
    print(f"  샘플: {{ {', '.join(f'{k}={rows[0].get(k)!r}' for k in keep)} }}")
    print(f"  SECT_TP_NM 분포: {dict(Counter(r.get('SECT_TP_NM') for r in rows))}")

    print(f"\n== 2) PIT/생존편향: {old} vs {recent} ==")
    _, old_rows = call(old, key)
    old_t = {r["ISU_CD"] for r in old_rows}
    new_t = {r["ISU_CD"] for r in rows}
    if old_t:
        print(f"  {old} 종목수={len(old_t)} / {recent} 종목수={len(new_t)}")
        print(f"  {old}-only(이후 상폐/코드변경 추정)={len(old_t - new_t)}  "
              f"→ >0 이면 PIT 성립(생존편향 차단 가능)")
    else:
        print(f"  {old} 응답 없음 — 과거 데이터 가용성 확인 필요")


if __name__ == "__main__":
    main()

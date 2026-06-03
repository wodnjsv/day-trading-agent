# API Spec

## 1.1. 사회책임투자채권 정보

## 1.2. Description

사회책임투자채권 정보를 제공 ('19년01월01일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/esg/sri_bond_info

## 1.3. request

### 1.3.1. InBlock_1

| Name | Type | Description |
| --- | --- | --- |
| basDd | string | 기준일자 |

## 1.4. response

### 1.4.1. OutBlock_1

| Name | Type | Description |
| --- | --- | --- |
| BAS_DD | string | 기준일자 |
| ISUR_NM | string | 발행기관 |
| ISU_CD | string | 표준코드 |
| SRI_BND_TP_NM | string | 채권종류 |
| ISU_NM | string | 종목명 |
| LIST_DD | string | 상장일 |
| ISU_DD | string | 발행일 |
| REDMPT_DD | string | 상환일 |
| ISU_RT | string | 표면이자율 |
| ISU_AMT | string | 발행금액 |
| LIST_AMT | string | 상장금액 |
| BND_TP_NM | string | 채권유형 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","ISUR_NM":"__","ISU_CD":"__","SRI_BND_TP_NM":"__","ISU_NM":"__","LIST_DD":"__","ISU_DD":"__","REDMPT_DD":"__","ISU_RT":"__","ISU_AMT":"__","LIST_AMT":"__","BND_TP_NM":"__"},{"BAS_DD":"__","ISUR_NM":"__","ISU_CD":"__","SRI_BND_TP_NM":"__","ISU_NM":"__","LIST_DD":"__","ISU_DD":"__","REDMPT_DD":"__","ISU_RT":"__","ISU_AMT":"__","LIST_AMT":"__","BND_TP_NM":"__"}]}
```

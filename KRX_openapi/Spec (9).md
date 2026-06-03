# API Spec

## 1.1. 유가증권 종목기본정보

## 1.2. Description

유가증권 종목기본정보 ('10년01월04일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/sto/stk_isu_base_info

## 1.3. request

### 1.3.1. InBlock_1

| Name | Type | Description |
| --- | --- | --- |
| basDd | string | 기준일자 |

## 1.4. response

### 1.4.1. OutBlock_1

| Name | Type | Description |
| --- | --- | --- |
| ISU_CD | string | 표준코드 |
| ISU_SRT_CD | string | 단축코드 |
| ISU_NM | string | 한글 종목명 |
| ISU_ABBRV | string | 한글 종목약명 |
| ISU_ENG_NM | string | 영문 종목명 |
| LIST_DD | string | 상장일 |
| MKT_TP_NM | string | 시장구분 |
| SECUGRP_NM | string | 증권구분 |
| SECT_TP_NM | string | 소속부 |
| KIND_STKCERT_TP_NM | string | 주식종류 |
| PARVAL | string | 액면가 |
| LIST_SHRS | string | 상장주식수 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"ISU_CD":"__","ISU_SRT_CD":"__","ISU_NM":"__","ISU_ABBRV":"__","ISU_ENG_NM":"__","LIST_DD":"__","MKT_TP_NM":"__","SECUGRP_NM":"__","SECT_TP_NM":"-","KIND_STKCERT_TP_NM":"__","PARVAL":"__","LIST_SHRS":"__"},{"ISU_CD":"__","ISU_SRT_CD":"__","ISU_NM":"__","ISU_ABBRV":"__","ISU_ENG_NM":"__","LIST_DD":"__","MKT_TP_NM":"__","SECUGRP_NM":"__","SECT_TP_NM":"-","KIND_STKCERT_TP_NM":"__","PARVAL":"__","LIST_SHRS":"__"}]}
```

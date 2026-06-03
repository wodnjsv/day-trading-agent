# API Spec

## 1.1. 선물 일별매매정보 (주식선물外)

## 1.2. Description

파생상품시장의 선물 중 주식선물을 제외한 선물의 매매정보 제공 ('10년01월04일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/drv/fut_bydd_trd

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
| PROD_NM | string | 상품구분 |
| MKT_NM | string | 시장구분(정규/야간) |
| ISU_CD | string | 종목코드 |
| ISU_NM | string | 종목명 |
| TDD_CLSPRC | string | 종가 |
| CMPPREVDD_PRC | string | 대비 |
| TDD_OPNPRC | string | 시가 |
| TDD_HGPRC | string | 고가 |
| TDD_LWPRC | string | 저가 |
| SPOT_PRC | string | 현물가 |
| SETL_PRC | string | 정산가 |
| ACC_TRDVOL | string | 거래량 |
| ACC_TRDVAL | string | 거래대금 |
| ACC_OPNINT_QTY | string | 미결제약정 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","PROD_NM":"__","MKT_NM":"__","ISU_CD":"__","ISU_NM":"__","TDD_CLSPRC":"-","CMPPREVDD_PRC":"-","TDD_OPNPRC":"-","TDD_HGPRC":"-","TDD_LWPRC":"-","SPOT_PRC":"-","SETL_PRC":"0.00","ACC_TRDVOL":"-","ACC_TRDVAL":"-","ACC_OPNINT_QTY":"-"},{"BAS_DD":"__","PROD_NM":"__","MKT_NM":"__","ISU_CD":"__","ISU_NM":"__","TDD_CLSPRC":"-","CMPPREVDD_PRC":"-","TDD_OPNPRC":"-","TDD_HGPRC":"-","TDD_LWPRC":"-","SPOT_PRC":"-","SETL_PRC":"0.00","ACC_TRDVOL":"-","ACC_TRDVAL":"-","ACC_OPNINT_QTY":"-"}]}
```
